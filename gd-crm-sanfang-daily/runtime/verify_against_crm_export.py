# -*- coding: utf-8 -*-
"""
拿 CRM 手工导出的报表核对本流水线的数字（两列并排 + 差异明细）。

用法:
    python verify_against_crm_export.py "C:\\path\\NetConsultantMediaChannel (11).xls"

会读取该文件的「时间」表头，解析其中的 三方营销 明细行，
与 data/raw/range.xls（本流水线刚导出的同区间报表）逐媒介比对。
"""
import collections
import os
import re
import sys

import xlrd

HERE = os.path.dirname(os.path.abspath(__file__))
RANGE_XLS = os.path.join(HERE, "data", "raw", "range.xls")
TYPE_NAME = "三方营销"
# 列名 -> 报表列偏移（自第 4 列起）
FIELDS = {"建档量": 0, "来院_总人数": 8, "成交_总人数": 14, "成交总金额": 20}


def parse(path):
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    title = str(sh.cell_value(1, 0)).strip()
    cur_t = cur_s = ""
    pairs = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in range(4, sh.nrows):
        c0, c1, c2 = [str(sh.cell_value(r, i)).strip() for i in range(3)]
        if c0.startswith("报表说明"):
            continue
        if c0 and c0 != "汇总：":
            cur_t = c0
        if c1 and c1 != "汇总：":
            cur_s = c1
        if not c2 or c2 in ("汇总：", "小计：") or c0 == "汇总：" or c1 == "汇总：":
            continue
        if cur_t != TYPE_NAME:
            continue
        key = f"{cur_s or '未填写'}|{c2}"
        for f, off in FIELDS.items():
            v = sh.cell_value(r, 3 + off)
            pairs[key][f] += v if isinstance(v, float) else 0.0
    return title, pairs


def totals(pairs):
    return {f: sum(p.get(f, 0.0) for p in pairs.values()) for f in FIELDS}


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    t1, a = parse(path)
    t2, b = parse(RANGE_XLS)
    ta, tb = totals(a), totals(b)

    print(f"对照文件: {path}")
    print(f"  {t1}")
    print(f"流水线  : {RANGE_XLS}")
    print(f"  {t2}")
    print()
    print(f"{'指标':<10}{'对照文件':>14}{'流水线':>14}{'差异':>10}")
    for f in FIELDS:
        d = tb[f] - ta[f]
        print(f"{f:<10}{ta[f]:>14,.0f}{tb[f]:>14,.0f}{d:>10,.0f}")
    print()
    diffs = []
    for k in sorted(set(a) | set(b)):
        for f in FIELDS:
            x, y = a.get(k, {}).get(f, 0.0), b.get(k, {}).get(f, 0.0)
            if abs(x - y) > 0.5:
                diffs.append((k, f, x, y))
    if not diffs:
        print("逐媒介逐字段：完全一致 ✅")
    else:
        print(f"逐媒介差异 {len(diffs)} 处：")
        for k, f, x, y in diffs:
            print(f"  {k:<28}{f:<10}对照 {x:>10,.0f} | 流水线 {y:>10,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
