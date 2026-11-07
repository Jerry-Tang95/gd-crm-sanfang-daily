# -*- coding: utf-8 -*-
"""
探测 CRM 当前能查到的日期区间，并把这个区间整段导出成一份报表。

- 二分查找「最早还有数据的那一天」（单日查询，返回空表即无数据）
- 再按 [最早日, 昨天] 导出区间报表 -> data/raw/range.xls
- 结果写 data/analysis/window.json

用法: python fetch_window.py [截止日 YYYY-MM-DD]
"""
import json
import os
import sys
from datetime import date, timedelta

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CRM_BASE_URL", "http://192.168.16.138").rstrip("/")  # [portable] 换内网地址时设环境变量
CHROME = os.environ.get("CRM_CHROME") or None  # [portable] 留空则用 playwright 自带 chromium
RANGE_XLS = os.path.join(HERE, "data", "raw", "range.xls")
WINDOW_JSON = os.path.join(HERE, "data", "analysis", "window.json")


def main():
    end = sys.argv[1] if len(sys.argv) > 1 else (date.today() - timedelta(days=1)).isoformat()
    d_end = date.fromisoformat(end)
    d_start = d_end.replace(day=1)
    days = []
    d = d_start
    while d <= d_end:
        days.append(d.isoformat())
        d += timedelta(days=1)

    with open(os.path.join(HERE, "config.local.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, accept_downloads=True)
        page = ctx.new_page()
        page.goto(BASE + "/Account/Auth/Login", timeout=30000)
        page.fill("#j_username", cfg["username"])
        page.fill("#j_password", cfg["password"])
        page.click("#login_ok")
        page.wait_for_timeout(4000)

        page.get_by_text("报表分析", exact=True).first.click()
        page.wait_for_timeout(2000)
        page.evaluate("""() => {
            var a = document.querySelector("a[href='/ReportAnalysis/NetAnalysis/NetConsultantMediaChannel']");
            if (a) a.click();
        }""")
        page.wait_for_selector("#submit", state="attached", timeout=20000)
        page.evaluate("() => document.querySelector('#submit').click()")
        page.wait_for_timeout(14000)

        frame = None
        for fr in page.frames:
            if "showReport.jsp" in fr.url:
                frame = fr
                break
        assert frame, "未找到 iframe"
        frame.evaluate("() => { jQuery('#twolevwd').combobox('setValue', '媒介+咨询师'); }")
        page.wait_for_timeout(1000)

        def query(d0, d1):
            frame.evaluate("""([a, b]) => {
                jQuery('#sdate').datebox('setValue', a);
                jQuery('#edate').datebox('setValue', b);
            }""", [d0, d1])
            frame.evaluate("""() => {
                var b = Array.from(document.querySelectorAll('a,button')).filter(x => x.innerText && x.innerText.trim() === '查询');
                if (b.length) b[0].click();
            }""")
            page.wait_for_timeout(16000)
            return "三方营销" in frame.inner_text("body")

        # 二分找最早有数据的一天（有数据的天是连续的一段，在末尾）
        lo, hi = 0, len(days) - 1
        if not query(days[-1], days[-1]):
            print(f"!! 截止日 {end} 也没有数据")
            browser.close()
            return 1
        while lo < hi:
            mid = (lo + hi) // 2
            has = query(days[mid], days[mid])
            print(f"  探测 {days[mid]} -> {'有数据' if has else '空表'}", flush=True)
            if has:
                hi = mid
            else:
                lo = mid + 1
        q_start = days[lo]
        print(f"CRM 当前可查区间: {q_start} ~ {end}", flush=True)

        # 统计口径＝当月 1 号 ~ 前一天；报表按整月区间提交（CRM 只返回它有的部分）
        month_start = d_start.isoformat()
        if q_start > month_start:
            print(f"  注意: {month_start} ~ {q_start} 之前的日期 CRM 返回空表，"
                  f"该段仅能由当日存档单日文件补齐", flush=True)

        # 整段导出（按整月区间导出，表头与实际数字一致，便于在 CRM 里复现）
        query(month_start, end)
        os.makedirs(os.path.dirname(RANGE_XLS), exist_ok=True)
        with page.expect_download(timeout=60000) as dl:
            frame.evaluate("() => report1_saveAsExcel2('&excelFormat=2003&pageStyle=0&formula=0')")
        dl.value.save_as(RANGE_XLS)
        print(f"区间报表已导出: {RANGE_XLS} ({os.path.getsize(RANGE_XLS):,} B)", flush=True)
        browser.close()

    os.makedirs(os.path.dirname(WINDOW_JSON), exist_ok=True)
    n = (date.fromisoformat(end) - date.fromisoformat(month_start)).days + 1
    json.dump({"start": month_start, "end": end, "days": n, "queryable_start": q_start},
              open(WINDOW_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"窗口已写入: {month_start} ~ {end}（{n} 天，CRM 可查自 {q_start} 起）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
