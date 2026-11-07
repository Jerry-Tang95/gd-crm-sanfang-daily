# -*- coding: utf-8 -*-
"""
区间统计报告（三方营销 · 五档拆分）
来院/成交 均按 新客首次 | 新客二次 | 新客 | 老客 | 总人数 拆开
用法: python gen_range_report.py 2026-10-01 2026-10-13
"""
import collections
import json
import os
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DAILY = os.path.join(HERE, "data", "analysis", "daily")
ECHARTS = os.path.join(HERE, "assets", "echarts.min.js")  # [portable] 图表库随仓库分发
TYPE = "三方营销"

F = ["建档量", "预约量", "一级预约量",
     "来院_新客首次", "来院_新客二次", "来院_新客", "来院_老客", "来院_总人数",
     "成交_新客首次", "成交_新客二次", "成交_新客", "成交_老客", "成交_总人数",
     "金额_新客首次", "金额_新客二次", "金额_新客", "金额_老客", "成交总金额"]


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-10-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-10-13"
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    dates, d = [], d0
    while d <= d1:
        dates.append(d.isoformat())
        d += timedelta(days=1)

    daily, src, emp = [], collections.defaultdict(lambda: collections.defaultdict(float)), \
        collections.defaultdict(lambda: collections.defaultdict(float))
    tot = collections.defaultdict(float)
    used = []
    for dt in dates:
        p = os.path.join(DAILY, dt + ".json")
        if not os.path.exists(p):
            continue
        D = json.load(open(p, encoding="utf-8"))
        day = collections.defaultdict(float)
        for r in D["detail"]:
            if r["媒介类型"] != TYPE:
                continue
            for f in F:
                day[f] += r[f]
                src[r["媒介来源"] or "未填写"][f] += r[f]
                emp[r["网电咨询师"]][f] += r[f]
        daily.append({"date": dt, **day})
        used.append(dt)
        for f in F:
            tot[f] += day[f]
    n = len(daily)
    assert n, "该区间无数据"

    conv = tot["成交_总人数"] / tot["建档量"] * 100 if tot["建档量"] else 0
    aov = tot["成交总金额"] / tot["成交_总人数"] if tot["成交_总人数"] else 0
    visit_conv = tot["来院_总人数"] / tot["建档量"] * 100 if tot["建档量"] else 0

    src_list = sorted([{"name": k, **v} for k, v in src.items()], key=lambda x: -x["建档量"])
    emp_list = sorted([{"name": k, **v} for k, v in emp.items()], key=lambda x: -x["成交总金额"])

    def kpi(k, v, sub=""):
        return f'<div class="kpi"><div class="k">{k}</div><div class="v">{v}</div><div class="d">{sub}</div></div>'

    kpis = "".join([
        kpi("录单量", f"{tot['建档量']:,.0f}", f"{n} 天合计"),
        kpi("来院人数", f"{tot['来院_总人数']:,.0f}", f"来院率 {visit_conv:.1f}%"),
        kpi("成交人数", f"{tot['成交_总人数']:,.0f}", f"转化率 {conv:.2f}%"),
        kpi("成交金额", f"{tot['成交总金额']:,.0f} 元", f"客单价 {aov/10000:.1f} 万"),
    ])

    # 拆分小表（来院 / 成交 / 金额）
    def split_rows(d, metric):
        if metric == "来院":
            return [d["来院_新客首次"], d["来院_新客二次"], d["来院_新客"], d["来院_老客"], d["来院_总人数"]]
        if metric == "成交":
            return [d["成交_新客首次"], d["成交_新客二次"], d["成交_新客"], d["成交_老客"], d["成交_总人数"]]
        return [d["金额_新客首次"], d["金额_新客二次"], d["金额_新客"], d["金额_老客"], d["成交总金额"]]

    def tds(d, metric, money=False):
        vals = split_rows(d, metric)
        out = []
        for i, v in enumerate(vals):
            cls = ' class="tot"' if i == 4 else ""
            out.append(f"<td{cls}>{v:,.0f}</td>")
        return "".join(out)

    rows_daily = "".join(
        f"<tr data-name=\"{d['date']}\"><td>{d['date'][5:]}</td><td class='tot'>{d['建档量']:,.0f}</td>"
        f"{tds(d,'来院')}{tds(d,'成交')}<td class='tot'>{d['成交总金额']:,.0f}</td></tr>"
        for d in daily)
    rows_src = "".join(
        f"<tr data-name=\"{s['name']}\"><td>{i+1}</td><td>{s['name']}</td><td class='tot'>{s['建档量']:,.0f}</td>"
        f"{tds(s,'来院')}{tds(s,'成交')}<td class='tot'>{s['成交总金额']:,.0f}</td></tr>"
        for i, s in enumerate(src_list))
    def is_public(nm):
        return ("公账" in nm) or ("公用" in nm)

    rows_emp = "".join(
        f"<tr class='{'pubrow' if is_public(e['name']) else ''}' data-name=\"{e['name']}\"><td>{i+1}</td>"
        f"<td>{e['name']}{' <span class=tagpub>公共账号</span>' if is_public(e['name']) else ''}</td>"
        f"<td class='tot'>{e['建档量']:,.0f}</td>"
        f"{tds(e,'来院')}{tds(e,'成交')}<td class='tot'>{e['成交总金额']:,.0f}</td></tr>"
        for i, e in enumerate(emp_list))

    # 合计行：前导列数因表而异（每日表=1列「日期」；媒介/咨询师表=2列「# + 名称」）
    def build_total(n_lead):
        lead = "<td>合计</td>" if n_lead == 1 else "<td>合计</td><td>—</td>"
        return (f"<tr class='sumrow'>{lead}<td class='tot'>{tot['建档量']:,.0f}</td>"
                f"{tds(tot,'来院')}{tds(tot,'成交')}<td class='tot'>{tot['成交总金额']:,.0f}</td></tr>")

    total_row = build_total(1)      # 每日明细表（13 列）
    total_row_m = build_total(2)    # 媒介 / 咨询师表（15 列）

    # 列数自检（每日表 13 列 = 日期+录单+来院5+成交5+金额；媒介/咨询师表 15 列 = +序号+名称）
    def n_td(html):
        return html.count("<td")

    assert n_td(total_row) == 13, f"每日表合计行列数错误: {n_td(total_row)}"
    assert n_td(total_row_m) == 14, f"媒介/咨询师表合计行列数错误: {n_td(total_row_m)}"
    if rows_daily:
        assert n_td(rows_daily.split("</tr>")[0]) == 13, "每日表数据行列数错误"
    if rows_src:
        assert n_td(rows_src.split("</tr>")[0]) == 14, "媒介表数据行列数错误"
    if rows_emp:
        assert n_td(rows_emp.split("</tr>")[0]) == 14, "咨询师表数据行列数错误"

    data_js = json.dumps({"daily": daily, "src": src_list, "emp": emp_list}, ensure_ascii=False)

    html = TMPL
    html = html.replace("/*__ECHARTS__*/", open(ECHARTS, encoding="utf-8").read())
    html = html.replace("/*__DATA__*/", "const D = " + data_js + ";")
    html = html.replace("__RANGE__", f"{start} ~ {end}")
    html = html.replace("__NDAYS__", str(n))
    html = html.replace("__KPIS__", kpis)
    html = html.replace("__ROWS_DAILY__", rows_daily + total_row)
    html = html.replace("__ROWS_SRC__", rows_src + total_row_m)
    html = html.replace("__ROWS_EMP__", rows_emp + total_row_m)
    html = html.replace("__NSRC__", str(len(src_list)))
    html = html.replace("__NEMP__", str(len(emp_list)))

    out = os.path.join(HERE, f"三方营销统计_{start}_{end}.html")
    open(out, "w", encoding="utf-8").write(html)

    # 版本留档：每次生成都存一份带时间戳的副本，保留最近 30 份，便于随时回退
    try:
        import glob
        import shutil
        from datetime import datetime as _dt
        hist = os.path.join(HERE, "history")
        os.makedirs(hist, exist_ok=True)
        stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        shutil.copyfile(out, os.path.join(hist, f"统计_{start}_{end}_{stamp}.html"))
        olds = sorted(glob.glob(os.path.join(hist, "统计_*.html")))
        for o in olds[:-30]:
            os.remove(o)
        print("已留档:", os.path.join(hist, f"统计_{start}_{end}_{stamp}.html"))
    except Exception as e:
        print("留档失败(不影响主流程):", e)

    print("报告:", out, os.path.getsize(out), "bytes")
    print(f"{start}~{end}（{n}天）录单{tot['建档量']:,.0f} 来院{tot['来院_总人数']:,.0f} "
          f"成交{tot['成交_总人数']:,.0f} 业绩{tot['成交总金额']:,.0f} 转化率{conv:.2f}%")
    print("拆分核对: 来院 首次+二次=%d 新客=%d 总=%d" % (
        tot["来院_新客首次"] + tot["来院_新客二次"], tot["来院_新客"], tot["来院_总人数"]))
    print("拆分核对: 成交 首次+二次=%d 新客=%d 新客+老客=%d 总=%d" % (
        tot["成交_新客首次"] + tot["成交_新客二次"], tot["成交_新客"],
        tot["成交_新客"] + tot["成交_老客"], tot["成交_总人数"]))


TMPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>三方营销统计 __RANGE__</title>
<style>
:root{--bg:#f7f8fb;--card:#fff;--ink:#1a1f36;--sub:#5b6478;--line:#e6e9f0;--a:#635bff;--a2:#00b8d9;--ok:#12b76a;--warn:#f79009;--bad:#f04438;
--sh:0 1px 2px rgba(16,24,40,.04),0 6px 22px rgba(16,24,40,.07)}
*{box-sizing:border-box}
body{margin:0;color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
background:radial-gradient(1200px 500px at 12% -8%,rgba(99,91,255,.10),transparent 60%),radial-gradient(900px 420px at 92% 4%,rgba(0,184,217,.09),transparent 55%),var(--bg)}
.wrap{max-width:1400px;margin:0 auto;padding:32px 22px 70px}
.hero{background:linear-gradient(135deg,#635bff,#7a5cff 45%,#00b8d9);border-radius:20px;padding:24px 26px;color:#fff;box-shadow:0 12px 40px rgba(99,91,255,.28)}
.hero h1{margin:0 0 6px;font-size:24px}
.hero .meta{opacity:.93;font-size:13.5px}
.hero .tag{display:inline-block;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);border-radius:999px;padding:3px 11px;font-size:12.5px;margin-right:8px}
h2{font-size:17.5px;margin:32px 0 13px;display:flex;align-items:center;gap:9px}
h2 .n{display:inline-flex;width:25px;height:25px;border-radius:9px;background:var(--a);color:#fff;font-size:12.5px;align-items:center;justify-content:center}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:14px 16px;box-shadow:var(--sh)}
.kpi .k{font-size:12.5px;color:var(--sub);margin-bottom:5px}
.kpi .v{font-size:24px;font-weight:700;letter-spacing:-.4px}
.kpi .d{font-size:12.5px;color:var(--sub);margin-top:4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;box-shadow:var(--sh);margin-bottom:15px}
.xwrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;font-size:13px;min-width:100%}
th,td{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:#fff;z-index:2}
th:nth-child(2),td:nth-child(2){text-align:left}
thead th{background:#fafbff;color:var(--sub);font-weight:600;font-size:12.5px;position:sticky;top:0;z-index:3}
thead tr:nth-child(2) th{top:29px}
thead th:first-child{background:#f0f2fb;z-index:5}
td.tot{background:#f8f9ff;font-weight:600}
tr.sumrow td{background:#eef0ff!important;font-weight:700;border-top:2px solid #d9dcf0}
tbody tr:hover td{background:#fbfcff}
tbody tr:hover td.tot{background:#f4f6ff}
.grp{background:#f2f4fd!important;text-align:center!important;font-weight:700;color:#4a4f6a}
.grp.v{color:#0a7ea4}.grp.d{color:#0f8b5f}
.pubrow td{background:#fdfaf4!important}
.tagpub{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:999px;background:#fef0c7;color:#b54708;font-size:11px;font-weight:600;vertical-align:middle}
/* 图表↔表格联动高亮 */
tr.rowhl td{background:#eae7ff!important;font-weight:700}
tr.rowhl td:first-child{box-shadow:inset 3px 0 0 #635bff}
tr.rowhl td:nth-child(2){color:#4b33ff}
tbody{cursor:default}.grp.m{color:#b26a00}
.chart{width:100%;height:330px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:15px}
@media(max-width:980px){.grid2{grid-template-columns:1fr}}
.note{font-size:12.8px;color:var(--sub);background:#fbfcff;border:1px dashed var(--line);border-radius:12px;padding:12px 15px}
.warnbox{font-size:13px;background:#fffaeb;border:1px solid #fedf89;border-radius:12px;padding:12px 15px;color:#7a4b00;margin-bottom:15px}
.toolbar{display:flex;justify-content:flex-end;margin-bottom:15px}
button{background:var(--a);color:#fff;border:0;border-radius:11px;padding:9px 17px;font-size:13.6px;cursor:pointer;box-shadow:0 5px 16px rgba(99,91,255,.3)}
@media print{.toolbar{display:none}.xwrap{overflow:visible}body{background:#fff}.card,.kpi,.hero{box-shadow:none}
 table{font-size:10.5px}th,td{padding:4px 5px}}
</style></head><body><div class="wrap">
<div class="toolbar"><button onclick="window.print()">打印 / 导出 PDF</button></div>
<div class="hero">
  <h1>三方营销 · 数据统计（新客/老客拆分）</h1>
  <div class="meta">
    <span class="tag">__RANGE__</span><span class="tag">共 __NDAYS__ 天</span>
    <span class="tag">录单量＝系统建档量</span>
    <div style="margin-top:8px">来院 / 成交 均按 新客首次 · 新客二次 · 新客 · 老客 · 总人数 拆分 ｜ __NSRC__ 个媒介 · __NEMP__ 位咨询师</div>
  </div>
</div>

<div class="warnbox">
  <b>数据口径已修正</b>：成交人数按「明细逐条加总」统计。报表自带的「媒介类型汇总行」的成交总人数字段有误（会明显偏小），本报告已改用明细口径。
</div>

<h2><span class="n">01</span>总览</h2>
<div class="kpis">__KPIS__</div>

<h2><span class="n">02</span>每日明细（含拆分）</h2>
<div class="card"><div id="c_daily" class="chart"></div></div>
<div class="card"><div class="xwrap">
  <table id="tbl_daily">
    <thead>
      <tr>
        <th rowspan="2">日期</th><th rowspan="2">录单量</th>
        <th colspan="5" class="grp v">来院人数</th>
        <th colspan="5" class="grp d">成交人数</th>
        <th rowspan="2">成交金额</th>
      </tr>
      <tr>
        <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
        <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
      </tr>
    </thead>
    <tbody>__ROWS_DAILY__</tbody>
  </table>
</div></div>

<h2><span class="n">03</span>各媒介统计（__NSRC__ 个，含拆分）</h2>
<div class="grid2">
  <div class="card"><div id="c_src_b" class="chart"></div></div>
  <div class="card"><div id="c_src_m" class="chart"></div></div>
</div>
<div class="card"><div class="xwrap">
  <table id="tbl_src">
    <thead>
      <tr>
        <th rowspan="2">#</th><th rowspan="2">媒介来源</th><th rowspan="2">录单量</th>
        <th colspan="5" class="grp v">来院人数</th>
        <th colspan="5" class="grp d">成交人数</th>
        <th rowspan="2">成交金额</th>
      </tr>
      <tr>
        <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
        <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
      </tr>
    </thead>
    <tbody>__ROWS_SRC__</tbody>
  </table>
</div></div>

<h2><span class="n">04</span>各咨询师统计（__NEMP__ 人，含拆分）</h2>
<div class="card"><div id="c_emp" class="chart"></div></div>
<div class="card"><div class="xwrap">
  <table id="tbl_emp">
    <thead>
      <tr>
        <th rowspan="2">#</th><th rowspan="2">网电咨询师</th><th rowspan="2">录单量</th>
        <th colspan="5" class="grp v">来院人数</th>
        <th colspan="5" class="grp d">成交人数</th>
        <th rowspan="2">成交金额</th>
      </tr>
      <tr>
        <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
        <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
      </tr>
    </thead>
    <tbody>__ROWS_EMP__</tbody>
  </table>
</div></div>

<h2><span class="n">05</span>口径说明</h2>
<div class="note">
  数据范围：系统「网电咨询师媒介/渠道报表」，媒介类型 = <b>三方营销</b>，维度 = 媒介+咨询师，组织机构 = 广州广大医院。<br>
  <b>录单量</b>＝系统「建档量」字段（网电录单/建档客户数）。<br>
  <b>来院人数 / 成交人数</b> 均按五档拆分：<b>新客首次 · 新客二次 · 新客 · 老客 · 总人数</b>（新客＝新客首次＋新客二次；总人数＝新客＋老客）。<br>
  <b>成交金额</b>：所录消费单业绩合计，含退款冲账（个别媒介/账号出现负数属正常）。<br>
  <b>转化率</b>＝成交人数 ÷ 录单量；<b>来院率</b>＝来院人数 ÷ 录单量。<br>
  ⚠️ 本报告所有指标按「明细行逐条加总」统计，未使用报表自带的类型汇总行（该行成交总人数字段有误）。<br>
  <b>证据（可直接反馈 IT）</b>：以 2026-10-01 为例，报表「三方营销类型汇总行」自身即矛盾 —— 它列出「新客 4 ＋ 老客 2」，总人数却填 <b>2</b>（应为 6）；
  而其明细行为 6 人（栋梁-公众号 2、胡桃盒子 1、美呗 1、芘特芙 1、清颜 1），与「全院汇总行」口径一致。
  经 15 天全量校验：各「媒介类型汇总行」相加 ≠ 全院汇总行（每天少算），而明细加总 ≡ 全院汇总行（0 误差）。<br>
  <b>为什么有人「成交人数 2 人、金额却是负数」？</b>——「成交人数」只统计成交单，<b>退款单不计人数</b>；而「成交金额」是<b>净额</b>，退款要扣减。
  因此同一行可能出现「人数为正、金额为负」。例：网电公账 13 天内 2 笔正常成交（+25,800）＋ 3 笔退款（−118,000）＝ <b>成交 2 人 / −92,200 元</b>。<br>
  <b>公共账号</b>（网电公账、三方公用等）非真人咨询师，退款无业绩归属时通常归集于此，故常出现「零录单、零来院却有金额」的情况，排名与人均类指标建议单列看待。
</div>
</div>
<script>/*__ECHARTS__*/</script>
<script>
/*__DATA__*/
const C={a:'#635bff',a2:'#00b8d9',ok:'#12b76a',warn:'#f79009',bad:'#f04438'};
const ax={axisLine:{lineStyle:{color:'#e6e9f0'}},axisLabel:{color:'#5b6478',fontSize:11.5},splitLine:{lineStyle:{color:'#f1f3f9'}}};
const wan=n=>((n||0)/10000).toFixed(1)+'万';
// 高亮态样式：被选中的柱子变成醒目的琥珀色，便于一眼看到"哪根亮着"
const EMPH={itemStyle:{color:'#f59e0b',shadowBlur:16,shadowColor:'rgba(245,158,11,.6)'}};
const CH={};
function mk(id,o){const e=document.getElementById(id);if(e){const c=echarts.init(e);c.setOption(o);CH[id]=c;}}
function bs(){return{tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},grid:{left:10,right:16,top:46,bottom:8,containLabel:true}};}

// 每日：录单 + 来院/成交堆叠（新客首次/新客二次/老客）
const dd=D.daily;
mk('c_daily',{...bs(),legend:{top:0,textStyle:{fontSize:11.5}},
 xAxis:{type:'category',data:dd.map(t=>t.date),...ax,axisLabel:{color:'#5b6478',fontSize:11.5,formatter:v=>v.slice(5)}},
 yAxis:[{type:'value',name:'人数',...ax},{type:'value',name:'金额',...ax,axisLabel:{color:'#5b6478',fontSize:11.5,formatter:v=>wan(v)}}],
 series:[
  {name:'录单量',type:'bar',data:dd.map(t=>t.建档量),itemStyle:{color:'rgba(99,91,255,.35)',borderRadius:[4,4,0,0]},barMaxWidth:30,emphasis:EMPH},
  {name:'来院-新客',type:'bar',stack:'v',data:dd.map(t=>t.来院_新客),itemStyle:{color:C.a2},barMaxWidth:30,emphasis:EMPH},
  {name:'来院-老客',type:'bar',stack:'v',data:dd.map(t=>t.来院_老客),itemStyle:{color:'#7fdcf0'},barMaxWidth:30,emphasis:EMPH},
  {name:'成交-新客',type:'bar',stack:'d',data:dd.map(t=>t.成交_新客),itemStyle:{color:C.ok},barMaxWidth:30,emphasis:EMPH},
  {name:'成交-老客',type:'bar',stack:'d',data:dd.map(t=>t.成交_老客),itemStyle:{color:'#7ee2b8'},barMaxWidth:30,emphasis:EMPH},
  {name:'成交金额',type:'line',smooth:true,yAxisIndex:1,data:dd.map(t=>t.成交总金额),itemStyle:{color:C.warn},lineStyle:{width:2.5,type:'dashed'}}]});

// 媒介 录单 TOP12
const b12=D.src.slice(0,12);
mk('c_src_b',{...bs(),title:{text:'录单量 TOP12',left:'center',top:0,textStyle:{fontSize:13,color:'#5b6478'}},
 xAxis:{type:'category',data:b12.map(s=>s.name),...ax,axisLabel:{color:'#5b6478',fontSize:10.5,rotate:30,interval:0}},
 yAxis:{type:'value',...ax},
 series:[{type:'bar',data:b12.map(s=>s.建档量),itemStyle:{color:C.a,borderRadius:[4,4,0,0]},barMaxWidth:28,emphasis:EMPH}]});

// 媒介 成交金额 TOP12（按总金额排序）
const m12=[...D.src].sort((a,b)=>b.成交总金额-a.成交总金额).slice(0,12).reverse();
mk('c_src_m',{...bs(),title:{text:'成交金额 TOP12',left:'center',top:0,textStyle:{fontSize:13,color:'#5b6478'}},
 grid:{left:10,right:46,top:46,bottom:8,containLabel:true},
 xAxis:{type:'value',...ax,axisLabel:{color:'#5b6478',fontSize:11,formatter:v=>wan(v)}},
 yAxis:{type:'category',data:m12.map(s=>s.name),...ax},
 series:[{type:'bar',data:m12.map(s=>s.成交总金额),itemStyle:{color:p=>p.value>=0?C.ok:C.bad,borderRadius:[0,5,5,0]},emphasis:EMPH,
   label:{show:true,position:'right',formatter:p=>wan(p.value),color:'#5b6478',fontSize:11}}]});

// 咨询师：成交按新客首次/新客二次/老客 堆叠，tooltip 显示合计
const eR=[...D.emp].reverse();
mk('c_emp',{...bs(),
 tooltip:{trigger:'axis',axisPointer:{type:'shadow'},formatter:function(ps){
   var n=ps[0].name, t=(D.emp.find(function(x){return x.name===n;})||{});
   var s='<b>'+n+'</b><br/>';
   ps.forEach(function(p){ if(p.value>0) s+=p.marker+p.seriesName.replace('成交-','')+'：'+p.value+'<br/>'; });
   s+='<b>成交人数合计：'+(t.成交_总人数||0)+'</b><br/>';
   s+='来院合计：'+(t.来院_总人数||0)+' ｜ 录单：'+(t.建档量||0)+'<br/>';
   s+='成交金额：'+((t.成交总金额||0).toLocaleString('zh-CN'))+' 元';
   return s;
 }},
 legend:{top:0,textStyle:{fontSize:11.5}},
 grid:{left:10,right:74,top:46,bottom:8,containLabel:true},
 xAxis:{type:'value',...ax,axisLabel:{color:'#5b6478',fontSize:11}},
 yAxis:{type:'category',data:eR.map(e=>e.name),...ax},
 series:[
  {name:'成交-新客首次',type:'bar',stack:'c',data:eR.map(e=>e.成交_新客首次),itemStyle:{color:C.ok},emphasis:EMPH},
  {name:'成交-新客二次',type:'bar',stack:'c',data:eR.map(e=>e.成交_新客二次),itemStyle:{color:'#7ee2b8'},emphasis:EMPH},
  // label 挂在堆叠最后一段，position:right 即整条柱子末端
  {name:'成交-老客',type:'bar',stack:'c',data:eR.map(e=>e.成交_老客),itemStyle:{color:C.a2},emphasis:EMPH,
   label:{show:true,position:'right',distance:6,
     formatter:function(p){var t=eR[p.dataIndex];return t.成交_总人数>0?(t.成交_总人数+' 人'):'';},
     color:'#2b3247',fontSize:11.5,fontWeight:600}}]});

/* ============ 图表 ↔ 表格 联动高亮 ============ */
function findRow(tableId, name){
  const t=document.getElementById(tableId); if(!t) return null;
  return Array.from(t.querySelectorAll('tr[data-name]')).find(x=>x.getAttribute('data-name')===name) || null;
}
function clearRows(tableId){
  const t=document.getElementById(tableId); if(!t) return;
  t.querySelectorAll('tr.rowhl').forEach(x=>x.classList.remove('rowhl'));
}
function hlRow(tableId, name){
  clearRows(tableId);
  const tr=findRow(tableId,name);
  // 只高亮，不自动滚动页面
  if(tr) tr.classList.add('rowhl');
}
function nameToIndex(c, nm){
  const opt=c.getOption(); let cats=[];
  (opt.xAxis||[]).forEach(a=>{ if(a.data&&a.data.length) cats=cats.concat(a.data); });
  (opt.yAxis||[]).forEach(a=>{ if(a.data&&a.data.length) cats=cats.concat(a.data); });
  return cats.indexOf(nm);
}
function hlChart(cid, name, withTip){
  const c=CH[cid]; if(!c) return;
  const i=nameToIndex(c,name);
  if(i>-1){
    c.dispatchAction({type:'highlight',seriesIndex:0,dataIndex:i});
    // withTip 仅由「表格行悬停」触发（鼠标在表格上，不会与图表内交互打架，也就不残留）
    if(withTip) c.dispatchAction({type:'showTip',seriesIndex:0,dataIndex:i});
  }
}
function unhlCharts(ids, withTip){
  ids.forEach(cid=>{
    const c=CH[cid]; if(!c) return;
    c.dispatchAction({type:'downplay'});
    if(withTip) c.dispatchAction({type:'hideTip'});   // 只在鼠标离开图表时隐藏 tooltip
  });
}
/* 同组联动：鼠标指向任一张图的柱子 → 同组所有图表 + 表格对应行 一起高亮
   （某张图里没有这个媒介时，nameToIndex 返回 -1，自动跳过不高亮） */
function hlChart(cid, name, withTip){
  const c=CH[cid]; if(!c) return;
  const i=nameToIndex(c,name);
  if(i>-1){
    c.dispatchAction({type:'highlight',seriesIndex:0,dataIndex:i});
    if(withTip) c.dispatchAction({type:'showTip',seriesIndex:0,dataIndex:i});  // 联动显示该图自己的数值
  }
}
function unhlCharts(ids){
  ids.forEach(cid=>{
    const c=CH[cid]; if(!c) return;
    c.dispatchAction({type:'downplay'});
    c.dispatchAction({type:'hideTip'});
  });
}
function bindGroup(chartIds, tableId){
  // ① 图表 → 表格 + 同组其它图表（同时显示各自的数值）
  chartIds.forEach(cid=>{
    const c=CH[cid]; if(!c) return;
    const onOver=p=>{
      if(!p || p.name===undefined) return;
      hlRow(tableId, p.name);
      unhlCharts(chartIds);                          // 先清掉旧的高亮/数值框
      chartIds.forEach(o=>hlChart(o, p.name, true)); // 同组全部（含自己）亮起并显示数值
    };
    const onOut=()=>{ clearRows(tableId); unhlCharts(chartIds); };
    c.on('mouseover', onOver);
    c.on('mouseout', onOut);
    c.getZr().on('globalout', onOut);               // 鼠标离开整张图 → 一并收掉
  });
  // ② 表格 → 同组全部图表（先清旧高亮，避免「该媒介不在图里」时残留）
  const t=document.getElementById(tableId); if(!t) return;
  Array.from(t.querySelectorAll('tr[data-name]')).forEach(tr=>{
    tr.addEventListener('mouseenter', ()=>{
      unhlCharts(chartIds);
      tr.classList.add('rowhl');
      const nm=tr.getAttribute('data-name');
      chartIds.forEach(cid=>hlChart(cid, nm));
    });
    tr.addEventListener('mouseleave', ()=>{
      tr.classList.remove('rowhl');
      unhlCharts(chartIds);
    });
  });
}
bindGroup(['c_src_b','c_src_m'],'tbl_src');
bindGroup(['c_emp'],'tbl_emp');
bindGroup(['c_daily'],'tbl_daily');

window.addEventListener('resize',()=>{document.querySelectorAll('.chart').forEach(el=>{const i=echarts.getInstanceByDom(el);if(i)i.resize();});});
</script></body></html>
"""


if __name__ == "__main__":
    main()
