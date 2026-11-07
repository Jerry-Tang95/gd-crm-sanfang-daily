# -*- coding: utf-8 -*-
"""生成「三方营销」专项单文件 HTML 报告"""
import datetime as _dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
# 默认读当月 sanfang.json、写日报主文件；月报重出时用环境变量指到归档 json / 独立文件名
SRC = os.environ.get("SANFANG_SRC") or os.path.join(HERE, "data", "analysis", "sanfang.json")
ECHARTS = os.path.join(HERE, "assets", "echarts.min.js")  # [portable] 图表库随仓库分发
OUT_HTML = os.environ.get("REPORT_OUT") or os.path.join(HERE, "三方营销媒介分析报告.html")



def main():
    A = json.load(open(SRC, encoding="utf-8"))
    dates = A["dates"]
    # 窗口不跨月，月初第一天时窗口可能只有 1 天 → 没有「前日」，环比显示 "—"
    latest = dates[-1]
    prev = dates[-2] if len(dates) > 1 else None
    _w0 = A.get("window") or {}
    _ndays = (_dt.date.fromisoformat(latest) - _dt.date.fromisoformat(_w0.get("start") or dates[0])).days + 1
    trends = {t["date"]: t for t in A["total_trend"]}

    def g(dt, f):
        return trends.get(dt, {}).get(f, 0) or 0

    def pct(a, b):
        if not b:
            return "—"
        v = (a - b) / b * 100
        return f"{v:+.0f}%"

    # 合计以 CRM 区间报表为准（window_totals）；没有就用逐日累加兜底
    _keys = ["建档量", "预约量", "一级预约量",
             "来院_新客首次", "来院_新客二次", "来院_新客", "来院_老客", "来院_总人数",
             "成交_新客首次", "成交_新客二次", "成交_新客", "成交_老客", "成交_总人数",
             "金额_新客", "金额_老客", "成交总金额"]
    if A.get("window_totals"):
        tot = {f: (A["window_totals"].get(f) or 0) for f in _keys}
    else:
        tot = {f: sum(t.get(f, 0) or 0 for t in A["total_trend"]) for f in _keys}
    conv = tot["成交_总人数"] / tot["建档量"] * 100 if tot["建档量"] else 0
    aov = tot["成交总金额"] / tot["成交_总人数"] if tot["成交_总人数"] else 0

    srcs = sorted(A["src_total"], key=lambda x: -x["成交总金额"])
    for s in srcs:
        s["转化率"] = s["成交_总人数"] / s["建档量"] * 100 if s["建档量"] else 0
        s["客单价"] = s["成交总金额"] / s["成交_总人数"] if s["成交_总人数"] else 0
    srcs_by_build = sorted(A["src_total"], key=lambda x: -x["建档量"])

    emps = sorted(A["emp_total"], key=lambda x: -x["成交总金额"])
    for e in emps:
        e["转化率"] = e["成交_总人数"] / e["建档量"] * 100 if e["建档量"] else 0
        e["客单价"] = e["成交总金额"] / e["成交_总人数"] if e["成交_总人数"] else 0

    # ---- 洞察 ----
    top3_build = srcs_by_build[:3]
    t3_b = sum(s["建档量"] for s in top3_build)
    t3_d = sum(s["成交_总人数"] for s in top3_build)
    top3_money = srcs[:3]
    star = [s for s in srcs if s["成交_总人数"] >= 2 and s["建档量"] >= 5 and s["转化率"] <= 100]
    star_sorted = sorted(star, key=lambda x: -x["转化率"])[:5]
    # 转化率 >100%：来院/成交超过当期建档，多为历史客户兑现
    over = [s for s in srcs if s["转化率"] > 100 and s["成交_总人数"] >= 2]

    _overall = ("录单海量、转化偏低" if conv < 2.5
                else ("转化处于常态区间" if conv < 4 else "转化好于常态"))
    # 新老客拆分（全部现算，禁止写死）
    _v_n, _v_o = tot["来院_新客"], tot["来院_老客"]
    _d_n, _d_o = tot["成交_新客"], tot["成交_老客"]
    _v_t = tot["来院_总人数"]
    _m_n, _m_o = tot["金额_新客"], tot["金额_老客"]
    _n_share = _v_n / _v_t * 100 if _v_t else 0
    _n_conv = _d_n / _v_n * 100 if _v_n else 0
    _o_conv = _d_o / _v_o * 100 if _v_o else 0
    _m_n_share = _m_n / tot["成交总金额"] * 100 if tot["成交总金额"] else 0
    ins = [
        f'<b>整体：三方营销「{_overall}」。</b>{_ndays} 天录单 <b>{tot["建档量"]:,.0f}</b> 个、'
        f'来院 <b>{_v_t:,.0f}</b> 人（新客 {_v_n:,.0f} / 老客 {_v_o:,.0f}），'
        f'成交 <b>{tot["成交_总人数"]:,.0f}</b> 人（新客 {_d_n:,.0f} / 老客 {_d_o:,.0f}，区间内按人去重），'
        f'转化率 <b>{conv:.2f}%</b>，业绩 {tot["成交总金额"]:,.0f} 元，客单价 {aov/10000:.1f} 万。',
        f'<b>新老客结构：</b>来院以{"新客" if _n_share >= 50 else "老客"}为主'
        f'（新客 {_v_n:,.0f} 人占 {_n_share:.0f}% / 老客 {_v_o:,.0f} 人）；'
        f'来院→成交 转化 新客 <b>{_n_conv:.1f}%</b>、老客 <b>{_o_conv:.1f}%</b>。'
        f'新客再拆两层：首次到院 {tot["来院_新客首次"]:,.0f} 人仅成交 {tot["成交_新客首次"]:,.0f} 人，'
        f'二次到院 {tot["来院_新客二次"]:,.0f} 人成交 {tot["成交_新客二次"]:,.0f} 人。'
        f'按金额：新客 {_m_n:,.0f} 元（{_m_n_share:.0f}%）、老客 {_m_o:,.0f} 元。'
        + ('<span class="warn">新客首次 0 人成交 —— 首诊当天下单几乎为零，业绩靠二次跟进与老客复购。</span>'
           if tot["成交_新客首次"] == 0 else
           ('<span class="warn">老客到院转化明显高于新客 —— 复购比首诊更容易出单。</span>'
            if _o_conv > _n_conv * 1.5 else '')),
        f'<b>录单前三名基本不产业绩。</b>{"、".join(s["name"] for s in top3_build)} 合计录单 {t3_b:,.0f} 个（占三方营销 {t3_b/tot["建档量"]*100:.0f}%），'
        f'却只成交 {t3_d:,.0f} 人。<span class="warn">纯流量、无线索质量感 —— 建议核实这几家的线索真实性与重复度。</span>',
        f'<b>业绩靠「小而精」的几家撑起来。</b>{"、".join(f"{s["name"]}（{s["成交总金额"]/10000:.1f}万）" for s in top3_money)} '
        f'合计 {sum(s["成交总金额"] for s in top3_money)/10000:.1f} 万，占三方营销业绩 '
        f'{sum(s["成交总金额"] for s in top3_money)/tot["成交总金额"]*100:.0f}%。',
    ]
    if star_sorted:
        ins.append(
            f'<b>最值得加投的媒介（转化率优先）：</b>' +
            "、".join(f'{s["name"]} <b>{s["转化率"]:.1f}%</b>' for s in star_sorted[:5]) + "。")
    if over:
        ins.append(
            '<b>另有「历史客户成交型」媒介：</b>' +
            "、".join(f'{s["name"]}（成交 {s["成交_总人数"]:.0f} 人 / 当期录单仅 {s["建档量"]:.0f}）' for s in over[:4]) +
            ' —— 转化率超 100%，说明成交主要来自历史存量客户，不宜直接按新流量效率衡量。')
    # 公共账号（三方公用）：动态取，别写死
    pub = next((e for e in emps if "三方公用" in e["name"]), None)
    pub_txt = (
        f'「三方公用」录单 {pub["建档量"]:,.0f} 个但 0 成交 —— 属公共账号，非真人跟进，统计时建议单列。'
        if pub else '')
    ins.append(
        f'<b>咨询师侧：</b>{emps[0]["name"]} 业绩最高（{emps[0]["成交总金额"]:,.0f} 元 / 成交 {emps[0]["成交_总人数"]:.0f} 人）；'
        + pub_txt)

    # ---- 数据范围（月累计口径：当月 1 号 ~ 前一天）----
    win = A.get("window") or {}
    w_start = win.get("start") or (dates[0] if dates else "")
    q_start = win.get("queryable_start") or w_start
    n_arch = win.get("archive_days") or 0
    dd = A.get("dedup") or {}
    crm = A.get("crm_segment") or {}
    _qd = __import__("datetime").date.fromisoformat(q_start)
    _pre_end = (_qd - __import__("datetime").timedelta(days=1)).isoformat()
    _d20raw = next((r.get("建档量") or 0 for r in A["total_trend"] if r["date"] == dd.get("day")), 0)

    _src_row = ('<b>CRM「网电咨询师媒介/渠道报表」区间导出</b>'
                '（媒介类型＝三方营销，维度＝媒介+咨询师，时间区间＝当月1号~昨天）')
    if n_arch > 0:
        _how_row = (f'统计口径＝<b>当月 1 号 ~ 前一天</b>。CRM 只保留当前统计周期内的明细：'
                    f'把 {w_start} ~ {latest} 整段提交查询，返回的行数与数值和 '
                    f'{q_start} ~ {latest} <b>完全一致</b>（已逐格实测）—— 月初记录已被并入 {q_start} 的积压里')
    else:
        _how_row = (f'统计口径＝<b>当月 1 号 ~ 前一天</b>。本次窗口自 {w_start} 起算，'
                    f'CRM 当前可查段同为 {q_start} ~ {latest}，<b>窗口内每一天都有完整明细</b>，'
                    f'不存在被归并或查不到的日期')
    _stat_row = ('报表明细行<b>逐条加总</b>，不做推算、不补录；'
                 '来院/成交按<b>人去重</b>（同一人跨天到院/成交只计一次）')
    scope_tbl = (
        '<table class="scope-tbl" style="min-width:0"><thead><tr><th style="text-align:left">项目</th>'
        '<th style="text-align:left">内容</th></tr></thead><tbody>'
        f'<tr><td style="text-align:left">统计区间</td><td style="text-align:left">'
        f'<b>{w_start} ~ {latest}</b>（{_ndays} 天）</td></tr>'
        f'<tr><td style="text-align:left">区间怎么来的</td><td style="text-align:left">{_how_row}</td></tr>'
        f'<tr><td style="text-align:left">数据来源</td><td style="text-align:left">{_src_row}</td></tr>'
        f'<tr><td style="text-align:left">统计方式</td><td style="text-align:left">{_stat_row}</td></tr>'
        '<tr><td style="text-align:left">区间合计</td><td style="text-align:left">'
        f'录单 {tot["建档量"]:,.0f} ｜ 来院 {tot["来院_总人数"]:,.0f} 人 ｜ '
        f'成交 {tot["成交_总人数"]:,.0f} 人 ｜ 业绩 {tot["成交总金额"]:,.2f} 元</td></tr>'
        '</tbody></table>')

    if n_arch > 0:
        scope_note = (f'<b>为什么逐日明细只有 {len(dates)} 天</b>：CRM 对 '
                      f'「{w_start} ~ {latest}」与「{q_start} ~ {latest}」返回的是同一批数据（逐格一致），'
                      f'说明 {q_start} 之前的记录已经被归并到 {q_start} 那天的积压里。'
                      f'所以本报告<b>只统计 CRM 当前实际持有的明细</b>，{w_start} ~ {_pre_end} 不单独累加，'
                      '否则同一批客户会被算两遍。')
    else:
        _nd0 = A.get("daily_sum") or {}
        _has_gap = any(round(tot[k] - _nd0.get(k, tot[k]))
                       for k in ("建档量", "来院_总人数", "成交_总人数"))
        scope_note = (f'<b>本次逐日明细共 {len(dates)} 天</b>：统计窗口从 {w_start} 开始，'
                      f'CRM 当前可查段同为 {q_start} ~ {latest}，两者完全重合，'
                      f'<b>没有查不到或被归并的日期</b>，未做任何补录或推算。'
                      + ('来院/成交按人去重，区间合计会略低于逐日相加（见下方对账表）。'
                         if _has_gap else '区间合计＝逐日相加。'))
    if dd.get("day"):
        scope_note += (f'<br><b>关于 {dd["day"]}</b>：当天录单 {_d20raw:,.0f}（日常约 100~190，约 {dd["ratio"]:.0f} 倍），'
                       f'里面约 {dd["amount"]:,.0f} 条是月初客户被重新挂了日期，其余是当天真实新增。'
                       f'这也是为什么必须按 CRM 当前口径取数、不能叠加月初存档。')
    scope_note += ('<br><b>怎么复核</b>：在 CRM 里把区间设成当月1号~昨天导出这份报表，'
                   '录单/来院/成交/业绩应当与本报告完全一致（差异只可能来自导出之后的实时修订）。')

    # 顶部与逐日表脚的说明：随窗口动态生成，禁止写死日期/数字
    if n_arch > 0:
        head_note = ('<b>统计口径：当月 1 号 ~ 前一天</b> —— 只用 CRM 现在能导出的数据，不掺存档、不推算。'
                     f'<b>{w_start} ~ {_pre_end} 的记录已被 CRM 并入 {q_start}</b>，'
                     '故不单独累加（否则同一批客户算两遍）。')
    else:
        head_note = ('<b>统计口径：当月 1 号 ~ 前一天</b> —— 只用 CRM 现在能导出的数据，不掺存档、不推算。'
                     f'本次窗口 {w_start} ~ {latest} 全部落在 CRM 可查段内（{q_start} 起），'
                     '<b>无需排除任何日期</b>。')
    _dsv = A.get("daily_sum") or {}
    if len(dates) > 1:
        daily_tail = ('逐日值取自每日单日报表，与区间报表可能有 1~2 条的差异（CRM 侧后续改数）；'
                      f'每天「来院」是当天到院人数，跨日相加会重复计人，所以逐日之和'
                      f'（{_dsv.get("来院_总人数", 0):,.0f} 人次）会略高于区间合计的 '
                      f'{tot["来院_总人数"]:,.0f} 人（按人去重）。')
    else:
        daily_tail = ('本次窗口只有 1 天，逐日值与区间合计取自同一份报表，两者完全一致，'
                      '不存在跨日重复计人的问题。')

    # 逐日明细（CRM 实际持有的可查段）
    _rows = []
    _prev_j = None
    for r in A["total_trend"]:
        if r["date"] not in dates:
            continue
        _j = r.get("建档量") or 0
        _mom = "—" if _prev_j in (None, 0) else f'{(_j - _prev_j) / _prev_j * 100:+.1f}%'
        _mark = ' *' if r["date"] == dd.get("day") else ''
        _rows.append(
            f'<tr><td style="text-align:left">{r["date"]}{_mark}</td><td>{_j:,.0f}</td>'
            f'<td>{r.get("来院_总人数") or 0:,.0f}</td><td>{r.get("成交_总人数") or 0:,.0f}</td>'
            f'<td>{(r.get("成交总金额") or 0):,.0f}</td><td>{_mom}</td></tr>')
        _prev_j = _j
    _ds = A.get("daily_sum") or {}
    _dsum = [f'{_ds.get(k, 0):,.0f}' for k in ("建档量", "来院_总人数", "成交_总人数", "成交总金额")]
    # 差额写成「逐行相加 → 合计」需要加减的量（带符号）：合计 = 逐行相加 + diff
    _diff = [round(tot[k] - _ds.get(k, 0)) for k in ("建档量", "来院_总人数", "成交_总人数", "成交总金额")]

    def _sg(x):
        if not x:
            return "0"
        return (f"+{x:,.0f}" if x > 0 else f"−{abs(x):,.0f}")

    _foot = (f'<tfoot><tr><td style="text-align:left">逐行相加</td><td>{_dsum[0]}</td><td>{_dsum[1]}</td>'
             f'<td>{_dsum[2]}</td><td>{_dsum[3]}</td><td>—</td></tr>'
             f'<tr><td style="text-align:left">差异（按人去重/改数）</td>'
             + "".join(f'<td>{_sg(x)}</td>' for x in _diff)
             + '<td>—</td></tr>'
             f'<tr><td style="text-align:left"><b>合计</b></td><td><b>{tot["建档量"]:,.0f}</b></td>'
             f'<td><b>{tot["来院_总人数"]:,.0f}</b></td><td><b>{tot["成交_总人数"]:,.0f}</b></td>'
             f'<td><b>{tot["成交总金额"]:,.0f}</b></td><td>—</td></tr></tfoot>')
    daily_tbl = (
        '<table style="min-width:0"><thead><tr><th style="text-align:left">日期</th><th>录单</th>'
        '<th>来院（人）</th><th>成交（人）</th><th>业绩（元）</th><th>录单环比</th></tr></thead><tbody>'
        + "".join(_rows) + _foot + '</table>'
        + (f'<div style="font-size:12px;color:#8a6c33;margin-top:6px">'
           f'* {dd["day"]} 为 CRM 积压归并日：当天录单 {_d20raw:,.0f} 里约 {dd["amount"]:,.0f} 条是月初客户被重挂日期，'
           f'其余为当天真实新增。逐行相加与合计的差额来自 CRM 按人去重（同一人跨天重复到院/成交只计一次）及事后改数。</div>'
           if dd.get("day") else ''))

    # ---- KPI ----
    def kpi(label, val, delta="", unit="", split=""):
        d = f'<div class="d">{delta}</div>' if delta else ""
        s = f'<div class="sp">{split}</div>' if split else ""
        return f'<div class="kpi"><div class="k">{label}</div><div class="v">{val}{unit}</div>{s}{d}</div>'

    def sp_cell(nc, ol):
        """新客 / 老客 拆分（速览卡专用）"""
        return (f'<span class="na">新客 <b>{nc:,.0f}</b></span>'
                f'<span class="sep">·</span>'
                f'<span class="ol">老客 <b>{ol:,.0f}</b></span>')

    # 日报最新日通常是「昨天」；月报/区间报告的最新日不是昨天 → 改叫「最新日」，避免读着别扭
    _yest = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    _dw = "昨日" if latest == _yest else "最新日"
    _dlabel = (lambda lbl: f'环比 {lbl}') if prev else (lambda lbl: '新周期首日 · 无可比日')
    kpi_now = "".join([
        kpi(f"{_dw}录单", f"{g(latest,'建档量'):,.0f}", _dlabel(pct(g(latest,"建档量"),g(prev,"建档量")))),
        kpi(f"{_dw}来院", f"{g(latest,'来院_总人数'):,.0f}", _dlabel(pct(g(latest,"来院_总人数"),g(prev,"来院_总人数"))),
            split=sp_cell(g(latest,"来院_新客"), g(latest,"来院_老客"))),
        kpi(f"{_dw}成交", f"{g(latest,'成交_总人数'):,.0f}", _dlabel(pct(g(latest,"成交_总人数"),g(prev,"成交_总人数"))),
            split=sp_cell(g(latest,"成交_新客"), g(latest,"成交_老客"))),
        kpi(f"{_dw}业绩", f"{g(latest,'成交总金额'):,.0f}", _dlabel(pct(g(latest,"成交总金额"),g(prev,"成交总金额"))), " 元"),
    ])
    kpi_tot = "".join([
        kpi(f"{_ndays}天录单", f"{tot['建档量']:,.0f}"),
        kpi(f"{_ndays}天来院", f"{tot['来院_总人数']:,.0f}", "按人去重",
            split=sp_cell(tot["来院_新客"], tot["来院_老客"])),
        kpi(f"{_ndays}天成交", f"{tot['成交_总人数']:,.0f}", "按人去重",
            split=sp_cell(tot["成交_新客"], tot["成交_老客"])),
        kpi(f"{_ndays}天业绩", f"{tot['成交总金额']/10000:,.1f} 万", f"转化率 {conv:.2f}% · 客单价 {aov/10000:.1f}万"),
    ])

    def rk(i):
        c = "g1" if i == 1 else ("g2" if i == 2 else ("g3" if i == 3 else ""))
        return f'<span class="rk {c}">{i}</span>'

    def split_tds(x):
        """来院5档 + 成交5档
        data-col 标记「档位」(0新客首次/1新客二次/2新客/3老客/4总人数)
        → 鼠标停在来院某档时，成交的同一档同时高亮（跨组同档联动）"""
        v = [x['来院_新客首次'], x['来院_新客二次'], x['来院_新客'], x['来院_老客'], x['来院_总人数']]
        d = [x['成交_新客首次'], x['成交_新客二次'], x['成交_新客'], x['成交_老客'], x['成交_总人数']]

        def tds(vals, grp):
            out = []
            for i, val in enumerate(vals):
                cls = " class='tot'" if i == 4 else ""
                out.append(f"<td data-col='{i}' data-grp='{grp}'{cls}>{val:,.0f}</td>")
            return "".join(out)

        return tds(v, 'v') + tds(d, 'd')

    rows_build = "".join(
        f"<tr><td>{rk(i+1)}</td><td>{s['name']}</td><td class='tot'>{s['建档量']:,.0f}</td>"
        f"{split_tds(s)}<td class='tot'>{s['成交总金额']:,.0f}</td></tr>"
        for i, s in enumerate(srcs_by_build[:20]))
    rows_money = "".join(
        f"<tr><td>{rk(i+1)}</td><td>{s['name']}</td><td class='tot'>{s['建档量']:,.0f}</td>"
        f"{split_tds(s)}<td class='tot'>{s['成交总金额']:,.0f}</td></tr>"
        for i, s in enumerate(srcs[:20]))
    rows_emp = "".join(
        f"<tr><td>{rk(i+1)}</td><td>{e['name']}</td><td class='tot'>{e['建档量']:,.0f}</td>"
        f"{split_tds(e)}<td class='tot'>{e['成交总金额']:,.0f}</td></tr>"
        for i, e in enumerate(emps))
    # 全量媒介明细（按录单量降序）
    rows_all = "".join(
        f"<tr><td>{s['name']}</td><td class='tot'>{s['建档量']:,.0f}</td>{split_tds(s)}"
        f"<td class='tot'>{s['成交总金额']:,.0f}</td></tr>"
        for s in srcs_by_build)

    # ---- 表格合计行（tfoot）----
    _FTK = ["建档量", "来院_新客首次", "来院_新客二次", "来院_新客", "来院_老客", "来院_总人数",
            "成交_新客首次", "成交_新客二次", "成交_新客", "成交_老客", "成交_总人数", "成交总金额"]

    def ft_tds(x):
        v = [x['来院_新客首次'], x['来院_新客二次'], x['来院_新客'], x['来院_老客'], x['来院_总人数']]
        d = [x['成交_新客首次'], x['成交_新客二次'], x['成交_新客'], x['成交_老客'], x['成交_总人数']]
        cells = lambda vals, grp: "".join(
            f"<td class='ft' data-col='{i}' data-grp='{grp}'>{val:,.0f}</td>" for i, val in enumerate(vals))
        return cells(v, 'v') + cells(d, 'd')

    def sum_rows(rows):
        return {k: sum((r.get(k) or 0) for r in rows) for k in _FTK}

    def foot_row(label, x, sub=False, colspan=2):
        cls = ' class="sub"' if sub else ''
        return (f'<tr{cls}>'
                f'<td class="ft" colspan="{colspan}" style="text-align:left">{label}</td>'
                f'<td class="ft">{x["建档量"]:,.0f}</td>{ft_tds(x)}'
                f'<td class="ft">{x["成交总金额"]:,.0f}</td></tr>')

    def ft_note(x):
        """表内逐行相加与区间报表合计不一致时给出说明（设计上应完全一致）"""
        dv, dvv = x["建档量"] - tot["建档量"], x["来院_总人数"] - tot["来院_总人数"]
        dd, dm = x["成交_总人数"] - tot["成交_总人数"], x["成交总金额"] - tot["成交总金额"]
        if all(abs(y) < 0.5 for y in (dv, dvv, dd, dm)):
            return ''
        return (f'<div class="ft-note">* 本表逐行相加与区间报表合计有差（建档 {dv:+,.0f} / 来院 {dvv:+,.0f} / '
                f'成交 {dd:+,.0f} / 金额 {dm:+,.0f}），属 CRM 按人去重或事后改数，报告合计以区间报表为准。</div>')

    _top_b, _top_m = srcs_by_build[:20], srcs[:20]
    _sb, _sm, _se, _sa = sum_rows(_top_b), sum_rows(_top_m), sum_rows(emps), sum_rows(srcs_by_build)
    foot_build = ('<tfoot>'
                  + foot_row(f'本表 TOP{len(_top_b)} 小计', _sb, sub=True)
                  + foot_row(f'全部 {len(srcs)} 个媒介合计', tot) + '</tfoot>')
    foot_money = ('<tfoot>'
                  + foot_row(f'本表 TOP{len(_top_m)} 小计', _sm, sub=True)
                  + foot_row(f'全部 {len(srcs)} 个媒介合计', tot) + '</tfoot>')
    foot_emp = '<tfoot>' + foot_row(f'合计（{len(emps)} 位咨询师）', tot) + '</tfoot>'
    foot_all = '<tfoot>' + foot_row(f'合计（{len(srcs)} 个媒介）', tot, colspan=1) + '</tfoot>'
    foot_note_emp, foot_note_all = ft_note(_se), ft_note(_sa)

    # 五档恒等式体检：跨天按人去重后，「新客首次+新客二次」可能大于「新客」，
    # 「新客+老客」也可能与「总人数」差 1~2 人（同一人跨天以不同身份出现只计一次）。
    _idv1 = (tot["来院_新客首次"] + tot["来院_新客二次"]) - tot["来院_新客"]
    _idv2 = (tot["来院_新客"] + tot["来院_老客"]) - tot["来院_总人数"]
    _idd1 = (tot["成交_新客首次"] + tot["成交_新客二次"]) - tot["成交_新客"]
    _idd2 = (tot["成交_新客"] + tot["成交_老客"]) - tot["成交_总人数"]
    if any(abs(x) >= 0.5 for x in (_idv1, _idv2, _idd1, _idd2)):
        _id_parts = []
        if abs(_idv1) >= 0.5 or abs(_idv2) >= 0.5:
            _id_parts.append(f'来院：首次 {tot["来院_新客首次"]:,.0f} + 二次 {tot["来院_新客二次"]:,.0f} '
                             f'= {tot["来院_新客首次"]+tot["来院_新客二次"]:,.0f}，但「新客」列 {tot["来院_新客"]:,.0f}；'
                             f'新客 {tot["来院_新客"]:,.0f} + 老客 {tot["来院_老客"]:,.0f} '
                             f'= {tot["来院_新客"]+tot["来院_老客"]:,.0f}，总人数 {tot["来院_总人数"]:,.0f}')
        if abs(_idd1) >= 0.5 or abs(_idd2) >= 0.5:
            _id_parts.append(f'成交：首次 {tot["成交_新客首次"]:,.0f} + 二次 {tot["成交_新客二次"]:,.0f} '
                             f'= {tot["成交_新客首次"]+tot["成交_新客二次"]:,.0f}，但「新客」列 {tot["成交_新客"]:,.0f}；'
                             f'新客 {tot["成交_新客"]:,.0f} + 老客 {tot["成交_老客"]:,.0f} '
                             f'= {tot["成交_新客"]+tot["成交_老客"]:,.0f}，总人数 {tot["成交_总人数"]:,.0f}')
        id_note = ('<div class="ft-note">* <b>五档相加不等于上一档，是正常的</b>：'
                   + '；'.join(_id_parts)
                   + '。原因＝<b>按人去重</b>——同一个人跨天分别以「新客首次」和「新客二次」到院（或在别处已是老客），'
                     '只会在「总人数」里计 1 次，但两个明细档各计 1 次。'
                     '看结构用明细档，看规模一律用「总人数」列。</div>')
    else:
        id_note = ''

    data_js = json.dumps({
        "dates": dates,
        "totalTrend": A["total_trend"],
        "srcs": srcs,                 # 按金额降序
        "srcsByBuild": srcs_by_build, # 按建档降序
        "emps": emps,
        "srcTrend": A["src_trend"],
        "latest": latest,
    }, ensure_ascii=False)

    note = (
        "<b>数据范围</b>：仅统计系统中 <b>媒介类型 = 三方营销</b> 的数据，"
        "下钻到该类型下的各具体媒介（媒介来源）+ 网电咨询师。"
        "报表维度＝媒介+咨询师，组织机构＝广州广大医院。<br>"
        "<b>录单量</b>＝系统「建档量」字段（网电录单/建档客户数）。<br>"
        "<b>来院人数 / 成交人数</b> 均按五档拆分：<b>新客首次 · 新客二次 · 新客 · 老客 · 总人数</b>"
        "（新客＝新客首次＋新客二次；总人数＝新客＋老客）。"
        "**该恒等式在单日严格成立**；区间合计按人去重后，同一人跨天身份不同只计一次，"
        "会出现「首次+二次 > 新客」或「新客+老客 ≠ 总人数」1~2 人的差，属正常，规模一律以「总人数」列为准。<br>"
        "<b>成交金额</b>＝所录消费单业绩合计（含退款冲账，个别媒介会出负数，属正常）。"
        "「三方公用(13125)」为公共账号，仅有录单无成交归属。<br>"
        "<b>转化率</b>＝成交人数 ÷ 录单量；<b>客单价</b>＝成交金额 ÷ 成交人数。<br>"
        "⚠️ 本报告所有指标按<b>明细行逐条加总</b>统计，未使用报表自带的类型汇总行（该行成交总人数字段有误，会明显偏小）。<br>"
        "<b>数据口径</b>：总量、媒介表、咨询师表全部直接取自 <b>CRM 区间报表</b>"
        "（与在系统里手动导出同一区间完全一致），不做任何推算或跨期合并。"
        "逐日曲线来自每日单日报表，反映当天真实发生量。<br>"
        "<b>为什么区间会变</b>：CRM 只返回「当前统计周期」内的明细，越早的日期越查不到"
        "（2026-10-26 实测：10-19 及以前均返回全零空表）。报告因此每个周期自动缩到可查范围，"
        "宁可少算也不掺入查不到的数据。<br>"
        "<b>证据（可直接反馈 IT）</b>：报表里「媒介类型汇总行」的成交总人数与它自己的分项对不上"
        "（例如列出「新客 4 ＋ 老客 2」，总人数却填 2），而明细行加总与「全院汇总行」完全一致。"
        "所以本报告一律用明细行加总。"
    )

    html = TMPL
    html = html.replace("/*__ECHARTS__*/", open(ECHARTS, encoding="utf-8").read())
    html = html.replace("/*__DATA__*/", "const D = " + data_js + ";")
    # 首页标签用「统计区间」（合计覆盖的范围），不是逐日明细段（后者可能因归并只从月中开始）
    html = html.replace("__RANGE__", f"{_w0.get('start') or dates[0]} ~ {latest}")
    html = html.replace("__INSIGHTS__", "".join(f"<li>{x}</li>" for x in ins))
    html = html.replace("__LATEST__", latest)
    html = html.replace("__DAYWORD__", _dw)
    html = html.replace("__KPI_NOW__", kpi_now)
    html = html.replace("__KPI_TOT__", kpi_tot)
    html = html.replace("__ROWS_BUILD__", rows_build)
    html = html.replace("__ROWS_MONEY__", rows_money)
    html = html.replace("__ROWS_EMP__", rows_emp)
    html = html.replace("__ROWS_ALL__", rows_all)
    html = html.replace("__FOOT_BUILD__", foot_build)
    html = html.replace("__FOOT_MONEY__", foot_money)
    html = html.replace("__FOOT_EMP__", foot_emp)
    html = html.replace("__FOOT_ALL__", foot_all)
    html = html.replace("__FOOT_NOTE_EMP__", foot_note_emp)
    html = html.replace("__FOOT_NOTE_ALL__", foot_note_all)
    html = html.replace("__ID_NOTE__", id_note)
    html = html.replace("__NMEDIA__", str(len(srcs)))
    html = html.replace("__NEMP__", str(len(emps)))
    html = html.replace("__NDAYS__", str(len(dates)))
    html = html.replace("__NOTE__", note)
    html = html.replace("__SCOPE_TBL__", scope_tbl)
    html = html.replace("__SCOPE_NOTE__", scope_note)
    html = html.replace("__HEAD_NOTE__", head_note)
    html = html.replace("__DAILY_TAIL__", daily_tail)
    html = html.replace("__DAILY_TBL__", daily_tbl)

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("报告已生成:", OUT_HTML, os.path.getsize(OUT_HTML), "bytes")
    print(f"三方营销 {w_start}~{latest}: 录单{tot['建档量']:,.0f} 来院{tot['来院_总人数']:,.0f} "
          f"成交{tot['成交_总人数']:,.0f} 业绩{tot['成交总金额']:,.0f} ({len(srcs)}个媒介/{len(emps)}个咨询师)")


TMPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>三方营销 · 媒介数据分析报告</title>
<style>
:root{--bg:#f7f8fb;--card:#fff;--ink:#1a1f36;--sub:#5b6478;--line:#e6e9f0;
--a:#635bff;--a2:#00b8d9;--ok:#12b76a;--warn:#f79009;--bad:#f04438;
--sh:0 1px 2px rgba(16,24,40,.04),0 6px 22px rgba(16,24,40,.07)}
*{box-sizing:border-box}
body{margin:0;color:var(--ink);background:
radial-gradient(1200px 500px at 12% -8%,rgba(99,91,255,.10),transparent 60%),
radial-gradient(900px 420px at 92% 4%,rgba(0,184,217,.09),transparent 55%),var(--bg);
font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1160px;margin:0 auto;padding:34px 22px 70px}
.hero{background:linear-gradient(135deg,#635bff,#7a5cff 45%,#00b8d9);border-radius:20px;padding:26px 28px;color:#fff;box-shadow:0 12px 40px rgba(99,91,255,.28)}
.hero h1{margin:0 0 6px;font-size:25px}
.hero .meta{opacity:.93;font-size:13.5px}
.hero .tag{display:inline-block;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);border-radius:999px;padding:3px 11px;font-size:12.5px;margin-right:8px}
h2{font-size:18px;margin:34px 0 14px;display:flex;align-items:center;gap:9px}
h2 .n{display:inline-flex;width:26px;height:26px;border-radius:9px;background:var(--a);color:#fff;font-size:13px;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(99,91,255,.35)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:var(--sh);margin-bottom:16px;overflow-x:auto}
table{min-width:100%}
thead tr:nth-child(2) th{top:29px}
td.tot{background:#f8f9ff;font-weight:600}
.grp{background:#f2f4fd!important;text-align:center!important;font-weight:700}
.grp.v{color:#0a7ea4}.grp.d{color:#0f8b5f}
/* 跨组同档联动高亮：指着「来院·新客」，把「成交·新客」一起点亮（同一档位跨两组） */
td[data-col]{transition:background .1s}
td.colhl{background:#fff2cc!important;box-shadow:inset 0 0 0 1.5px #efb024}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:13px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:15px 17px;box-shadow:var(--sh)}
.kpi .k{font-size:12.5px;color:var(--sub);margin-bottom:6px}
.kpi .v{font-size:25px;font-weight:700;letter-spacing:-.4px}
.kpi .d{font-size:12.5px;margin-top:5px;color:var(--sub)}
.kpi .sp{font-size:12.8px;margin-top:6px;color:var(--sub);letter-spacing:.2px}
.kpi .sp b{font-weight:700}
.kpi .sp .na b{color:#0a7ea4}
.kpi .sp .ol b{color:#9a4c1a}
.kpi .sp .sep{color:#c3c9d9;margin:0 8px}
td.ft{background:#f4f6ff;font-weight:700;border-top:2px solid #dfe3f5;border-bottom:0}
tr.sub td.ft{background:#fafbff;font-weight:600;color:var(--sub)}
tr.sub td.ft[data-col]{font-weight:600}
.ft-note{font-size:12px;color:#8a6c33;margin-top:6px}
ul.ins{list-style:none;padding:0;margin:0}
ul.ins li{padding:11px 0;border-bottom:1px dashed var(--line);font-size:14.2px}
ul.ins li:last-child{border-bottom:0}
.warn{color:#b54708;background:#fffaeb;border:1px solid #fedf89;border-radius:6px;padding:1px 6px;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13.6px}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
.scope-tbl th,.scope-tbl td{white-space:normal;line-height:1.6}
th:first-child,td:first-child{text-align:left}
th:nth-child(2),td:nth-child(2){text-align:left}
th{background:#fafbff;color:var(--sub);font-weight:600;font-size:12.8px;position:sticky;top:0}
tbody tr:hover{background:#fbfcff}
.rk{display:inline-flex;width:20px;height:20px;border-radius:6px;background:#eef0ff;color:var(--a);font-size:11.5px;align-items:center;justify-content:center;margin-right:7px;font-weight:700}
.rk.g1{background:#fff3cd;color:#8a6100}.rk.g2{background:#e9eef5;color:#4b5a6b}.rk.g3{background:#fdece1;color:#9a4c1a}
.chart{width:100%;height:340px}
.chart.sm{height:290px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:860px){.grid2{grid-template-columns:1fr}}
.scroll{max-height:430px;overflow:auto;border:1px solid var(--line);border-radius:12px}
.scroll table{font-size:13px}.scroll th{top:0}
/* 长表格里的合计行吸底，滚动时也看得见 */
.scroll tfoot td.ft{position:sticky;bottom:0;z-index:3;box-shadow:0 -3px 8px rgba(16,24,40,.07)}
.note{font-size:12.8px;color:var(--sub);background:#fbfcff;border:1px dashed var(--line);border-radius:12px;padding:12px 15px}
.toolbar{display:flex;gap:10px;justify-content:flex-end;margin:0 0 16px}
button{background:var(--a);color:#fff;border:0;border-radius:11px;padding:9px 17px;font-size:13.6px;cursor:pointer;box-shadow:0 5px 16px rgba(99,91,255,.3)}
@media print{.toolbar{display:none}.card,.kpi,.hero{box-shadow:none}.scroll{max-height:none;overflow:visible}body{background:#fff}}
</style>
</head>
<body>
<div class="wrap">
  <div class="toolbar"><button onclick="window.print()">打印 / 导出 PDF</button></div>

  <div class="hero">
    <h1>三方营销 · 媒介数据分析报告</h1>
    <div class="meta">
      <span class="tag">数据区间 __RANGE__</span>
      <span class="tag">媒介类型：三方营销</span>
      <span class="tag">维度：媒介 + 咨询师</span>
      <div style="margin-top:8px">共 __NMEDIA__ 个媒介来源 · __NEMP__ 位网电咨询师 · 数据源自内网 GD-CRM 自动抓取</div>
    </div>
  </div>

  <h2><span class="n">01</span>核心结论</h2>
  <div class="note" style="margin-bottom:14px;background:#fffaeb;border-color:#fedf89;color:#7a4b00">
    <b>数据口径已修正</b>：成交人数按「明细逐条加总」统计。报表自带的「媒介类型汇总行」成交总人数字段有误（会明显偏小），本报告已改用明细口径。
    来院 / 成交 均已按 <b>新客首次 · 新客二次 · 新客 · 老客 · 总人数</b> 五档拆分。
  </div>
  <div class="card"><ul class="ins">__INSIGHTS__</ul></div>

  <h2><span class="n">02</span>__DAYWORD__速览 · __LATEST__</h2>
  <div class="kpis">__KPI_NOW__</div>
  <div style="height:8px"></div>
  <div class="kpis">__KPI_TOT__</div>

  <h2><span class="n">03</span>各媒介录单情况（TOP20）</h2>
  <div class="card"><div id="c_build" class="chart"></div></div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th rowspan="2">#</th><th rowspan="2">媒介</th><th rowspan="2">录单量</th>
          <th colspan="5" class="grp v">来院人次</th>
          <th colspan="5" class="grp d">成交人数</th>
          <th rowspan="2">成交金额</th>
        </tr>
        <tr>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
        </tr>
      </thead>
      <tbody>__ROWS_BUILD__</tbody>
      __FOOT_BUILD__
    </table>
    __ID_NOTE__
  </div>

  <h2><span class="n">04</span>各媒介成交情况（TOP20 · 按金额）</h2>
  <div class="card"><div id="c_money" class="chart"></div></div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th rowspan="2">#</th><th rowspan="2">媒介</th><th rowspan="2">录单量</th>
          <th colspan="5" class="grp v">来院人次</th>
          <th colspan="5" class="grp d">成交人数</th>
          <th rowspan="2">成交金额</th>
        </tr>
        <tr>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
        </tr>
      </thead>
      <tbody>__ROWS_MONEY__</tbody>
      __FOOT_MONEY__
    </table>
  </div>

  <h2><span class="n">05</span>咨询师成交数据（三方营销口径）</h2>
  <div class="card"><div id="c_emp" class="chart"></div></div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th rowspan="2">#</th><th rowspan="2">网电咨询师</th><th rowspan="2">录单量</th>
          <th colspan="5" class="grp v">来院人次</th>
          <th colspan="5" class="grp d">成交人数</th>
          <th rowspan="2">成交金额</th>
        </tr>
        <tr>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
        </tr>
      </thead>
      <tbody>__ROWS_EMP__</tbody>
      __FOOT_EMP__
    </table>
    __FOOT_NOTE_EMP__
  </div>

  <h2><span class="n">06</span>趋势分析（__NDAYS__ 天）</h2>
  <div class="card"><div id="c_trend" class="chart"></div></div>
  <div class="grid2">
    <div class="card"><div id="c_trend_src" class="chart sm"></div></div>
    <div class="card"><div id="c_conv" class="chart sm"></div></div>
  </div>

  <h2><span class="n">07</span>媒介质量四象限（录单量 × 成交金额）</h2>
  <div class="card"><div id="c_scatter" class="chart" style="height:400px"></div></div>
  <div class="note" style="margin-bottom:16px">
    右上＝<b>量价齐优</b>，应加投；右下＝<b>有量无产</b>，需查线索质量；左上＝<b>小而精</b>，可放量试投；左下＝量少产少，观察即可。</div>

  <h2><span class="n">08</span>全部媒介明细（__NMEDIA__ 个，按录单量降序）</h2>
  <div class="card"><div class="scroll">
    <table>
      <thead>
        <tr>
          <th rowspan="2">媒介</th><th rowspan="2">录单量</th>
          <th colspan="5" class="grp v">来院人次</th>
          <th colspan="5" class="grp d">成交人数</th>
          <th rowspan="2">成交金额</th>
        </tr>
        <tr>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
          <th>新客首次</th><th>新客二次</th><th>新客</th><th>老客</th><th>总人数</th>
        </tr>
      </thead>
      <tbody>__ROWS_ALL__</tbody>
      __FOOT_ALL__
    </table>
  </div>__FOOT_NOTE_ALL__</div>

  <h2><span class="n">09</span>数据口径说明</h2>
  <div class="note">__NOTE__</div>

  <h2><span class="n">10</span>数据范围与来源</h2>
  <div class="card" style="padding:14px 16px">
    <div style="font-size:13.5px;color:var(--sub);margin-bottom:10px">
      __HEAD_NOTE__
    </div>
    <div class="scroll" style="max-height:none">__SCOPE_TBL__</div>
    <div class="note" style="margin-top:12px">__SCOPE_NOTE__</div>
  </div>

  <h2><span class="n">11</span>逐日明细 · 按天核对用</h2>
  <div class="card" style="padding:0;overflow:hidden">
    <div class="scroll" style="max-height:360px;border:0;border-radius:0">__DAILY_TBL__</div>
    <div style="padding:10px 14px;font-size:12.5px;color:var(--sub);border-top:1px solid var(--line)">
      __DAILY_TAIL__
    </div>
  </div>
</div>

<script>/*__ECHARTS__*/</script>
<script>
/*__DATA__*/
const C={a:'#635bff',a2:'#00b8d9',ok:'#12b76a',warn:'#f79009',bad:'#f04438'};
const ax={axisLine:{lineStyle:{color:'#e6e9f0'}},axisLabel:{color:'#5b6478',fontSize:11.5},splitLine:{lineStyle:{color:'#f1f3f9'}}};
const fmt=n=>(n||0).toLocaleString('zh-CN',{maximumFractionDigits:0});
const wan=n=>((n||0)/10000).toFixed(1)+'万';
function mk(id,o,h){const e=document.getElementById(id);if(!e)return;if(h){e.style.height=h+'px';}echarts.init(e).setOption(o);}
const APLABEL={show:true,backgroundColor:'#2b3247',color:'#fff',fontSize:11.5,padding:[4,8],borderRadius:4,shadowBlur:4,shadowColor:'rgba(0,0,0,.2)'};
function bs(){return{tooltip:{trigger:'axis',confine:true,axisPointer:{type:'shadow',label:APLABEL}},grid:{left:10,right:16,top:38,bottom:8,containLabel:true}};}

// 03 建档 TOP20
const bTop=[...D.srcsByBuild.slice(0,20)];
mk('c_build',{...bs(),legend:{top:0,textStyle:{fontSize:12}},
 xAxis:{type:'category',data:bTop.map(s=>s.name),...ax,axisLabel:{color:'#5b6478',fontSize:10.5,rotate:32,interval:0}},
 yAxis:{type:'value',...ax},
 series:[{name:'录单量',type:'bar',data:bTop.map(s=>s.建档量),itemStyle:{color:C.a,borderRadius:[4,4,0,0]},barMaxWidth:30},
         {name:'来院人次',type:'bar',data:bTop.map(s=>s.来院_总人数),itemStyle:{color:C.a2,borderRadius:[4,4,0,0]},barMaxWidth:30},
         {name:'成交人数',type:'bar',data:bTop.map(s=>s.成交_总人数),itemStyle:{color:C.ok,borderRadius:[4,4,0,0]},barMaxWidth:30}]});

// 04 成交金额 TOP20
// ⚠️ 横向条形图：容器高度必须随条数增长，且类目轴要 interval:0
//    否则 ECharts 的 axisLabel.interval 默认 'auto' 会「隐藏放不下的标签」→ 媒介名缺失
const mTop=[...D.srcs.slice(0,20)].reverse();
mk('c_money',{...bs(),grid:{left:10,right:40,top:26,bottom:8,containLabel:true},
 xAxis:{type:'value',...ax,axisLabel:{color:'#5b6478',fontSize:11.5,formatter:v=>wan(v)}},
 yAxis:{type:'category',data:mTop.map(s=>s.name),...ax,axisTick:{show:false},axisLabel:{color:'#5b6478',fontSize:11,interval:0}},
 series:[{type:'bar',data:mTop.map(s=>s.成交总金额),itemStyle:{color:p=>p.dataIndex>=mTop.length-3?C.ok:C.a,borderRadius:[0,5,5,0]},
   label:{show:true,position:'right',formatter:p=>wan(p.value),color:'#5b6478',fontSize:11}}]},
 Math.max(340, mTop.length*27+56));

// 05 咨询师
const eR=[...D.emps].reverse();
mk('c_emp',{...bs(),grid:{left:10,right:40,top:26,bottom:8,containLabel:true},
 xAxis:{type:'value',...ax,axisLabel:{color:'#5b6478',fontSize:11.5,formatter:v=>wan(v)}},
 yAxis:{type:'category',data:eR.map(e=>e.name),...ax,axisTick:{show:false},axisLabel:{color:'#5b6478',fontSize:11,interval:0}},
 series:[{type:'bar',data:eR.map(e=>e.成交总金额),itemStyle:{color:p=>p.dataIndex>=eR.length-3?C.ok:C.a,borderRadius:[0,5,5,0]},
   label:{show:true,position:'right',formatter:p=>wan(p.value),color:'#5b6478',fontSize:11}}]},
 Math.max(340, eR.length*30+56));

// 06 趋势
const tt=D.totalTrend;
mk('c_trend',{...bs(),legend:{top:0,textStyle:{fontSize:12}},
 xAxis:{type:'category',data:tt.map(t=>t.date.slice(5)),...ax},
 yAxis:[{type:'value',name:'人数',...ax},{type:'value',name:'金额',...ax,axisLabel:{color:'#5b6478',fontSize:11.5,formatter:v=>wan(v)}}],
 series:[
  {name:'录单量',type:'line',smooth:true,data:tt.map(t=>t.建档量),itemStyle:{color:C.a},lineStyle:{width:2.5},areaStyle:{color:'rgba(99,91,255,.10)'}},
  {name:'来院-新客',type:'bar',stack:'v',data:tt.map(t=>t.来院_新客),itemStyle:{color:C.a2},barMaxWidth:22},
  {name:'来院-老客',type:'bar',stack:'v',data:tt.map(t=>t.来院_老客),itemStyle:{color:'#7fdcf0'},barMaxWidth:22},
  {name:'成交-新客',type:'bar',stack:'d',data:tt.map(t=>t.成交_新客),itemStyle:{color:C.ok},barMaxWidth:22},
  {name:'成交-老客',type:'bar',stack:'d',data:tt.map(t=>t.成交_老客),itemStyle:{color:'#7ee2b8'},barMaxWidth:22},
  {name:'成交金额',type:'line',smooth:true,yAxisIndex:1,data:tt.map(t=>t.成交总金额),itemStyle:{color:C.warn},lineStyle:{width:2.5,type:'dashed'}}]});

// 06b 头部媒介趋势（按建档TOP5）
const top5=D.srcsByBuild.slice(0,5).map(s=>s.name);
const pal=[C.a,C.a2,C.ok,C.warn,C.bad];
mk('c_trend_src',{...bs(),legend:{top:0,textStyle:{fontSize:11}},
 xAxis:{type:'category',data:D.dates.map(d=>d.slice(5)),...ax},
 yAxis:{type:'value',...ax},
 series:top5.map((n,i)=>({name:n,type:'line',smooth:true,
   data:D.dates.map(d=>((D.srcTrend[n]||{})[d]||{}).建档量||0),
   itemStyle:{color:pal[i]},lineStyle:{width:2}}))});

// 06c 转化率趋势
mk('c_conv',{...bs(),
 xAxis:{type:'category',data:D.dates.map(d=>d.slice(5)),...ax},
 yAxis:{type:'value',...ax,axisLabel:{color:'#5b6478',fontSize:11.5,formatter:v=>v+'%'}},
 series:[{name:'录单→成交转化率',type:'line',smooth:true,
   data:tt.map(t=>t.建档量?(t.成交_总人数/t.建档量*100):0),
   itemStyle:{color:C.bad},lineStyle:{width:2.5},areaStyle:{color:'rgba(240,68,56,.08)'}}]});

// 07 四象限散点
const sc=D.srcs.filter(s=>s.建档量>0||s.成交总金额>0);
const maxB=Math.max(...sc.map(s=>s.建档量),1);
const medB=sc.map(s=>s.建档量).sort((a,b)=>a-b)[Math.floor(sc.length/2)];
mk('c_scatter',{tooltip:{formatter:p=>p.data[3]},
 grid:{left:10,right:26,top:30,bottom:10,containLabel:true},
 xAxis:{type:'value',name:'录单量',nameTextStyle:{color:'#5b6478'},...ax},
 yAxis:{type:'value',name:'成交金额',nameTextStyle:{color:'#5b6478'},...ax,axisLabel:{color:'#5b6478',fontSize:11.5,formatter:v=>wan(v)}},
 series:[{
   type:'scatter',
   symbolSize:d=>Math.max(9,Math.min(38,8+Math.sqrt(d[2])*5)),
   data:sc.map(s=>[s.建档量,s.成交总金额,s.成交_总人数||0,s.name+'｜录单'+fmt(s.建档量)+'｜成交'+fmt(s.成交_总人数)+'人｜'+fmt(s.成交总金额)+'元']),
   itemStyle:{color:p=>p.data[1]>0?(p.data[0]>=medB?C.ok:C.a2):'#c9cfdc',opacity:.85},
   label:{show:true,formatter:p=>p.data[1]>50000?p.data[3].split('｜')[0]:'',position:'right',color:'#5b6478',fontSize:10.5},
   markLine:{silent:true,symbol:'none',lineStyle:{color:'#d7dbe7',type:'dashed'},
     data:[{xAxis:medB}]}
 }]});

// 表格：跨组同档联动高亮
// 指针停在哪一档（新客首次/新客二次/新客/老客/总人数），该行「来院」与「成交」的同一档同时亮起
document.querySelectorAll('td[data-col]').forEach(td=>{
  td.addEventListener('mouseenter',()=>{
    const col=td.dataset.col;
    td.closest('tr').querySelectorAll('td[data-col="'+col+'"]').forEach(c=>c.classList.add('colhl'));
  });
  td.addEventListener('mouseleave',()=>{
    td.closest('tr').querySelectorAll('td.colhl').forEach(c=>c.classList.remove('colhl'));
  });
});

window.addEventListener('resize',()=>{document.querySelectorAll('.chart').forEach(el=>{const i=echarts.getInstanceByDom(el);if(i)i.resize();});});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
