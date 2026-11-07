# -*- coding: utf-8 -*-
"""
解析每日 Excel -> 结构化 JSON
输出: data/analysis/daily/{date}.json
"""
import json
import os
import re

import xlrd

HERE = os.path.dirname(os.path.abspath(__file__))
DAILY = os.path.join(HERE, "data", "raw", "daily")
OUTDIR = os.path.join(HERE, "data", "analysis", "daily")

# 列定义（0-based，已用汇总行交叉验证：来院总人数=新客+老客，成交总额=各客群合计）
COLS = {
    "建档量": 3,
    "预约量": 4,
    "预约率": 5,
    "一级预约量": 6,
    "来院_新客首次": 7,
    "来院_新客二次": 8,
    "来院_新客": 9,
    "来院_老客": 10,
    "来院_总人数": 11,
    "新客首次来院率": 12,
    "成交_新客首次": 13,
    "成交_新客二次": 14,
    "成交_新客": 15,
    "成交_老客": 16,
    "成交_总人数": 17,
    "新客成交率": 18,
    "金额_新客首次": 19,
    "金额_新客二次": 20,
    "金额_新客": 21,
    "金额_老客": 22,
    "成交总金额": 23,
    "新客人均金额": 24,
}
# 兼容 22 列数值区（c3 起）
NUM_START = 3


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


def parse_one(path: str):
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_index(0)
    nrows, ncols = sh.nrows, sh.ncols

    date = None
    # 行1 形如 "时间：2026-10-13--2026-10-13"
    for r in range(min(4, nrows)):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(sh.cell_value(r, 0)))
        if m:
            date = m.group(1)
            break

    detail, source_totals, type_totals, grand_total = [], [], [], None
    cur_type, cur_source = "", ""

    for r in range(4, nrows):
        c0 = str(sh.cell_value(r, 0)).strip()
        c1 = str(sh.cell_value(r, 1)).strip()
        c2 = str(sh.cell_value(r, 2)).strip()
        if not (c0 or c1 or c2):
            continue
        if c0.startswith("报表说明") or "前提：" in str(sh.cell_value(r, 3)):
            continue

        if c0:
            cur_type = c0
        if c1 and c1 != "汇总：":
            cur_source = c1

        vals = {}
        for name, idx in COLS.items():
            vals[name] = num(sh.cell_value(r, idx)) if idx < ncols else 0.0

        row = {"媒介类型": cur_type, "媒介来源": cur_source, "网电咨询师": c2, **vals}

        if c0 == "汇总：":
            grand_total = row
        elif c1 == "汇总：":
            type_totals.append(row)
        elif c2 in ("汇总：", "小计："):
            source_totals.append(row)
        elif c2:
            detail.append(row)

    return {
        "date": date,
        "detail": detail,
        "source_totals": source_totals,
        "type_totals": type_totals,
        "grand_total": grand_total,
    }


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    files = sorted(f for f in os.listdir(DAILY) if f.endswith(".xls"))
    print(f"共 {len(files)} 个 Excel")
    for f in files:
        p = os.path.join(DAILY, f)
        if os.path.getsize(p) < 5000:
            print(f"  跳过 {f} (过小)")
            continue
        try:
            data = parse_one(p)
            out = os.path.join(OUTDIR, f.replace(".xls", ".json"))
            with open(out, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=1)
            gt = data["grand_total"] or {}
            print(f"  {data['date']}: 明细{len(data['detail'])} 来源汇总{len(data['source_totals'])} "
                  f"类型汇总{len(data['type_totals'])} 总建档{gt.get('建档量', '-')} "
                  f"总成交{gt.get('成交_总人数', '-')} 总金额{gt.get('成交总金额', '-')}")
        except Exception as e:
            print(f"  {f} 解析失败: {type(e).__name__} {e}")


if __name__ == "__main__":
    main()
