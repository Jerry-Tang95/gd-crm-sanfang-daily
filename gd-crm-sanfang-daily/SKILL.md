---
name: gd-crm-sanfang-daily
description: 内网 GD-CRM「三方营销」媒介日报：跑一键脚本取数、按区间报表唯一真值出单文件 HTML 趋势报告，并做口径核对与假成功识别。当用户说「跑三方营销日报」「三方日报出数」「媒介日报」「网电咨询师媒介报表」「重出上月报告」「报告数字对不上」「CRM 可查区间」时使用；也是每天 08:00 定时任务「三方营销日报」的执行入口，定时任务触发时按《每日定时任务执行 SOP》跑完整闭环。只适用于内网 192.168.16.138 的 GD-CRM，不适用于云客 CRM。
summary: 内网 GD-CRM 三方营销日报全流程（取数窗口 → 区间基准 → 三方聚合 → HTML 报告），含唯一真值口径、定时任务执行 SOP、11 道交付门禁与 20+ 个已知坑。
type: data-report
triggers:
  - 跑三方营销日报 / 三方日报出数
  - 媒介日报 / 网电咨询师媒介报表
  - 三方营销统计 / 媒介分析
  - 重出上月报告 / 月报重出
  - 报告数字对不上 / CRM 可查区间
  - 每日定时任务跑日报 / 定时执行三方日报 / 自动化跑日报
version: "1.3"
updated: "2026-11-07"
agent_created: true
---

# 内网 GD-CRM 三方营销日报

## 何时用 / 边界

- 用：每天从内网 GD-CRM 拉「网电咨询师媒介/渠道报表」，只统计 **媒介类型 = 三方营销** 的明细行，产出 `三方营销媒介分析报告.html`。
- **不要用**：`yunke-crm-periodic-report` / `yunke-crm*`（那是外部云客 CRM，走 omni-cli 命令族，与本系统无关）；三套医疗 Excel 报表（走 `wangdian-monthly-report` / `xianchang-monthly-report` / `network-report-build`）。
- 周报填表走 `weekly-report-fill`，它消费本流程产出的 `sanfang.json`，**共用取数层，不要另写一套取数逻辑**。

## 唯一真源（脚本只在项目目录，禁止复制）

| 项 | 值 |
|---|---|
| 项目目录 | `C:\Users\TJL\WorkBuddy\2026-10-14-15-59-59\gd-crm-媒介日报\` |
| Python | `C:\Users\TJL\.workbuddy\binaries\python\envs\default\Scripts\python.exe` |
| 一键入口 | `run_daily.py [YYYY-MM-DD]`（不带参数 = 昨天） |
| 权威数据 | `data\analysis\sanfang.json`（合计）、`data\raw\range.xls` + `data\analysis\range_baseline.json`（区间报表真值） |
| 交付报告 | `三方营销媒介分析报告.html`（主文件同名覆盖，`run_daily.py` 自动留档到 `history\`） |
| 月报入口 | `gen_month.py [YYYY-MM]` → `三方营销媒介分析报告_YYYY年M月.html`（复用日报模板；`gen_oct.py` 仅为兼容壳） |
| 内网 | `192.168.16.138`，账号密码在同目录 `config.local.json` |
| 定时任务 | `三方营销日报`（id `e83f79a3-cfe0-4b95-9de2-bea94fae2514`，每天 08:00，ACTIVE）；**2026-11-07 起 prompt 改为「加载本 Skill 并按《每日定时任务执行 SOP》执行」，本 Skill 是执行逻辑的唯一真源** |

⚠️ 改代码前先确认跑的是哪份：源目录 + `history\backup_20261028\` 有副本，判据是文件名/md5，不是「我改过了」。**不要把脚本复制到别处跑**。

### 发布副本 `runtime\`（改完脚本必须同步，别只改源目录）
本 Skill 目录内带一份 `runtime\`，是给 GitHub 分发 / 换机部署用的**可移植副本**（把本机 python 路径、chromium 路径、内网 BASE、ECharts 路径换成环境变量 / 随包资源）。方向单向：**源目录 → runtime**，绝不反向拷回。

```bash
cd "C:/Users/TJL/.workbuddy/skills/gd-crm-sanfang-daily"
"C:/Users/TJL/.workbuddy/binaries/python/envs/default/Scripts/python.exe" tools/sync_runtime.py \
  --src "C:/Users/TJL/WorkBuddy/2026-10-14-15-59-59/gd-crm-媒介日报"
```

- **`--check` 只验证「补丁能不能打上」，不比对内容**——2026-11-07 实测：源脚本改了 2 处大功能、runtime 还是 6 小时前的旧版，`--check` 照样全 OK。**判断同步没同步要看文件大小 / grep 关键改动，别只看 OK。**
- 同步后跑 `python -m py_compile runtime\gen_report_sanfang.py` 确认可编译；再 `diff` 一遍（除 `[portable]` 标记行外应完全相同）。

### 交付前自检 `tools\verify_skill.py`（可替代手工逐项核对）
```bash
python tools/verify_skill.py --full     # 结构/元数据/JSON/编译/同步/渲染 + playwright 版式回归
```
2026-11-07 实测 **26/26 通过**。发布前先跑它，绿了再发布；发布后用 `github-skill-publish/scripts/verify_publish.py <skill_dir> --repo gd-crm-sanfang-daily` 核远端 blob sha。**本地绿 ≠ 线上绿**——改了不重发，远端会一直是旧版（本次实测落后 9 处）。

## 一键命令

```bash
"C:/Users/TJL/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
  "C:/Users/TJL/WorkBuddy/2026-10-14-15-59-59/gd-crm-媒介日报/run_daily.py"
```

约 1~8 分钟（含逐日补抓），属正常。手动指定日期只在补跑时用；**统计窗口由程序自动探测，不要手工指定，也不要补齐查不到的历史日期**。

月报（独立文件，不覆盖日报）：
```bash
"…python.exe" "…/gd-crm-媒介日报/gen_month.py" 2026-10
```

## 每日定时任务执行 SOP（自动化唯一入口）

定时任务 `三方营销日报`（每天 08:00）触发时，**严格按本节从头跑到尾**；本节与下方「硬性禁令」冲突时以硬性禁令为准。

**① 前置连通性**（先做，别一上来就跑脚本）
```powershell
$r = Test-NetConnection -ComputerName 192.168.16.138 -Port 80 -WarningAction SilentlyContinue; $r.TcpTestSucceeded
```
`True` 才继续。**`PingSucceeded=False` 不代表离线**（防火墙拦 ICMP，见已知坑）；只有 `TcpTestSucceeded=False` 且 ARP 显示 Unreachable 才是服务器真离线 → 直接按 ⑥ 报失败。

**② 执行一键脚本**（工作目录 `gd-crm-媒介日报\`，不带参数 = 昨天）
```bash
"C:/Users/TJL/.workbuddy/binaries/python/envs/default/Scripts/python.exe" "C:/Users/TJL/WorkBuddy/2026-10-14-15-59-59/gd-crm-媒介日报/run_daily.py"
```
约 1~8 分钟属正常，用后台运行并等结果，别中途当卡死杀掉。

**③ 判成功（最关键，防假成功）**
- `analyze_sanfang.py` 必须打印 `建档 X | 来院 X | 成交 X 人 | 业绩 X 元` 累计行；
- fetch_window / parse / baseline / analyze / gen 各步退出码为 0；
- **没有累计行 = 分析崩了**，`gen_report` 仍可能拿旧 json 出一份「看起来成功」的 HTML → **判失败，不许沿用上一版报告**（10-24 空日 `KeyError: '建档量'` 踩过）。

**④ 取数汇报**（数字一律从 `data/analysis/sanfang.json` 现算，禁止手写常量）
```python
import json
d = json.load(open('data/analysis/sanfang.json', encoding='utf-8'))
w  = d['window']                      # start/end/query_days/queryable_start/archive_days
t  = d['window_totals']               # 建档量/来院_总人数/成交_总人数/成交总金额 + 五档
tr = {r['date']: r for r in d['total_trend']}   # 逐日；最新日 = d['dates'][-1]，环比取倒数第二天
s  = d['daily_sum']; src = d['src_total']; emp = d['emp_total']   # 对账 / 媒介异常 / 公共账号
```
转化率 = `t['成交_总人数']/t['建档量']`；客单价 = `t['成交总金额']/t['成交_总人数']`。
异常重点看：`src_total` 里有录单零成交的媒介数、净负金额、`成交总金额≠0 且 成交_总人数=0`（有金额无人数）、`src_trend` 里最新日较前一日建档变动 ≥10、`emp_total` 的 `三方公用(13125)` / `网电公账(11013)` 占比。

**⑤ 交付校验**（做完再汇报）
- `python verify_days.py <最新日>` → 单日 xls 四项与区间逐项一致；
- `python check_group_hl.py`（20/20 PASS）、`python check_charts.py`（类目标签全显）；
- HTML 边界：含最新日、**不含次日**、不含上月月份串／`09-30`、不含跨月写死文案。
- **版式硬要求**（2026-11-07 起，靓仔提的两个问题）：① 速览四张卡（昨日/区间 的来院、成交）都有 `新客 X · 老客 Y` 拆分行，核心结论带「新老客结构」；② 4 张主表都有合计行且与 `window_totals` 对得上（08 表 sticky 吸底）。缺任一项视为没改到位。

**⑥ 失败处理**：内网不通 / 登录失败 / 报表接口报错 / ③ 判假成功 → **如实报失败原因与报错信息**，不生成占位数字、不推算、不沿用旧报告冒充新数据。

**⑦ 汇报模板**（回给用户的固定结构，简明）
报告路径（可点击） → 实际统计区间（含天数与 `queryable_start`） → 区间合计四项 → 最新一天四项 + 环比 → 异常清单（暴涨暴跌 / 负额冲账 / 零成交媒介 / 有金额无人数 / 公共账号占比） → 一句话结论；另附口径差（逐日相加 vs 区间报表，按人去重）与校验结果。

**⑧ 留痕**：向自动化自己的 `memory.md` 追加一条高层摘要（窗口、合计、最新日环比、异常、校验结果、报告 md5/留档名），**不要把报告全文写进去**。

## 流水线（`run_daily.py` 内部顺序）

1. `fetch_window.py` —— 二分探测 CRM 当前可查首日 → `window.json{start=当月1号, end=昨天, queryable_start, days}`，并按整月区间导出 `range.xls`
2. `batch_fetch.py` —— 只补抓区间内缺失的**单日** xls（仅供画逐日曲线，**不参与合计**）
3. `parse_daily.py` —— 单日 xls → json
4. `build_range_baseline.py` —— 区间报表 → `range_baseline.json`（合计/媒介/咨询师/五档的**唯一真值**）
5. `analyze_sanfang.py` —— 合并成 `sanfang.json`
6. `gen_report_sanfang.py` —— 出 HTML + 自动留档快照

四步（parse/base/analyze/gen）全绿才留档；否则 `archive_report()` 会跳过，避免把假成功版本存进历史。

## 口径铁律（违反必出错）

1. **统计区间 = 当月 1 号 ~ 前一天；合计一律取 CRM 区间报表（`range_baseline.json`），绝不叠加本地存档、绝不用逐日相加当合计。**
   - 铁证：把 10-01~10-27 整段提交 CRM 与 10-20~10-27 返回逐格一致；手工导出的 10-01~10-27 表也是同一组数（3,415 / 156 / 64 / 1,585,955.92）。用存档补月初算出 308 人来院，被用户当场否掉。
2. **逐日明细只列 CRM 实际持有 `>= queryable_start` 的天数**，更早的日期不画、不累加。
3. **差异只能解释、不能修补**：逐日相加 vs 区间报表差 3~5 条属正常（按人去重 + CRM 后改数），写进逐日表 footer 对账；**超过 20 条要查是不是又出现重挂/补录**。
4. **「录单」= 系统的「建档量」字段**（用户 10-14 17:16 确认），JSON 字段名仍是 `建档量`，只改显示文本。
5. **一律用 detail 明细行逐条加总，绝不用报表自带的「媒介类型汇总行」**——该行 `成交_总人数` 有 bug（10-01 三方汇总写「新客4+老客2」总人数却填 2）。已验证：全院汇总行 ≡ 明细聚合（0 误差），金额/录单/来院三列两口径一致，仅成交人数受影响。
6. **成交人数只统计成交单**（退款不计人数）；成交金额是**净额**（退款冲减）→ 会出现「人数为正、金额为负」；恒等式：新客 = 新客首次 + 新客二次，总人数 = 新客 + 老客 —— **单日严格成立；区间合计按人去重后会有差**（同一人跨天分别以首次/二次到院只计一次，实测 10 月来院 首次129+二次40=169 ≠ 新客154、新客154+老客31=185 ≠ 总人数184）。报告里的 `id_note` 会在出现差时自动在表下解释，别当作 bug 去「修平」。
7. **公共账号单列**：`网电公账(11013)`、`三方公用(13125)` 不是真人咨询师，退款无归属归集于此，不要混进人均/排名。
8. **「有金额、成交人数 = 0」的明细行真实存在**（如美探 7.1 万 0 人），不是 bug；这类金额要在结论里单列，不能拿去算人均。

## 验收标准与假成功识别

**用户原话（10-26）：「我只保证统计的数据和当天看到的数据是一样就行」** → 两条判据：①每日数字 ≡ 当天 CRM 看到的；②区间合计要和 CRM 区间报表对得上。

- **跑完必须看 `analyze_sanfang.py` 有没有打印「建档 / 来院 / 成交 / 业绩」累计行**。没有 = 分析步骤崩了，`gen_report` 仍可能拿旧 json 出一份「看起来成功」的报告（2026-10-24 的 CRM 停机空日就触发过 `KeyError: '建档量'`）。**此时如实报失败，不许沿用上一版报告冒充新数据**。
- `run_daily.py` 退出码：四步全绿才返回 0。
- 交叉核对：`python verify_against_crm_export.py "<任意CRM导出.xls>"` → 逐媒介并排比；`python verify_days.py <日期...>` → 单日复核。
- **出数前先拿用户的报表当基准对一遍**，别等他说「还是不对」。

## 交付门禁（报告生成后逐条打勾）

1. 报告里**任何日期、人数、金额都要能在 `sanfang.json` 里找到出处**，正文不许写常量。
   - 踩过：首版手写「三方公用录单 469 人」，窗口扩到 25 天后真实值已是 1,212，报告一直显示 469。
2. **跨月后先 grep 上个月的月份串**：模板里的「10-01~10-19 已并入 10-20」「差异 143 人」「录单海量、转化偏低」这类写死文案在 11-01 全部变错，已改为按数据现算（`__HEAD_NOTE__` / `__DAILY_TAIL__` / 转化率分档 <2.5 / 2.5~4 / ≥4）。
3. **单日窗口没有环比**：`dates` 只有 1 天时 `prev=None`，4 张 KPI 卡显示「新周期首日 · 无可比日」，**不要拿上月存档凑环比**。
4. **首页「数据区间」取 `window.start`**（不是 `dates[0]`），否则跨月会和口径表打架。
5. **口径表 `.scope-tbl` 允许换行**：全局 `th,td{white-space:nowrap}` 会把长文案右侧硬裁；媒介/逐日表保持 nowrap。看报告专门扫一眼这类长文本行。
6. **逐日表「差异」行带符号**：`合计 = 逐行相加 + 差异`，别恒显示负号。
7. ECharts 横向条形图：容器高度随条数动态给（`h = 条数*27+56`）+ 类目轴 `interval:0`，否则标签被自动隐藏（表现为「媒介名时有时无」）。校验 `check_charts.py`。
8. 4 张表的**跨组同档联动高亮**：指针停在某一档（新客首次/新客二次/新客/老客/总人数），**该行「来院人数」与「成交人数」的同一档同时亮，恰好 2 格**。不是整组高亮、不是按组配色（用户 10-15 16:17 纠正过）。回归 `check_group_hl.py`（4 表 × 5 档 = 20/20 PASS）。⚠️ 以后接到「联动高亮」需求，先确认高亮范围（同一格/同一档/同组/整列/整行）再动手。
9. **4 张主表都要有合计行**（2026-11-07 靓仔提，原先只有逐日表有）：03/04 的 TOP20 表给两行 tfoot ——「本表 TOP20 小计」+「全部 N 个媒介合计」；05 咨询师表、08 全部媒介表各一行「合计」。数值取 `window_totals`（已验证逐行相加与区间合计零差；若将来有差，`ft_note()` 会自动追加说明）。08 表在 `.scroll` 里，`td.ft` 用 `position:sticky;bottom:0` 吸底，否则 50 行要滚到底才看得见。
10. **速览与核心结论必须分新客/老客**（2026-11-07 靓仔提）：02 的「昨日来院/成交」与「N 天来院/成交」四张卡都要有 `新客 X · 老客 Y` 拆分行（蓝＝新客、橙＝老客）；01 核心结论首条带拆分，并单列一条「新老客结构」——来院→成交转化分别给新客/老客，新客再拆首次/二次，金额也拆新老。全部从 `window_totals` 现算，禁止写死。
11. **五档相加对不上时不许「修平」**：区间合计按人去重，会出现「首次+二次 > 新客」「新客+老客 ≠ 总人数」1~2 人的差（10 月实测 169 vs 154、185 vs 184）。`id_note()` 会在 03 表下自动解释原因；看规模一律用「总人数」列，别改数字去凑恒等式。

## 已知坑速查

- **内网访问必须禁用系统代理**（urllib 用 `ProxyHandler({})`），否则走 127.0.0.1:51832 失败。
- **必须用 playwright 浏览器**：8080 报表服务不能带 80 端口的 GD-CRM 登录 cookie，requests 不按端口隔离 → IIS 伪装 404。
  - 浏览器显式指定 `C:\Users\TJL\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe`（playwright 1.62 要 1234，本机只有 1243）。
  - 导出 Excel 是两步：`exportExcel('report1')` 只弹选项框，真正下载要调 `report1_saveAsExcel2('&excelFormat=2003&pageStyle=0&formula=0')` 并用 `page.expect_download()` 接住。
  - 登录返回 `{"statusCode":"200"}` 是**字符串**，别用 `== 200` 判断。
- `batch_fetch.py` 对「已存在且 >5000B」的 xls 会跳过，要重抓先移走旧文件。
- 残缺日数据不要留在 `data\raw\daily\`（会永久残留），隔离样本在 `data\_partial_2026-10-15\`。
- **CRM 停机后出现「报表只有表头」的空日**（10-17~10-19）：`analyze_sanfang.py` 已改 `.get(f, 0.0)`，别回退成 `tot[f] += ...`。
- **积压补录会污染单日口径**（10-20 建档 2,440，日常 140~190；10-21 成交 38 人 101.6 万）：判定方法是查 `(媒介来源, 网电咨询师)` 是否重复，无重复 = CRM 侧归日问题，**这类日要在结论里单独剔除，不能当趋势拐点**。
- **「10-31 永久缺失」是误判、已推翻**：月初只做「按天归并」（单日查仍空），但**整月区间数据保留、能导出**。要补上个月：直接把「上月1号~月末」整段查一次导出，不要在当月窗口里二分判断。
- 项目非 git 仓库 → 生成类脚本要自己留档（`history\`）；主报告现已自动留档（同窗口同 md5 去重，同日数字变了会新增一份而不是覆盖）。
- **区间报告 `gen_range_report.py <起> <止>`** 是手动指定区间的工具（不受「不跨月」约束），读 `data\analysis\daily\*.json`；历史报告重出走它。
- `check_group_hl.py` 只测含 `td[data-col]` 的表，新增表格别让它 `range(n_tbl)` 崩掉。

## 月报重出流程（`gen_month.py [YYYY-MM]`，`gen_oct.py` 是兼容壳）

### 关键架构：**月报与日报共用同一份模板**
`gen_month.py` 不维护自己的模板，它只是设置两个环境变量后调用 `gen_report_sanfang.py`：
`SANFANG_SRC`（读哪份 sanfang.json）、`REPORT_OUT`（写到哪个文件名）。
→ **日报版式改动（新老客拆分、表格合计行等）自动带到月报，不需要改两份**。
（2026-11-07 之前 `gen_oct.py` 靠正则替换 OUT_HTML 实现，同样共用模板；现已泛化。）

### 数据源优先级（只读，绝不动当月四件套）
1. `data\archive_YYYY-MM\sanfang.json`（月报重出时留下的归档基准）← 首选
2. `data\analysis\sanfang.json`（仅当其 `window.start` 属于目标月份）

### 重出步骤
① `probe_oct.py` 导出上月区间 → ② **备份当月四件套** `range.xls / range_baseline.json / window.json / sanfang.json` → ③ 写上月 `window`（`queryable_start` 取月末最后一个有明细的月份段首日，如 10-20）→ ④ `build_range_baseline.py` → `analyze_sanfang.py` → ⑤ `gen_month.py 2026-10` 输出 `三方营销媒介分析报告_2026年10月.html`（不覆盖日报主文件）→ ⑥ **恢复当月四件套并重跑 `gen_report_sanfang.py` 复核 md5**。上月基准另存 `data\archive_YYYY-MM\`。
**若归档 json 已存在，可跳过 ①~④ 直接跑 ⑤**（不联网、不动当月数据，最快最安全）。

### 区间报告 `gen_range_report.py` 是独立模板
它读 `data\analysis\daily\*.json` 逐日累加，有自己的 `TMPL`，**不继承日报模板**；KPI 卡的新老客拆分已于 2026-11-07 单独对齐（合计行原本就有）。

## 硬性禁令

- 只统计 CRM 现在查得到的部分，**不掺历史存档、不推算、不补录**；查不到的日期一律不纳入。
- **不伪造任何数据**。脚本失败（内网不通 / 登录失败 / 报表接口报错）就如实报失败原因和报错，不生成占位数字、不沿用上一版报告。
- 汇报时给出：报告路径、实际统计区间、区间合计 + 最新一天核心数字（录单/来院/成交/金额 + 环比）、观察到的异常（暴涨暴跌、负额冲账、零转化媒介）、一句话结论。

## 关联

- **定时任务**：`三方营销日报`（id `e83f79a3-cfe0-4b95-9de2-bea94fae2514`，每天 08:00，ACTIVE）的 prompt 只负责「加载本 Skill 并按《每日定时任务执行 SOP》执行」+ 最小兜底禁令。**改执行逻辑、汇报格式、口径只需改本文件一处**，不要再回去堆长 prompt；改完记得复核 `automation_update mode=view` 与账本 SK-096 版本。
- 权威项目级记忆：`C:\Users\TJL\WorkBuddy\2026-10-14-15-59-59\.workbuddy\memory\MEMORY.md`（8 节）；首轮全过程在 `2026-10-14.md`。
- 下游：`weekly-report-fill` 消费 `sanfang.json` 的 `window_totals / total_trend / daily_sum / crm_segment / src_total / emp_total / dates / window`。
- 资产账本：`C:\Users\TJL\WorkBuddy\2026-08-27-11-13-14\SKILLS-INDEX.md` 编号 **SK-096**（v1.3 / 2026-11-07）。
