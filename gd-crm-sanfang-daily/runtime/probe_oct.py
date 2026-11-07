# -*- coding: utf-8 -*-
"""只读探测：CRM 目前还能不能查到 2026-10 整月的数据。
命中则把区间报表另存为 data/raw/range_oct.xls，不碰 range.xls / window.json。
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CRM_BASE_URL", "http://192.168.16.138").rstrip("/")  # [portable] 换内网地址时设环境变量
CHROME = os.environ.get("CRM_CHROME") or None  # [portable] 留空则用 playwright 自带 chromium
OUT_XLS = os.path.join(HERE, "data", "raw", "range_oct.xls")

D0, D1 = "2026-10-01", "2026-10-31"


def main():
    cfg = json.load(open(os.path.join(HERE, "config.local.json"), encoding="utf-8"))
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

        frame.evaluate("""([a, b]) => {
            jQuery('#sdate').datebox('setValue', a);
            jQuery('#edate').datebox('setValue', b);
        }""", [D0, D1])
        frame.evaluate("""() => {
            var b = Array.from(document.querySelectorAll('a,button')).filter(x => x.innerText && x.innerText.trim() === '查询');
            if (b.length) b[0].click();
        }""")
        page.wait_for_timeout(18000)

        txt = frame.inner_text("body")
        has = "三方营销" in txt
        print(f"查询 {D0} ~ {D1} -> {'有数据' if has else '空表'}")
        print(f"页面文本长度 {len(txt)}B")
        if not has:
            print("—— CRM 已不返回 10 月数据，无法重出")
            browser.close()
            return 2

        with page.expect_download(timeout=90000) as dl:
            frame.evaluate("() => report1_saveAsExcel2('&excelFormat=2003&pageStyle=0&formula=0')")
        dl.value.save_as(OUT_XLS)
        print(f"已导出: {OUT_XLS} ({os.path.getsize(OUT_XLS):,} B)")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
