# -*- coding: utf-8 -*-
"""
三方营销日报 · 一键流程（月累计口径：当月 1 号 ~ 前一天）

1. fetch_window.py          探测 CRM 当前可查区间（自动二分），并导出该区间报表
2. batch_fetch.py           补抓区间内缺失的单日文件（只用于画逐日曲线）
3. parse_daily.py           解析单日文件
4. build_range_baseline.py  把区间报表解析成基准（总量/媒介/咨询师的唯一真值）
5. analyze_sanfang.py       合并成 sanfang.json
6. gen_report_sanfang.py    出 HTML（主报告，同名覆盖）
7. da_pro_analysis.py       data-analyst-pro 六阶分析（读 sanfang.json → da_pro.json）
8. gen_da_pro_fusion.py     六阶分析融入主报告 → 三方营销_质量数据分析Pro_融合版.html

第 7、8 步是增值分析层：复用主报告的 echarts 与 const D，不联网、不动主报告。
Pro 两步失败不会把主报告判成失败，但会明确告警（日报本体仍可用）。

用法: python run_daily.py [YYYY-MM-DD]   不带参数 = 昨天
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable  # [portable] 用当前解释器，不写死本机路径
DAILY_XLS = os.path.join(HERE, "data", "raw", "daily")
WINDOW_JSON = os.path.join(HERE, "data", "analysis", "window.json")
REPORT = os.path.join(HERE, "三方营销媒介分析报告.html")
PRO_REPORT = os.path.join(HERE, "三方营销_质量数据分析Pro_融合版.html")
HISTORY = os.path.join(HERE, "history")


def _md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_report(win, report=REPORT, prefix=None):
    """每次出报告都留一份快照到 history/，同名窗口 + 同内容只留一份。
    避免主报告被同名覆盖后无法回溯。Pro 融合版用自己的前缀单独留档。"""
    if not os.path.exists(report):
        return None
    os.makedirs(HISTORY, exist_ok=True)
    if prefix is None:
        prefix = f"趋势_{win['start']}_{win['end']}_"
    cur = _md5(report)
    for fn in sorted(os.listdir(HISTORY)):
        if not (fn.startswith(prefix) and fn.endswith(".html")):
            continue
        p = os.path.join(HISTORY, fn)
        try:
            if _md5(p) == cur:
                print(f"[留档] 同内容快照已存在: {fn}", flush=True)
                return p
        except OSError:
            pass
    dst = os.path.join(HISTORY, f"{prefix}{datetime.now():%Y%m%d_%H%M%S}.html")
    shutil.copy2(report, dst)
    print(f"[留档] {os.path.basename(dst)}  ({os.path.getsize(dst):,} B)", flush=True)
    return dst


def run(script, *args, show=8):
    cmd = [PY, os.path.join(HERE, script), *args]
    print(f"\n>>> {script} {' '.join(args)}", flush=True)
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    for line in out.splitlines()[-show:]:
        print("   ", line)
    if r.returncode != 0:
        print(f"!! {script} 退出码 {r.returncode}")
    return r.returncode == 0


def _ok(p):
    return os.path.exists(p) and os.path.getsize(p) > 5000


def _daterange(a, b):
    d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
    out = []
    while d0 <= d1:
        out.append(d0.isoformat())
        d0 += timedelta(days=1)
    return out


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else (date.today() - timedelta(days=1)).isoformat()
    print(f"=== 三方营销日报 {target}（统计区间：当月1号 ~ 前一天）===", flush=True)

    if not run("fetch_window.py", target, show=10):
        print("\n[失败] 无法确定 CRM 可查区间（内网不通或报表异常），未生成报告。")
        return 1

    win = json.load(open(WINDOW_JSON, encoding="utf-8"))
    start, end = win["start"], win["end"]
    print(f"\n统计区间: {start} ~ {end}（{win['days']} 天）", flush=True)
    print(f"CRM 可查自: {win.get('queryable_start', start)}", flush=True)

    # 补齐区间内缺失的单日文件（只为画逐日曲线，不参与合计）
    need = [d for d in _daterange(start, end) if not _ok(os.path.join(DAILY_XLS, d + ".xls"))]
    if need:
        run("batch_fetch.py", need[0], need[-1], show=6)
    else:
        print("单日文件已齐，无需补抓", flush=True)

    ok_parse = run("parse_daily.py", show=8)
    ok_base = run("build_range_baseline.py", show=6)
    ok_ana = run("analyze_sanfang.py", show=10)
    ok_gen = run("gen_report_sanfang.py", show=4)

    core_ok = ok_parse and ok_base and ok_ana and ok_gen
    if os.path.exists(REPORT):
        print(f"\n[完成] 主报告: {REPORT}  ({os.path.getsize(REPORT):,} bytes)")
        print(f"[完成] 窗口: {start} ~ {end}（{win['days']} 天）")
        # 只有四步全绿才留档：否则可能是 gen 用旧 json 出的「假成功」版本，不该进历史
        if core_ok:
            archive_report(win)
        else:
            print("[留档] 跳过 —— 流程有步骤失败，不把这份报告存进历史", flush=True)
    else:
        print("\n[失败] 主报告未生成")
        return 1

    # ===== 增值分析层：data-analyst-pro 六阶分析（不联网、纯本地后处理） =====
    # 只在核心四步全绿时跑，避免拿假成功的旧 json 做二次分析。
    pro_ok = False
    if core_ok:
        print("\n=== 增值分析层 · data-analyst-pro 六阶分析 ===", flush=True)
        ok_pro_ana = run("da_pro_analysis.py", show=8)
        ok_pro_gen = run("gen_da_pro_fusion.py", show=6)
        pro_ok = ok_pro_ana and ok_pro_gen and _ok(PRO_REPORT)
        if pro_ok:
            print(f"[完成] Pro 融合版: {PRO_REPORT}  ({os.path.getsize(PRO_REPORT):,} bytes)")
            archive_report(win, report=PRO_REPORT, prefix=f"Pro_{win['start']}_{win['end']}_")
        else:
            print("[告警] Pro 分析层未生成/失败 —— 主报告不受影响，仍可正常使用。", flush=True)
            print("        排查：da_pro_analysis.py 是否读到 sanfang.json；gen_da_pro_fusion.py 是否读到主报告。", flush=True)
    else:
        print("\n[告警] 核心四步未全绿，跳过 Pro 分析层（避免用旧数据做二次分析）。", flush=True)

    print(f"[完成] 时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    return 0 if core_ok else 1


if __name__ == "__main__":
    sys.exit(main())
