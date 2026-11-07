# -*- coding: utf-8 -*-
"""
三方营销分析（统计区间：当月 1 号 ~ 前一天）

⚠️ 核心事实（2026-10-28 实测确认）：
   向 CRM 查询「当月1号~昨天」与「可查首日~昨天」返回的是**同一批数据**（逐格一致）。
   即 CRM 只保留当前统计周期内的明细，月初的记录已被归并到可查首日那天的积压里。
   → 所以合计**只能取 CRM 区间报表**，绝不能再叠加本地存档，否则同一批人算两遍。

数据来源：
  1) data/analysis/window.json          —— start=当月1号, end=前一天, queryable_start=CRM 可查最早日
  2) data/analysis/range_baseline.json  —— CRM 区间报表（合计/媒介/咨询师的唯一真值）
  3) data/analysis/daily/*.json         —— 可查段内的单日报表（只用于逐日曲线）

输出 data/analysis/sanfang.json
"""
import collections
import json
import os
import statistics
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DAILY = os.path.join(HERE, "data", "analysis", "daily")
BASE = os.path.join(HERE, "data", "analysis", "range_baseline.json")
WINDOW = os.path.join(HERE, "data", "analysis", "window.json")
OUT = os.path.join(HERE, "data", "analysis", "sanfang.json")
TYPE_NAME = "三方营销"

FIELDS = [
    "建档量", "预约量", "预约率", "一级预约量",
    "来院_新客首次", "来院_新客二次", "来院_新客", "来院_老客", "来院_总人数", "新客首次来院率",
    "成交_新客首次", "成交_新客二次", "成交_新客", "成交_老客", "成交_总人数", "新客成交率",
    "金额_新客首次", "金额_新客二次", "金额_新客", "金额_老客", "成交总金额", "新客人均金额",
]


def load_day(dt):
    return json.load(open(os.path.join(DAILY, dt + ".json"), encoding="utf-8"))["detail"]


def main():
    win = json.load(open(WINDOW, encoding="utf-8"))
    start, end = win["start"], win["end"]
    q_start = win.get("queryable_start") or start

    today = date.today().isoformat()
    all_days = sorted(f[:-5] for f in os.listdir(DAILY)
                      if f.endswith(".json") and start <= f[:-5] <= end and f[:-5] < today)
    # 逐日曲线只用可查段（更早的日子 CRM 已不返回，画上去会与积压日重复）
    dates = [d for d in all_days if d >= q_start]
    if not dates:
        raise SystemExit("可查段内没有任何单日文件")

    print(f"统计区间 {start} ~ {end}（{len(all_days)} 天）")
    print(f"  CRM 可查段 {q_start} ~ {end}（{len(dates)} 天）；"
          f"{start} ~ {q_start} 之前 {len(all_days) - len(dates)} 天 CRM 已不返回，合计不叠加")

    # 重挂日判定：可查区间首日，且建档量 ≥ 日常中位数 3 倍（只用于报告脚注说明，不改数）
    dedup = {"day": None, "amount": 0.0, "ratio": 0.0,
             "archive_days": len(all_days) - len(dates)}
    if len(dates) > 1 and q_start in dates:
        others = [sum(r.get("建档量", 0.0) for r in load_day(d)
                      if r["媒介类型"] == TYPE_NAME) for d in dates if d != q_start]
        med = statistics.median(others) if others else 0
        q_val = sum(r.get("建档量", 0.0) for r in load_day(q_start) if r["媒介类型"] == TYPE_NAME)
        ratio = q_val / med if med else 0
        dedup["ratio"] = ratio
        if med and ratio >= 3:
            pre = [d for d in all_days if d < q_start]
            cum = collections.defaultdict(float)
            for d in pre:
                for r in load_day(d):
                    if r["媒介类型"] == TYPE_NAME:
                        cum[(r["媒介来源"] or "未填写", r["网电咨询师"] or "未填写")] += r.get("建档量", 0.0)
            dedup["day"] = q_start
            dedup["amount"] = sum(cum.values())
            dedup["raw"] = q_val
            print(f"  存量重挂日 {q_start}：建档 {q_val:,.0f}（日常中位 {med:,.0f}，{ratio:.1f} 倍），"
                  f"其中约 {dedup['amount']:,.0f} 条是月初客户被重新挂日期")

    total_trend = {}
    src_trend = collections.defaultdict(dict)
    emp_trend = collections.defaultdict(dict)
    for dt in dates:
        day_tot = collections.defaultdict(float)
        day_src = collections.defaultdict(lambda: collections.defaultdict(float))
        day_emp = collections.defaultdict(lambda: collections.defaultdict(float))
        for r in load_day(dt):
            if r["媒介类型"] != TYPE_NAME:
                continue
            s = r["媒介来源"] or "未填写"
            e = r["网电咨询师"]
            for f in FIELDS:
                v = r.get(f, 0.0)
                day_tot[f] += v
                day_src[s][f] += v
                if e and e not in ("汇总：", "小计："):
                    day_emp[e][f] += v
        total_trend[dt] = dict(day_tot)
        for k, v in day_src.items():
            src_trend[k][dt] = dict(v)
        for k, v in day_emp.items():
            emp_trend[k][dt] = dict(v)

    # 合计 / 媒介 / 咨询师：一律取 CRM 区间报表
    if not os.path.exists(BASE):
        raise SystemExit("缺少 range_baseline.json，请先跑 fetch_window.py 与 build_range_baseline.py")
    base = json.load(open(BASE, encoding="utf-8"))
    totals = {f: base["totals"].get(f, 0.0) for f in FIELDS}
    src_total = collections.defaultdict(lambda: collections.defaultdict(float))
    emp_total = collections.defaultdict(lambda: collections.defaultdict(float))
    for key, rec in base["pairs"].items():
        m, _, e = key.partition("|")
        for f in FIELDS:
            src_total[m][f] += rec.get(f, 0.0)
            emp_total[e][f] += rec.get(f, 0.0)

    # 逐日相加（仅供报告脚注说明与区间报表的差异）
    daily_sum = {f: sum(d.get(f, 0.0) for d in total_trend.values())
                 for f in ("建档量", "来院_总人数", "成交_总人数", "成交总金额")}

    result = {
        "type_name": TYPE_NAME,
        "dates": dates,
        "date_range": [start, end],
        "window": {"start": start, "end": end, "queryable_start": q_start,
                   "archive_days": dedup["archive_days"], "query_days": len(dates)},
        "window_totals": totals,
        "daily_sum": daily_sum,
        "dedup": dedup,
        "crm_segment": {k: base["totals"].get(k, 0.0) for k in
                        ("建档量", "来院_总人数", "成交_总人数", "成交总金额")},
        "total_trend": [{"date": d, **total_trend[d]} for d in dates],
        "src_total": [{"name": k, **{f: v.get(f, 0.0) for f in FIELDS}} for k, v in src_total.items()],
        "src_trend": src_trend,
        "emp_total": [{"name": k, **{f: v.get(f, 0.0) for f in FIELDS}} for k, v in emp_total.items()],
        "emp_trend": emp_trend,
    }
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("已写出:", OUT)

    conv = totals["成交_总人数"] / totals["建档量"] * 100 if totals["建档量"] else 0
    aov = totals["成交总金额"] / totals["成交_总人数"] if totals["成交_总人数"] else 0
    print(f"\n三方营销 {start}~{end}（CRM 区间报表口径）：")
    print(f"  建档 {totals['建档量']:,.0f} | 来院 {totals['来院_总人数']:,.0f} | "
          f"成交 {totals['成交_总人数']:,.0f} 人 | 业绩 {totals['成交总金额']:,.0f} 元")
    print(f"  转化率 {conv:.2f}%  客单价 {aov:,.0f} 元")
    print(f"  逐日相加（{len(dates)} 天）：建档 {daily_sum['建档量']:,.0f} | 来院 {daily_sum['来院_总人数']:,.0f} | "
          f"成交 {daily_sum['成交_总人数']:,.0f} | 业绩 {daily_sum['成交总金额']:,.0f}"
          f"（差额＝CRM 按人去重/后改数）")
    print(f"\n媒介 {len(src_total)} 个、咨询师 {len(emp_total)} 人")


if __name__ == "__main__":
    main()
