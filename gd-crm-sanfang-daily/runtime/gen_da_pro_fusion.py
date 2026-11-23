# -*- coding: utf-8 -*-
"""Pro 融合版：以原日报为主体，融入 data-analyst-pro 六阶分析的增量层。
去重按 Pro 标准（一问一图/表格能说清就别画图/不重复造数据）：
- 规模KPI/环比/分层表/趋势图 → 锚点指向原报告 01/02/06，不重画
- 增量：防错溯源/描述统计/前后半段/帕累托/异常清单/因果分级/区间预测/四维评分
- 全页仍只 7 张图（原报告的），零新增图
输出：三方营销_质量数据分析Pro_融合版.html（独立新文件，不碰其他版本）
"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
O = json.load(open(os.path.join(BASE,'data/analysis/da_pro.json'),encoding='utf-8'))
SF = json.load(open(os.path.join(BASE,'data/analysis/sanfang.json'),encoding='utf-8'))
src = open(os.path.join(BASE,'三方营销媒介分析报告.html'),encoding='utf-8').read()

def n(x): return f"{float(x):,.0f}"
def money(x): return f"{float(x):,.2f}"
def wan(x): return f"{float(x)/10000:,.1f}万"
def sgn(x): return f"{x:+.1f}%" if x is not None else "—"

meta=O['meta']; st1=O['stage1']; st2=O['stage2']; st3=O['stage3']; st4=O['stage4']
st5=O['stage5']; st6=O['stage6']; q=O['quality']; c=st1['central']; ds=st1['dispersion']
sc=st1['skew_check']; mom=st2['环比']; hf=st2['前后半段']; hz=st2['横向']

def trend_ui(word):
    """方向词 → (词, 箭头, 颜色)：全部从 da_pro.json 现算，禁止写死升降。"""
    if '降' in word: return (word, '↘', '#f04438')
    if '升' in word: return (word, '↗', '#12b76a')
    return (word, '→', '#5b6478')

def hf_phrase():
    """前后半段对照句：按成交/业绩方向现算，避免写死「单子变少」之类。"""
    b, a = hf['前半'], hf['后半']
    dj = a['成交'] - b['成交']; dy = a['业绩'] - b['业绩']
    head = (f"后半 {n(a['成交'])} 单 vs 前半 {n(b['成交'])} 单、"
            f"业绩 {wan(a['业绩'])} vs {wan(b['业绩'])}，"
            f"转化率 {b['转化率']}%→{a['转化率']}%")
    if dj > 0 and dy > 0: return head + '，量效齐升'
    if dj < 0 and dy > 0: return head + '，靠客单价拉动'
    if dj > 0 and dy < 0: return head + '，客单价下滑'
    return head + '，量价齐降'

d_word, d_arrow, d_color = trend_ui(st3['方向']['成交'])
a_word, a_arrow, a_color = trend_ui(st3['方向']['业绩'])

# 1. 加锚点
for num in ['01','02','03','04','05','06','07','08','09','10','11']:
    src = src.replace('<h2><span class="n">'+num+'', f'<h2 id="s{num}"><span class="n">'+num+'"',1)

# 2. 片段
trace_rows=''.join(f"<tr><td class='k'>{x['数字']}</td><td style='text-align:left'>{x['来源文件']}</td>"
    f"<td style='text-align:left'>{x['字段']}</td><td style='text-align:left'>{x['逻辑']}</td></tr>" for x in O['trace'])

desc_rows=f'''
<tr><td class="k">样本量</td><td>{n(st1['scale']['录单'])}录单/{n(st1['scale']['成交'])}成交</td><td>{meta['n_days']}天</td></tr>
<tr><td class="k">日业绩均值/中位数</td><td>{money(c['日业绩均值'])}/{money(c['日业绩中位数'])}</td><td class="bad">右偏{sc['均值中位数差pct']}%</td></tr>
<tr><td class="k">日成交均值/中位数</td><td>{c['日成交均值']}/{c['日成交中位数']}</td><td>多数日≤2单</td></tr>
<tr><td class="k">日业绩标准差/IQR</td><td>{money(ds['日业绩标准差'])}/{money(ds['业绩IQR'])}</td><td>离散度高</td></tr>'''

an_rows=''.join(f"<tr><td class='k'>{x['date'][5:]}</td><td class='{'bad' if x['业绩']<0 else ''}'>{money(x['业绩'])}</td>"
    f"<td>{n(x['成交'])}</td><td>{x['z']}</td><td style='text-align:left'>{x['方法']}</td>"
    f"<td class='{'bad' if '严重' in x['级别'] else 'warn'}'>{x['级别']}</td></tr>" for x in st4['异常清单'])

act_link={1:'<span class="tag new">六阶新增</span>',2:'<span class="tag up">承接 01 第5/6条 · 升级</span>',3:'<span class="tag up">承接 01 第4条 · 升级</span>'}
act_rows=''.join(f"<tr><td class='k'>{a['#']}</td><td style='text-align:left'><b>{a['建议']}</b> {act_link.get(a['#'],'')}</td>"
    f"<td style='text-align:left'>{a['基于发现']}</td><td style='text-align:left'>{a['验证指标']}</td>"
    f"<td>{a['急迫度']}</td></tr>" for a in st6['建议'])

sc_rows=''.join(f"<tr><td class='k {color}'>{name}</td><td style='text-align:left'>{st6['情景'][key]['条件']}</td>"
    f"<td class='k'>{st6['情景'][key]['日均成交区间'][0]}~{st6['情景'][key]['日均成交区间'][1]}人/日</td></tr>"
    for name,key,color in [('乐观','乐观','ok'),('中性','中性',''),('悲观','悲观','bad')])

qd=[('数据准确性',q['数据准确性']),('分析深度',q['分析深度']),('表达清晰度',q['表达清晰度']),('决策可用性',q['决策可用性'])]
q_rows=''.join(f"<div class='qi'><span>{name}</span><div class='qb'><i style='width:{score*10}%'></i></div><b>{score}/10</b></div>" for name,score in qd)

seg3=st5['分层']
pivots='；'.join(f"{p['日期'][5:]}(MA3{p['MA3变化']:+})" for p in st3['拐点'])

LAYER=f'''
  <h2 id="pro"><span class="n" style="background:linear-gradient(135deg,#3b2f8f,#00b8d9)">✦</span>Pro 分析层 · data-analyst-pro 六阶法</h2>
  <div class="note" style="margin-bottom:14px;background:linear-gradient(100deg,rgba(99,91,255,.06),rgba(0,184,217,.05));border-color:#d9d5ff">
    <b>这一层做什么：</b>不是把 01~11 再分析一遍，而是对 <a href="#s01">01 核心结论</a>做<b>「复检 + 升级」</b>——01 管「是什么、怎么办」，本层管「这个结论靠不靠谱、往哪走」：修正右偏口径、补时间方向、标注异常、收敛因果措辞、给区间预测。
    <b>去重原则</b>：01 已下的结论（规模/环比/媒介两极分化/新老客分层）一律锚点引用或改为措辞复检，<b>不再摆第二套数字、不重画第二张图</b>。全页仍只有原报告 7 张图。
  </div>

  <div class="card" style="background:linear-gradient(120deg,#3b2f8f,#635bff 50%,#00b8d9);color:#fff;border:0">
    <div style="font-size:12px;opacity:.88;margin-bottom:8px">防错六步法 · 数据链</div>
    <div style="display:flex;gap:5px;flex-wrap:wrap">__CHAIN__</div>
  </div>

  <div class="card">
    <h3 style="margin:0 0 8px;font-size:16px">核心结论（结论先行）</h3>
    <div class="note" style="font-size:14px;line-height:1.75">__SUMMARY__</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-top:12px" class="pro-kpi">
      <div class="pk"><div class="pl">业绩（中位数/日）</div><div class="pv">__MED__</div><div class="pd">右偏，均值 __MEAN__ 仅参考</div></div>
      <div class="pk"><div class="pl">成交趋势</div><div class="pv" style="color:{d_color}">{d_word} {d_arrow}</div><div class="pd">MA3 __D0__→__D1__ 人/日</div></div>
      <div class="pk"><div class="pl">业绩趋势</div><div class="pv" style="color:{a_color}">{a_word} {a_arrow}</div><div class="pd">__A0__→__A1__/日</div></div>
      <div class="pk"><div class="pl">质量自评</div><div class="pv" style="color:#12b76a">__QSCORE__<span style="font-size:12px">/40</span></div><div class="pd">__QRATE__</div></div>
    </div>
    <div class="note" style="font-size:12px;margin-top:10px"><b>不重复：</b>规模四项见 <a href="#s01">01</a>（录单 {n(st1['scale']['录单'])} / 来院 {n(st1['scale']['来院'])} / 成交 {n(st1['scale']['成交'])} / 业绩 {wan(st1['scale']['业绩'])}），此处只放原报告没有的推断性指标。</div>
  </div>

  <h2><span class="n">0</span>防错六步 · 溯源表（数字可回溯）</h2>
  <div class="card">
    <table style="font-size:12.6px"><thead><tr><th>数字</th><th>来源文件</th><th>字段</th><th>提取逻辑</th></tr></thead><tbody>{trace_rows}</tbody></table>
    <div class="note" style="font-size:12.3px"><b>三向核对：</b>{O['consistency']['verdict']}</div>
  </div>

  <h2><span class="n">1</span>第一阶 · 描述统计（数据长什么样）</h2>
  <div class="card">
    <table style="font-size:13px"><thead><tr><th>指标</th><th>数值</th><th>注意</th></tr></thead><tbody>{desc_rows}</tbody></table>
    <div class="note" style="font-size:12.8px"><b>右偏判定：</b>日业绩均值比中位数高 <b>{sc['均值中位数差pct']}%</b>（>20% 阈值），受高分日拉高。按 Pro 规则核心汇报用<b>中位数 {money(c['日业绩中位数'])}</b>，避免极值误导。原始分布见 <a href="#s06">06 趋势</a> / <a href="#s11">11 逐日</a>。</div>
  </div>

  <h2><span class="n">2</span>第二阶 · 对比分析（前后半段 + 横向结构）</h2>
  <div class="card">
    <div class="note" style="font-size:12.3px;margin-bottom:10px"><b>去重：</b>最新日环比（{mom['日期'][5:]} vs {mom['vs'][5:]}，业绩 {sgn(mom['变化pct']['成交总金额'])}）已在 <a href="#s02">02 速览</a>，此处不再重复。</div>
    <div class="split">
      <div><b style="font-size:13.5px">前后半段（各 {meta['n_days']//2} 天）</b>
        <table style="font-size:13px;margin-top:8px"><thead><tr><th>指标</th><th>前半</th><th>后半</th></tr></thead><tbody>
        <tr><td class="k">成交单数</td><td>{n(hf['前半']['成交'])}</td><td>{n(hf['后半']['成交'])}</td></tr>
        <tr><td class="k">业绩</td><td>{wan(hf['前半']['业绩'])}</td><td>{wan(hf['后半']['业绩'])}</td></tr>
        <tr><td class="k">转化率</td><td>{hf['前半']['转化率']}%</td><td>{hf['后半']['转化率']}%</td></tr></tbody></table>
        <div class="note" style="font-size:12px">__HF_NOTE__</div>
      </div>
      <div><b style="font-size:13.5px">横向结构（帕累托）</b>
        <div class="note" style="font-size:12.8px;margin-top:8px"><b>去重：</b>「媒介两极分化」01 已下结论（见 <a href="#s01">01 第 5、6 条</a>：前三名录单 {hz['TOP3录单占比']}% 只成交 {hz['TOP3录单成交数']} 人、TOP3 撑 {hz['TOP3业绩占比']}% 业绩），此处<b>不重摆第二套数字</b>。补一个 01 没给的量级：<b>{hz['帕累托媒介数']} 个媒介（{hz['帕累托占比']}%）贡献 {hz['帕累托业绩占比']}% 业绩、{hz['零成交媒介数']} 个媒介零成交占 {hz['零成交录单占比']}% 录单</b>——作为"集中度"的量化佐证，不是新结论。</div>
        <div class="note" style="font-size:12.3px">完整排行见 <a href="#s04">04</a> / <a href="#s08">08</a>。</div>
      </div>
    </div>
  </div>

  <h2><span class="n">3</span>第三阶 · 趋势发现（方向 + 速度 + 拐点）</h2>
  <div class="card">
    <div class="note" style="font-size:12.3px;margin-bottom:10px"><b>去重：</b>趋势图已在 <a href="#s06">06</a>（含逐日柱线）。按 Pro「一问一图、表格能说清就别画图」，此处<b>不重画 MA3 曲线</b>，只给移动平均消噪后的文字结论。</div>
    <div class="split">
      <div><ul class="ins">
        <li><b>方向（3日移动平均）：</b>成交 <b style="color:{d_color}">{d_word}</b>（MA3 {n(st3['方向']['成交MA3首末'][0])}→{n(st3['方向']['成交MA3首末'][1])}）；业绩 <b style="color:{a_color}">{a_word}</b>（{wan(st3['方向']['业绩MA3首末'][0])}→{wan(st3['方向']['业绩MA3首末'][1])}）。</li>
        <li><b>速度：</b>日均成交较前半 <b>{sgn(st3['速度']['后半较前半日均成交变化pct'])}</b>（{st3['速度']['解读']}）。</li>
        <li><b>拐点：</b>{pivots}。</li>
      </ul></div>
      <div class="note" style="font-size:13px"><b>🔍 量效对照：</b>__HF_NOTE__。<br><br><b>季节性：</b>{st3['季节性']}。<br><br><b>驱动：</b>量 {st3['驱动拆分']['量贡献']}，效率 {st3['驱动拆分']['成交效率贡献']}。</div>
    </div>
  </div>

  <h2><span class="n">4</span>第四阶 · 异常检测（3σ + IQR 双法交叉）</h2>
  <div class="card">
    <div class="note" style="font-size:12.3px;margin-bottom:10px">阈值：3σ [{wan(st4['阈值']['3σ下界'])}, {wan(st4['阈值']['3σ上界'])}]；IQR [{wan(st4['阈值']['IQR下界'])}, {wan(st4['阈值']['IQR上界'])}]。异常≠问题，先核实再定性。</div>
    <table style="font-size:12.8px"><thead><tr><th>日期</th><th>业绩</th><th>成交</th><th>Z</th><th>检出方法</th><th>级别</th></tr></thead><tbody>{an_rows}</tbody></table>
    <div class="note" style="font-size:12.5px"><b>业务核实：</b>{st4['业务核实']}<br><b>交叉验证：</b>{st4['交叉验证']}</div>
  </div>

  <h2><span class="n">5</span>第五阶 · 因果推断（复检 01 的结论措辞）</h2>
  <div class="card">
    <div class="note" style="font-size:12.3px;margin-bottom:10px"><b>这一节做什么：</b>分层数字 01 已给（见 <a href="#s01">01 新老客结构</a>），<b>不重复数字</b>。这里只做一件事——复检 01 那句「老客到院转化明显高于新客 —— 复购比首诊更容易出单」的<b>措辞严谨度</b>，并补一个 01 没算的三档对照。</div>
    <div class="note" style="font-size:13.5px"><span class="tag l2">{st5['L2相关']['层级']}</span> <b>01 的发现</b>（数字见 01）：首次 {seg3[0]['转化']}% / 二次 {seg3[1]['转化']}% / 老客 {seg3[2]['转化']}% —— 二次与老客接近、都远高于首次。<br>
      <b style="color:#b54708">⚠️ 措辞复检：</b>01 写「复购比首诊更容易出单」，这把「老客」和「首诊」放在一起比较，且用了因果口吻。按 Pro 纪律应收敛为：<b>「数据显示到院次数与成交存在统计关联，但不足以确认因果」</b>——因为老客本身意向可能就更高，不一定是跟进带来的。<br>
      <b style="color:#b54708">措辞纪律：</b>{st5['L2相关']['措辞']}</div>
    <div class="note" style="font-size:12.5px"><b>补充三档对照（01 未拆）：</b>{st5['混杂提示']['说明']}<br><b>能力边界：</b>{st5['不可推断']}<br><b>要验证因果需补：</b>{st5['建议补数据']}</div>
  </div>

  <h2><span class="n">6</span>第六阶 · 预测建议（区间 + 情景 + 验证指标）</h2>
  <div class="card">
    <div class="note" style="font-size:13.5px"><b>📊 {st6['预测']['对象']}：</b>中性点 {st6['预测']['中性点']} 人/日，<b>80% 区间 {st6['预测']['80%区间'][0]}~{st6['预测']['80%区间'][1]}</b><br>
      <span style="font-size:12.3px;color:#5b6478">方法：{st6['预测']['方法']}｜假设：{'；'.join(st6['预测']['假设'])}</span><br>
      <span style="font-size:12.3px;color:#f04438">失效条件：{'；'.join(st6['预测']['失效条件'])}</span></div>
    <table style="font-size:13px;margin:11px 0"><thead><tr><th>情景</th><th>触发条件</th><th>日均成交区间</th></tr></thead><tbody>{sc_rows}</tbody></table>
    <div class="note" style="font-size:12.3px;margin-bottom:9px"><b>去重说明：</b>建议 2、3 的<b>发现</b>来自 01（不重复陈述），这里把 01 的「观察」升级为「可验证动作」——加了验证指标和急迫度；建议 1 是六阶新增。</div>
    <table style="font-size:12.8px"><thead><tr><th>#</th><th>建议</th><th>基于发现</th><th>验证指标</th><th>急迫度</th></tr></thead><tbody>{act_rows}</tbody></table>
  </div>

  <h2><span class="n">★</span>四维质量自评</h2>
  <div class="card">
    {q_rows}
    <div class="note" style="font-size:12.8px">总分 <b>{q['总分']}/40</b>（{q['评级']}）。{q['说明']}</div>
  </div>

  <div class="card">
    <b style="font-size:14px">图表去重审计 · 按 data-analyst-pro 标准</b>
    <div style="font-size:12.4px;color:#5b6478;margin:5px 0 9px">标准：一问一图、表格能说清就别画、不重复造数据。全页 7 图（均为原报告），Pro 层新增 0 图。<b>本次额外审出 3 处与 01 重复，已按下表处理。</b></div>
    <table style="font-size:12.5px"><thead><tr><th>内容</th><th>处理</th><th>依据</th></tr></thead><tbody>
      <tr><td>规模 KPI / 环比 / 分层表</td><td style="color:#12b76a">锚点引用 01/02</td><td style="text-align:left">数字已存在，不重复</td></tr>
      <tr><td>MA3 趋势图（Pro 独立版曾有）</td><td style="color:#f04438"><b>已砍</b></td><td style="text-align:left">与 06 趋势图同问，改文字结论</td></tr>
      <tr><td><b>① 二次到院/老客转化</b>（01 第4条）</td><td style="color:#f79009"><b>改为措辞复检</b></td><td style="text-align:left">核心结论不再复述，第五阶收敛 01 的因果口吻</td></tr>
      <tr><td><b>② 媒介两极分化</b>（01 第5/6条）</td><td style="color:#f79009"><b>压缩成一句佐证</b></td><td style="text-align:left">不重摆第二套数字，只补集中度量化</td></tr>
      <tr><td><b>③ 建议 2/3</b>（源自 01 发现）</td><td style="color:#f79009"><b>标注「承接·升级」</b></td><td style="text-align:left">观察→可验证动作，从重复变增量</td></tr>
      <tr><td>溯源/描述统计/异常/趋势/预测</td><td style="color:#12b76a">增量保留</td><td style="text-align:left">原报告无此视角</td></tr>
      <tr><td>原报告 7 张图</td><td style="color:#12b76a">全部保留</td><td style="text-align:left">各答各问题，无重复</td></tr>
    </tbody></table>
  </div>
'''

chain=''.join(f"<span style='background:rgba(255,255,255,.16);border-radius:8px;padding:4px 10px;font-size:12px'>{x}</span>" for x in ['①源审阅','②溯源表','③只提取一次','④自洽验证','⑤三向核对','⑥交付锁定'])

summary=(f"<b>本层不复述 01 的结论</b>（规模/结构/媒介表现见 <a href='#s01'>01</a>），只给 01 没有的 5 条复检结果："
  f"① <b>口径纠偏</b>：01 的「客单价 {wan(st1['scale']['业绩']/st1['scale']['成交'])}」用的是均值，实际右偏 {sc['均值中位数差pct']}%，核心汇报应改用<b>中位数 {money(c['日业绩中位数'])}</b>；"
  f"② <b>趋势对照</b>（01 无时间判断）：成交{d_word}（MA3 {n(st3['方向']['成交MA3首末'][0])}→{n(st3['方向']['成交MA3首末'][1])}）业绩{a_word}（{wan(st3['方向']['业绩MA3首末'][0])}→{wan(st3['方向']['业绩MA3首末'][1])}）；{hf_phrase()}；"
  f"③ <b>异常标注</b>：负额日经核实是退款冲账、__POS_DAY__ 是正向尖峰；"
  f"④ <b>措辞收敛</b>：01「复购比首诊更容易出单」是因果口吻，按 L2 纪律应改为统计关联（见第五阶）；"
  f"⑤ <b>区间预测</b>：未来 7 天日均成交 {st6['预测']['80%区间'][0]}~{st6['预测']['80%区间'][1]} 人（01 无预测）。")

pos_spike=[a for a in st4['异常清单'] if '3σ(z>2)' in a['方法'] and a['业绩']>0]
pos_day=(pos_spike[0]['date'][5:]) if pos_spike else '本窗口无 3σ 正向尖峰'
rep=dict(CHAIN=chain,SUMMARY=summary,HF_NOTE=hf_phrase(),POS_DAY=pos_day,MED=wan(c['日业绩中位数']),MEAN=wan(c['日业绩均值']),
  D0=n(st3['方向']['成交MA3首末'][0]),D1=n(st3['方向']['成交MA3首末'][1]),
  A0=wan(st3['方向']['业绩MA3首末'][0]),A1=wan(st3['方向']['业绩MA3首末'][1]),
  QSCORE=str(q['总分']),QRATE=q['评级'])

# Pro 专属 CSS
css='''@media(max-width:860px){.pro-kpi{grid-template-columns:1fr 1fr}}
.pk{background:#fafbff;border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.pl{font-size:11.5px;color:var(--sub)}.pv{font-size:21px;font-weight:800;margin:3px 0}.pd{font-size:11.5px;color:var(--sub)}
.split{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.qi{display:grid;grid-template-columns:92px 1fr 44px;gap:10px;align-items:center;margin:8px 0;font-size:12.5px}
.qb{height:8px;background:#eef0f6;border-radius:8px;overflow:hidden}.qb i{display:block;height:100%;background:linear-gradient(90deg,#635bff,#12b76a);border-radius:8px}
.tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:6px;font-weight:700}
.tag.l2{background:rgba(247,144,9,.13);color:#b54708}
.tag.new{background:rgba(99,91,255,.12);color:#635bff}
.tag.up{background:rgba(18,183,106,.12);color:#087443}
@media print{.card,.hero{box-shadow:none;break-inside:avoid}body{background:#fff}}
'''
src=src.replace('</style>',css+'\n</style>',1)
for k,v in rep.items():
    LAYER=LAYER.replace('__'+k+'__',v)
src=src.replace('<h2 id="s01">',LAYER+'\n  <h2 id="s01">',1)

out=os.path.join(BASE,'三方营销_质量数据分析Pro_融合版.html')
open(out,'w',encoding='utf-8').write(src)
print('written:',out,len(src),'chars')
print('unresolved:',set(re.findall(r'(?<![_])__[A-Z][A-Z0-9_]*__(?!_)',src)))
