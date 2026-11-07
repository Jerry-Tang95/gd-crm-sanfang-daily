# -*- coding: utf-8 -*-
"""渲染校验：截图横向条形图，确认类目轴标签（媒介名）没有因 auto 隐藏而缺失"""
import os
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "三方营销媒介分析报告.html")
OUT = os.path.join(HERE, "_check_charts")
CHROME = os.environ.get("CRM_CHROME") or None  # [portable] 留空则用 playwright 自带 chromium

os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    pg = b.new_page(viewport={"width": 1400, "height": 1000})
    pg.goto("file:///" + HTML.replace("\\", "/"))
    pg.wait_for_timeout(2500)

    report = []
    for cid in ["c_money", "c_emp", "c_build"]:
        info = pg.evaluate("""(cid) => {
            const el = document.getElementById(cid);
            if (!el) return {err:'no element'};
            const ch = echarts.getInstanceByDom(el);
            if (!ch) return {err:'no instance'};
            const o = ch.getOption();
            const cats = (o.yAxis && o.yAxis[0] && o.yAxis[0].type === 'category')
                       ? o.yAxis[0].data
                       : ((o.xAxis && o.xAxis[0] && o.xAxis[0].type === 'category') ? o.xAxis[0].data : []);
            // ECharts 内部记录「实际参与渲染的刻度」：被 auto 隐藏的标签不会进这里
            let shown = null;
            try {
                const ax = ch.getModel().getComponent('yAxis', 0) || ch.getModel().getComponent('xAxis', 0);
                const ticks = ax.axis.getTicksCoords ? ax.axis.getTicksCoords() : null;
                shown = ticks ? ticks.length : null;
            } catch(e) { shown = 'n/a'; }
            return {height: el.clientHeight, cats: cats.length, first: cats[0], last: cats[cats.length-1], ticks: shown};
        }""", cid)
        report.append((cid, info))
        try:
            pg.locator("#" + cid).screenshot(path=os.path.join(OUT, cid + ".png"))
        except Exception as e:
            print("截图失败", cid, e)

    for cid, info in report:
        print(f"{cid}: 容器高 {info.get('height')}px, 类目数 {info.get('cats')}, 首 {info.get('first')}, 末 {info.get('last')}")
    b.close()

print("截图目录:", OUT)
