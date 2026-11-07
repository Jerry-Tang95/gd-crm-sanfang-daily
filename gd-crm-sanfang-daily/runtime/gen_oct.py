# -*- coding: utf-8 -*-
"""[已泛化] 原名 gen_oct.py，只出 10 月，现改为按月份出：请用 gen_month.py [YYYY-MM]。

保留此文件只为兼容旧命令（SKILL.md 历史版本里的 `python gen_oct.py`），
它等价于 `python gen_month.py 2026-10`。
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    print("[提示] gen_oct.py 已泛化为 gen_month.py，本次等价于 `gen_month.py 2026-10`；"
          "以后请直接用 gen_month.py [YYYY-MM]", flush=True)
    sys.argv = [os.path.join(HERE, "gen_month.py"), "2026-10"]
    runpy.run_path(sys.argv[0], run_name="__main__")
