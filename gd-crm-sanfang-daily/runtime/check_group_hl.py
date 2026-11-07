# -*- coding: utf-8 -*-
"""校验：跨组同档联动高亮（2026-10-15 靓仔明确的需求）

需求：指针停在「来院人数·新客」→「成交人数·新客」同时高亮（同一档位，跨两组）。

用例（在报告中所有表格上分别测 5 个档位）：
  1. 悬停来院组第 i 档 → 恰好 2 格亮：来院·第i档 + 成交·第i档
  2. 两格必须同一行、同一 data-col
  3. 移开 → 全部熄灭（无残留）
"""
import os

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "三方营销媒介分析报告.html")
OUT = os.path.join(HERE, "_check_charts")
CHROME = os.environ.get("CRM_CHROME") or None  # [portable] 留空则用 playwright 自带 chromium
os.makedirs(OUT, exist_ok=True)

COLS = [(0, "新客首次"), (1, "新客二次"), (2, "新客"), (3, "老客"), (4, "总人数")]

JS_STATE = """() => {
  const els = Array.from(document.querySelectorAll('td.colhl'));
  return els.map(td => ({
    grp: td.dataset.grp, col: td.dataset.col,
    row: Array.from(td.closest('tr').parentNode.children).indexOf(td.closest('tr'))
  }));
}"""


def check(pg, ti, src_grp, col, name):
    """悬停第 ti 张表某行、src_grp 组、第 col 档 → 断言恰好 2 格（两组同档同 n 行）"""
    row = 3
    pg.evaluate(f"() => document.querySelectorAll('table')[{ti}].scrollIntoView({{block:'center'}})")
    pg.wait_for_timeout(120)
    pg.locator("table").nth(ti).locator("tbody tr").nth(row).locator(
        f"td[data-grp='{src_grp}'][data-col='{col}']").first.hover()
    pg.wait_for_timeout(180)
    st = pg.evaluate(JS_STATE)
    grps = sorted(x["grp"] for x in st)
    cols = {x["col"] for x in st}
    rows = {x["row"] for x in st}
    ok = (len(st) == 2 and grps == ["d", "v"] and cols == {str(col)} and len(rows) == 1)
    flag = "OK " if ok else "FAIL"
    print(f"  表#{ti+1} 悬停{('来院' if src_grp=='v' else '成交')}·{name}: [{flag}] 亮了 {len(st)} 格 {grps} 档位={sorted(cols)}")
    return ok


with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    pg = b.new_page(viewport={"width": 1500, "height": 1000})
    pg.goto("file:///" + HTML.replace("\\", "/"))
    pg.wait_for_timeout(2000)

    n_tbl = pg.evaluate("() => document.querySelectorAll('table').length")
    n_cells = pg.evaluate("() => document.querySelectorAll('td[data-col]').length")
    # 只测「带联动高亮」的表（含 td[data-col]）；口径核对表等普通表不参与
    tbl_idx = pg.evaluate("""() => Array.from(document.querySelectorAll('table'))
        .map((t, i) => ({i, n: t.querySelectorAll('td[data-col]').length}))
        .filter(o => o.n > 0).map(o => o.i)""")
    print(f"表格 {n_tbl} 张（其中带联动高亮 {len(tbl_idx)} 张）；带 data-col 的单元格 {n_cells} 个\n")

    allok = True
    for ti in tbl_idx:
        for col, name in COLS:
            allok &= check(pg, ti, "v", col, name)

    # 截图留证：第 3 张表悬停「来院·新客」
    pg.evaluate("() => document.querySelectorAll('table')[2].scrollIntoView({block:'center'})")
    pg.wait_for_timeout(200)
    pg.locator("table").nth(2).locator("tbody tr").nth(4).locator(
        "td[data-grp='v'][data-col='2']").first.hover()
    pg.wait_for_timeout(300)
    pg.locator("table").nth(2).screenshot(path=os.path.join(OUT, "col_pair_emp.png"))

    # 反向：悬停「成交·新客」应同样点亮「来院·新客」
    pg.locator("table").nth(2).locator("tbody tr").nth(4).locator(
        "td[data-grp='d'][data-col='2']").first.hover()
    pg.wait_for_timeout(300)
    pg.locator("table").nth(2).screenshot(path=os.path.join(OUT, "col_pair_emp_rev.png"))

    pg.mouse.move(5, 5)
    pg.wait_for_timeout(250)
    st = pg.evaluate(JS_STATE)
    clean = len(st) == 0
    allok &= clean
    print(f"\n移开后清除: [{'OK' if clean else 'FAIL'}] 残留 {len(st)} 格")
    print("总判定:", "PASS" if allok else "FAIL")
    b.close()
