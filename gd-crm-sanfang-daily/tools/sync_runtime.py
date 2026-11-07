#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把生产项目目录里的脚本，同步成仓库中的「可移植副本」runtime/。

用途：源机器改了脚本逻辑后，跑一次这个工具，runtime/ 里的发布副本就会带上
同样的改动，并自动重新打上 4 类可移植补丁。避免「源目录 / 仓库」两份代码脱节。

用法（在源机器上，从本仓库任意目录执行）:
    python tools/sync_runtime.py --src "C:/Users/TJL/WorkBuddy/.../gd-crm-媒介日报"

    # 也可只做检查，不写文件
    python tools/sync_runtime.py --src ... --check

补丁内容（都是单行替换，不改业务逻辑）:
    1. PY      -> sys.executable                    （Python 解释器）
    2. CHROME  -> 环境变量 CRM_CHROME，默认 None    （Playwright 浏览器）
    3. BASE    -> 环境变量 CRM_BASE_URL，默认原内网地址
    4. ECHARTS -> runtime/assets/echarts.min.js     （随仓库分发的图表库）

注意：源目录是生产真源、这份是发布副本，方向单向（源 -> 仓库）。
不要反过来把 runtime/ 的改动拷回源目录。
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# 生产流水线 + 校验 + 月报重出所需的最小脚本集。probe* 调试脚本 / 备份副本一律不带。
CORE = [
    "run_daily.py",
    "fetch_window.py",
    "batch_fetch.py",
    "parse_daily.py",
    "build_range_baseline.py",
    "analyze_sanfang.py",
    "gen_report_sanfang.py",
    "verify_days.py",
    "verify_against_crm_export.py",
    "check_group_hl.py",
    "check_charts.py",
    "gen_range_report.py",
    "gen_month.py",
    "gen_oct.py",
    "probe_oct.py",
]

PY_OLD = r'PY = r"C:\Users\TJL\.workbuddy\binaries\python\envs\default\Scripts\python.exe"'
PY_NEW = 'PY = sys.executable  # [portable] 用当前解释器，不写死本机路径'

CHROME_OLD = r'CHROME = r"C:\Users\TJL\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe"'
CHROME_NEW = (
    'CHROME = os.environ.get("CRM_CHROME") or None  '
    '# [portable] 留空则用 playwright 自带 chromium'
)

BASE_OLD = 'BASE = "http://192.168.16.138"'
BASE_NEW = (
    'BASE = os.environ.get("CRM_BASE_URL", "http://192.168.16.138").rstrip("/")  '
    '# [portable] 换内网地址时设环境变量'
)

ECHARTS_OLD = (
    r'ECHARTS = r"C:\Users\TJL\.workbuddy\connectors-marketplace'
    r'\connectors\tencent-yaoxiang-bi\skills\assets\echarts.min.js"'
)
ECHARTS_NEW = (
    'ECHARTS = os.path.join(HERE, "assets", "echarts.min.js")  '
    '# [portable] 图表库随仓库分发'
)

PATCHES = [
    ("PY", PY_OLD, PY_NEW),
    ("CHROME", CHROME_OLD, CHROME_NEW),
    ("BASE", BASE_OLD, BASE_NEW),
    ("ECHARTS", ECHARTS_OLD, ECHARTS_NEW),
]

DEFAULT_SRC = r"C:\Users\TJL\WorkBuddy\2026-10-14-15-59-59\gd-crm-媒介日报"
ECHARTS_CANDIDATES = [
    Path(r"C:\Users\TJL\.workbuddy\connectors-marketplace\connectors"
         r"\tencent-yaoxiang-bi\skills\assets\echarts.min.js"),
]

CONFIG_EXAMPLE = {
    "base_url": "http://192.168.16.138",
    "username": "改成你的 CRM 账号",
    "password": "改成你的 CRM 密码",
    "media_source": "三方营销",
    "note": "复制本文件为 config.local.json 后填写真实凭据；config.local.json 已被 .gitignore 排除，切勿提交",
}

REQUIREMENTS = """# 三方营销日报运行时依赖
playwright>=1.40
xlrd>=2.0.1
"""


def patch(text: str):
    hits = []
    for tag, old, new in PATCHES:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            hits.append(f"{tag}x{n}")
    return text, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.environ.get("CRM_SRC_DIR", DEFAULT_SRC),
                    help="生产项目目录（脚本唯一真源）")
    ap.add_argument("--dst", default=None, help="输出目录，默认 <skill>/runtime")
    ap.add_argument("--echarts", default=None, help="echarts.min.js 源文件路径")
    ap.add_argument("--check", action="store_true", help="只检查不写文件")
    args = ap.parse_args()

    src = Path(args.src)
    here = Path(__file__).resolve()
    dst = Path(args.dst) if args.dst else here.parents[1] / "runtime"
    if not src.is_dir():
        sys.exit(f"源目录不存在: {src}")

    total_hits = 0
    print(f"源: {src}\n目标: {dst}\n模式: {'检查' if args.check else '生成'}\n")
    for name in CORE:
        p = src / name
        if not p.exists():
            print(f"  !! 缺失 {name}")
            continue
        text = p.read_text(encoding="utf-8")
        patched, hits = patch(text)
        total_hits += sum(int(h.split("x")[1]) for h in hits)
        # 生成副本里绝不能残留本机绝对路径
        bad = [k for k in (r"C:\Users\TJL", "C:/Users/TJL") if k in patched]
        flag = "OK " if not bad else "BAD"
        print(f"  {flag} {name:32s} {','.join(hits) or '无需补丁'}")
        if bad:
            print(f"       !! 仍残留本机路径: {bad}")
        if not args.check:
            (dst / name).parent.mkdir(parents=True, exist_ok=True)
            (dst / name).write_text(patched, encoding="utf-8", newline="\n")

    if not args.check:
        (dst / "assets").mkdir(parents=True, exist_ok=True)
        target = dst / "assets" / "echarts.min.js"
        if not target.exists():
            cands = ([Path(args.echarts)] if args.echarts else []) + ECHARTS_CANDIDATES
            for c in cands:
                if c.exists():
                    shutil.copy2(c, target)
                    print(f"  OK  assets/echarts.min.js  <- {c} ({c.stat().st_size:,} B)")
                    break
            else:
                print("  !! 未找到 echarts.min.js，请用 --echarts 指定")
        else:
            print(f"  OK  assets/echarts.min.js  已存在，跳过 ({target.stat().st_size:,} B)")

        (dst / "config.example.json").write_text(
            json.dumps(CONFIG_EXAMPLE, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        (dst / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
        print("  OK  config.example.json / requirements.txt")

    print(f"\n共应用 {total_hits} 处可移植补丁，{len(CORE)} 个脚本。")
    print("提醒：runtime/ 是发布副本，生产真源仍是 --src 指向的目录，方向单向。")


if __name__ == "__main__":
    main()
