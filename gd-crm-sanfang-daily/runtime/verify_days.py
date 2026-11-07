# -*- coding: utf-8 -*-
"""
逐日复核：把指定日期的报表重新抓一遍，与本地存档逐项比对（三方营销口径）。
用法: python verify_days.py 2026-10-20 2026-10-21 ...
输出: data/raw/verify/{date}.xls
"""
import json
import os
import sys

import xlrd
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("CRM_BASE_URL", "http://192.168.16.138").rstrip("/")  # [portable] 换内网地址时设环境变量
CHROME = os.environ.get("CRM_CHROME") or None  # [portable] 留空则用 playwright 自带 chromium
OUT = os.path.join(HERE, "data", "raw", "verify")
DAILY = os.path.join(HERE, "data", "raw", "daily")


def num(v):
    try:
        return float(str(v).replace(",", "").replace("%", "")) if str(v).strip() not in ("", "None") else 0.0
    except Exception:
        return 0.0


def totals(path):
    """返回三方营销口径的 (建档, 来院, 成交, 金额, 明细行数)"""
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    cur_t = cur_s = ""
    j = y = c = a = 0.0
    n = 0
    for r in range(4, sh.nrows):
        c0, c1, c2 = [str(sh.cell_value(r, i)).strip() for i in range(3)]
        if c0.startswith("报表说明"):
            continue
        if c0:
            cur_t = c0
        if c1 and c1 != "汇总：":
            cur_s = c1
        if c2 in ("汇总：", "小计：") or not c2 or c0 == "汇总：" or c1 == "汇总：":
            continue
        if cur_t != "三方营销":
            continue
        v = [num(sh.cell_value(r, k)) for k in range(3, 25)]
        j += v[0]; y += v[8]; c += v[14]; a += v[20]; n += 1
    return j, y, c, a, n


def main():
    days = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
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

        for d in days:
            dst = os.path.join(OUT, f"{d}.xls")
            frame.evaluate("""(dd) => {
                jQuery('#sdate').datebox('setValue', dd);
                jQuery('#edate').datebox('setValue', dd);
            }""", d)
            frame.evaluate("""() => {
                var b = Array.from(document.querySelectorAll('a,button')).filter(x => x.innerText && x.innerText.trim() === '查询');
                if (b.length) b[0].click();
            }""")
            page.wait_for_timeout(16000)
            try:
                with page.expect_download(timeout=45000) as dl:
                    frame.evaluate("() => report1_saveAsExcel2('&excelFormat=2003&pageStyle=0&formula=0')")
                dl.value.save_as(dst)
                print(f"[{d}] 已导出 {os.path.getsize(dst)}B", flush=True)
            except Exception as e:
                print(f"[{d}] 导出失败 {type(e).__name__}", flush=True)
            page.wait_for_timeout(700)

        browser.close()

    print("\n=== 逐日比对（三方营销）===")
    print("%-12s %-34s %-34s %s" % ("日期", "当天存档(建档/来院/成交/金额)", "现在重抓(建档/来院/成交/金额)", "结论"))
    for d in days:
        a = os.path.join(DAILY, f"{d}.xls")
        b = os.path.join(OUT, f"{d}.xls")
        if not (os.path.exists(a) and os.path.exists(b)):
            print(f"{d} 缺文件")
            continue
        ta = totals(a)
        tb = totals(b)
        diff = [round(tb[i] - ta[i], 2) for i in range(4)]
        ok = all(abs(x) < 0.01 for x in diff)
        print("%-12s %.0f/%.0f/%.0f/%.2f   %.0f/%.0f/%.0f/%.2f   %s"
              % (d, ta[0], ta[1], ta[2], ta[3], tb[0], tb[1], tb[2], tb[3],
                 "一致" if ok else "差 " + str(diff)))


if __name__ == "__main__":
    main()
