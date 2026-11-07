# -*- coding: utf-8 -*-
"""
把 CRM 区间报表（fetch_window.py 导出的 data/raw/range.xls）解析成基准数据。
只取「媒介类型 = 三方营销」的明细行，保留全部指标列。

输出 data/analysis/range_baseline.json：
  window / pairs（媒介×咨询师 全字段）/ totals（区间合计）
"""
import json
import os
import sys

import xlrd

HERE = os.path.dirname(os.path.abspath(__file__))
RANGE_XLS = os.path.join(HERE, "data", "raw", "range.xls")
OUT = os.path.join(HERE, "data", "analysis", "range_baseline.json")
TYPE_NAME = "三方营销"

# 与 parse_daily.py 一致：报表列序（0-based，建档量起于第 4 列）
COLS = [
    "建档量", "预约量", "预约率", "一级预约量",
    "来院_新客首次", "来院_新客二次", "来院_新客", "来院_老客", "来院_总人数", "新客首次来院率",
    "成交_新客首次", "成交_新客二次", "成交_新客", "成交_老客", "成交_总人数", "新客成交率",
    "金额_新客首次", "金额_新客二次", "金额_新客", "金额_老客", "成交总金额", "新客人均金额",
]
START = 3


def num(v):
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else RANGE_XLS
    wj = os.path.join(HERE, "data", "analysis", "window.json")
    window = json.load(open(wj, encoding="utf-8")) if os.path.exists(wj) else {}

    sh = xlrd.open_workbook(path).sheet_by_index(0)
    cur_t = cur_s = ""
    pairs = {}
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
        vals = {name: num(sh.cell_value(r, START + i)) for i, name in enumerate(COLS)}
        key = f"{cur_s or '未填写'}|{c2}"
        if key in pairs:
            for k, v in vals.items():
                pairs[key][k] += v
        else:
            pairs[key] = vals

    totals = {k: sum(p.get(k, 0.0) for p in pairs.values()) for k in COLS}
    json.dump({
        "window": [window.get("start"), window.get("end")],
        "source": os.path.basename(path),
        "pairs": pairs,
        "totals": totals,
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"区间 {window.get('start')} ~ {window.get('end')}｜组合 {len(pairs)} 个")
    print(f"  建档 {totals['建档量']:,.0f} | 来院 {totals['来院_总人数']:,.0f} | "
          f"成交 {totals['成交_总人数']:,.0f} | 业绩 {totals['成交总金额']:,.2f}")
    print("已写出:", OUT)


if __name__ == "__main__":
    main()
