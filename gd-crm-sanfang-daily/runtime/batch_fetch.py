# -*- coding: utf-8 -*-
"""
GD-CRM 批量抓取：一个浏览器会话内逐日拉取「网电咨询师媒介/渠道报表」
每天：设日期 -> 查询 -> 抓HTML -> 导出Excel
用法: python batch_fetch.py 2026-10-01 2026-10-13
"""
import json
import os
import sys
from datetime import date, timedelta

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "raw", "daily")
BASE = os.environ.get("CRM_BASE_URL", "http://192.168.16.138").rstrip("/")  # [portable] 换内网地址时设环境变量
CHROME = os.environ.get("CRM_CHROME") or None  # [portable] 留空则用 playwright 自带 chromium


def daterange(a: str, b: str):
    d0 = date.fromisoformat(a)
    d1 = date.fromisoformat(b)
    while d0 <= d1:
        yield d0.isoformat()
        d0 += timedelta(days=1)


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-10-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-10-13"
    os.makedirs(OUT, exist_ok=True)

    with open(os.path.join(HERE, "config.local.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME)
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        )
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
        print("iframe 就绪", flush=True)

        # 维度设一次（后续查询沿用）
        frame.evaluate("() => { jQuery('#twolevwd').combobox('setValue', '媒介+咨询师'); }")
        page.wait_for_timeout(1000)

        for d in daterange(start, end):
            xls = os.path.join(OUT, f"{d}.xls")
            if os.path.exists(xls) and os.path.getsize(xls) > 5000:
                print(f"[{d}] 已存在，跳过", flush=True)
                continue
            try:
                frame.evaluate("""(dd) => {
                    jQuery('#sdate').datebox('setValue', dd);
                    jQuery('#edate').datebox('setValue', dd);
                }""", d)
                frame.evaluate("""() => {
                    var b = Array.from(document.querySelectorAll('a,button')).filter(x => x.innerText && x.innerText.trim() === '查询');
                    if (b.length) b[0].click();
                }""")
                page.wait_for_timeout(16000)
                txt = frame.inner_text("body")
                with open(os.path.join(OUT, f"{d}.txt"), "w", encoding="utf-8") as f:
                    f.write(txt)
                # 导出 Excel
                try:
                    with page.expect_download(timeout=45000) as dl:
                        frame.evaluate("() => report1_saveAsExcel2('&excelFormat=2003&pageStyle=0&formula=0')")
                    dl.value.save_as(xls)
                    print(f"[{d}] OK  文本{len(txt)}B  Excel{os.path.getsize(xls)}B", flush=True)
                except Exception as e:
                    print(f"[{d}] Excel失败 {type(e).__name__}", flush=True)
            except Exception as e:
                print(f"[{d}] 失败 {type(e).__name__} {str(e)[:100]}", flush=True)
            page.wait_for_timeout(800)

        browser.close()
    print("全部完成", flush=True)


if __name__ == "__main__":
    main()
