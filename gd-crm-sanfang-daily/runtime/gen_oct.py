# -*- coding: utf-8 -*-
"""用当前 sanfang.json（10 月口径）出一份独立的 10 月报告，不覆盖每日主报告。"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable  # [portable] 用当前解释器，不写死本机路径
SRC = os.path.join(HERE, "gen_report_sanfang.py")
TMP = os.path.join(HERE, "gen_oct_report.py")
OUT_NAME = "三方营销媒介分析报告_2026年10月.html"

s = open(SRC, encoding="utf-8").read()
old = 'OUT_HTML = os.path.join(HERE, "三方营销媒介分析报告.html")'
new = f'OUT_HTML = os.path.join(HERE, "{OUT_NAME}")'
assert old in s, "未找到 OUT_HTML 定义"
open(TMP, "w", encoding="utf-8").write(s.replace(old, new))

r = subprocess.run([PY, TMP], cwd=HERE, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
print((r.stdout or "") + (r.stderr or ""))
sys.exit(r.returncode)
