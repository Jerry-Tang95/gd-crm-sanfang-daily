# -*- coding: utf-8 -*-
"""出「某个月」的独立月度报告，不覆盖每日主报告。

用法:
    python gen_month.py            # 默认：取当前 sanfang.json 所在月份
    python gen_month.py 2026-10    # 指定月份

数据源优先级（只读，绝不改动 data/analysis/ 下的当月四件套）:
    1. data/archive_YYYY-MM/sanfang.json   （月报重出时留下的归档基准）
    2. data/analysis/sanfang.json          （仅当它的 window.start 属于目标月份）

输出: 三方营销媒介分析报告_YYYY年M月.html

注意: 模板与日报完全共用 gen_report_sanfang.py（同一份 TMPL），
所以日报的版式改动（新老客拆分、表格合计行等）会自动带到月报，不需要另维护一套模板。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
GEN = os.path.join(HERE, "gen_report_sanfang.py")
LIVE = os.path.join(HERE, "data", "analysis", "sanfang.json")


def _month_of(path):
    d = json.load(open(path, encoding="utf-8"))
    w = d.get("window") or {}
    start = w.get("start") or (d.get("dates") or [""])[0]
    return start[:7], d


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg:
        month = arg
    else:
        if not os.path.exists(LIVE):
            print("[失败] 找不到 data/analysis/sanfang.json，请先跑一次日报")
            return 1
        month = _month_of(LIVE)[0]

    archive = os.path.join(HERE, "data", f"archive_{month}", "sanfang.json")
    if os.path.exists(archive):
        src, note = archive, "归档基准"
    elif os.path.exists(LIVE) and _month_of(LIVE)[0] == month:
        src, note = LIVE, "当月实时基准"
    else:
        print(f"[失败] 没有 {month} 的数据：{archive} 不存在，"
              f"当月 sanfang.json 也不是这个月。请先走月报重出流程（probe → baseline → analyze）")
        return 2

    _, data = _month_of(src)
    w = data.get("window") or {}
    t = data.get("window_totals") or {}
    y, m = month.split("-")
    out = os.path.join(HERE, f"三方营销媒介分析报告_{y}年{int(m)}月.html")

    print(f"月份: {month}（{note}）")
    print(f"窗口: {w.get('start')} ~ {w.get('end')}"
          f"（逐日 {len(data.get('dates') or [])} 天，可查自 {w.get('queryable_start')}）")
    print(f"合计: 录单 {t.get('建档量', 0):,.0f} / 来院 {t.get('来院_总人数', 0):,.0f} / "
          f"成交 {t.get('成交_总人数', 0):,.0f} 人 / 业绩 {t.get('成交总金额', 0):,.2f}")
    print(f"输出: {os.path.basename(out)}")

    env = dict(os.environ, SANFANG_SRC=src, REPORT_OUT=out)
    r = subprocess.run([PY, GEN], cwd=HERE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(((r.stdout or "") + (r.stderr or "")).strip())
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
