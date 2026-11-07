#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill 自检（交付前跑一遍，全绿才算可发布）。

用法（在 Skill 目录下）:
    python tools/verify_skill.py            # 快速项：结构 / 元数据 / 脚本 / 同步 / 渲染
    python tools/verify_skill.py --full     # 追加：playwright 版式与图表回归（较慢，约 40s）

检查项：
    [1] 文件完整性（SKILL.md / README / test-prompts / runtime 15 脚本 / echarts 资源）
    [2] SKILL.md frontmatter（YAML 可解析、name/version/summary/triggers 齐全）
    [3] test-prompts.json（JSON 合法、id 唯一、type 合法、条数）
    [4] runtime 脚本：全部 py_compile 通过、无本机绝对路径残留
    [5] runtime ↔ 源目录：逐行一致（允许 PY/CHROME/BASE/ECHARTS 四类可移植补丁行 + 换行符）
    [6] 渲染冒烟：runtime 版 gen_report_sanfang 产出的日报与生产版 md5 相同
    [7] --full：check_group_hl.py PASS、check_charts.py 图表类目全显

退出码 0 = 全绿；非 0 = 有不通过项。
"""
import argparse
import hashlib
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(HERE, "runtime")
SRC = os.environ.get("CRM_SRC_DIR", r"C:\Users\TJL\WorkBuddy\2026-10-14-15-59-59\gd-crm-媒介日报")

CORE = ["run_daily.py", "fetch_window.py", "batch_fetch.py", "parse_daily.py",
        "build_range_baseline.py", "analyze_sanfang.py", "gen_report_sanfang.py",
        "verify_days.py", "verify_against_crm_export.py", "check_group_hl.py",
        "check_charts.py", "gen_range_report.py", "gen_month.py", "gen_oct.py", "probe_oct.py"]
OPTIONAL = ["assets/echarts.min.js", "config.example.json", "requirements.txt", "DEPLOY.md"]

results = []          # (ok, 项目, 详情)
def rec(ok, name, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def sha(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()

    print("=" * 66)
    print(f"Skill: {os.path.basename(HERE)}   目录: {HERE}")
    print("=" * 66)

    # [1] 文件完整性
    print("\n[1] 文件完整性")
    for f in ["SKILL.md", "README.md", "test-prompts.json"]:
        rec(os.path.exists(os.path.join(HERE, f)), f, "" if os.path.exists(os.path.join(HERE, f)) else "缺失")
    miss = [f for f in CORE if not os.path.exists(os.path.join(RUNTIME, f))]
    rec(not miss, "runtime 核心脚本 15 个", f"缺 {miss}" if miss else "齐全")
    miss2 = [f for f in OPTIONAL if not os.path.exists(os.path.join(RUNTIME, f))]
    rec(not miss2, "runtime 附带资源", f"缺 {miss2}" if miss2 else "齐全")

    # [2] frontmatter
    print("\n[2] SKILL.md frontmatter")
    raw = open(os.path.join(HERE, "SKILL.md"), encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    if not rec(bool(m), "YAML 块存在"):
        return 1
    try:
        import yaml
        meta = yaml.safe_load(m.group(1))
        rec(True, "YAML 可解析")
    except Exception as e:                                    # noqa: BLE001
        rec(False, "YAML 可解析", repr(e))
        meta = {}
    for k in ("name", "description", "summary", "version", "type", "triggers"):
        rec(bool(meta.get(k)), f"字段 {k}", str(meta.get(k))[:60] if meta.get(k) else "缺失")
    rec(meta.get("name") == os.path.basename(HERE), "name 与目录名一致", str(meta.get("name")))

    # [3] test-prompts
    print("\n[3] test-prompts.json")
    try:
        tp = json.load(open(os.path.join(HERE, "test-prompts.json"), encoding="utf-8"))
        cases = tp.get("test_cases") or []
        rec(True, "JSON 合法", f"{len(cases)} 条 / v{tp.get('version')}")
        ids = [c.get("id") for c in cases]
        rec(len(ids) == len(set(ids)), "id 唯一")
        bad = [c.get("id") for c in cases
               if c.get("type") not in ("should_trigger", "should_not_trigger", "edge_case")
               or not c.get("prompt") or not c.get("expected_behavior")]
        rec(not bad, "字段完整且 type 合法", f"问题项 {bad}" if bad else "")
        rec(len([c for c in cases if c.get("type") == "should_trigger"]) >= 3, "should_trigger 覆盖")
        rec(len([c for c in cases if c.get("type") == "should_not_trigger"]) >= 2, "should_not_trigger 覆盖")
        rec(len([c for c in cases if c.get("type") == "edge_case"]) >= 2, "edge_case 覆盖")
    except Exception as e:                                    # noqa: BLE001
        rec(False, "JSON 合法", repr(e))

    # [4] runtime 脚本编译 + 无本机路径
    print("\n[4] runtime 脚本可编译 / 无本机路径")
    badc, badp = [], []
    for f in CORE:
        p = os.path.join(RUNTIME, f)
        if not os.path.exists(p):
            continue
        try:
            py_compile.compile(p, cfile=os.path.join(tempfile.gettempdir(), "vc.pyc"), doraise=True)
        except Exception:                                     # noqa: BLE001
            badc.append(f)
        txt = open(p, encoding="utf-8").read()
        if r"C:\Users\TJL" in txt or "C:/Users/TJL" in txt:
            badp.append(f)
    rec(not badc, "15 个脚本 py_compile", f"失败 {badc}" if badc else "全部通过")
    rec(not badp, "无本机绝对路径残留", f"残留 {badp}" if badp else "")

    # [5] runtime ↔ 源目录
    print("\n[5] runtime ↔ 源目录逐行一致")
    if not os.path.isdir(SRC):
        rec(False, "源目录可达", SRC)
    else:
        PAT = re.compile(r"^(PY|CHROME|BASE|ECHARTS)\s*=")
        def norm(p):
            s = open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
            return "\n".join("<PATCH>" if PAT.match(x) else x for x in s.split("\n")).rstrip("\n")
        diff = [f for f in CORE
                if os.path.exists(os.path.join(SRC, f))
                and norm(os.path.join(SRC, f)) != norm(os.path.join(RUNTIME, f))]
        rec(not diff, f"{len(CORE)} 个脚本内容一致（忽略 4 类补丁行）", f"不一致 {diff}" if diff else "15/15")

    # [6] 渲染冒烟
    print("\n[6] 渲染冒烟（runtime 版 vs 生产日报）")
    try:
        import importlib.util
        prod = os.path.join(SRC, "三方营销媒介分析报告.html")
        sj = os.path.join(SRC, "data", "analysis", "sanfang.json")
        if not (os.path.exists(prod) and os.path.exists(sj)):
            rec(False, "生产日报与 sanfang.json 存在", "缺文件，跳过渲染比对")
        else:
            spec = importlib.util.spec_from_file_location("g", os.path.join(RUNTIME, "gen_report_sanfang.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            out = os.path.join(tempfile.gettempdir(), "_skill_smoke.html")
            mod.SRC = sj
            mod.OUT_HTML = out
            mod.main()
            same = sha(out) == sha(prod)
            rec(same, "runtime 渲染 == 生产日报", f"{sha(out)[:12]} vs {sha(prod)[:12]}")
            os.remove(out)
    except Exception as e:                                    # noqa: BLE001
        rec(False, "渲染冒烟", repr(e))

    # [7] 版式回归
    if a.full:
        print("\n[7] 版式/图表回归（playwright）")
        for script, kw in (("check_group_hl.py", "PASS"), ("check_charts.py", "类目")):
            p = os.path.join(SRC, script)
            if not os.path.exists(p):
                rec(False, script, "脚本不存在")
                continue
            r = subprocess.run([sys.executable, p], cwd=SRC, capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            tail = (r.stdout or "").strip().splitlines()[-1:] or [""]
            rec(r.returncode == 0, script, tail[0][:70])

    ok = sum(1 for x in results if x[0])
    total = len(results)
    print("\n" + "=" * 66)
    print(f"结果：{ok}/{total} 通过" + ("  ✅ 全绿" if ok == total else "  ❌ 有未通过项"))
    print("=" * 66)
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
