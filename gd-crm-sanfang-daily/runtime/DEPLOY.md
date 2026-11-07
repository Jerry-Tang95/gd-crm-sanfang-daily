# 新电脑部署（clone 即用）

> 前置条件不满足时，脚本会如实报失败，不会编数字顶上。先确认下面 4 条再动手。

## 0. 前置条件（缺一不可）

| # | 条件 | 自检 |
|---|---|---|
| 1 | **能连公司内网** `192.168.16.138` 的 80 / 8080 端口 | PowerShell：`(Test-NetConnection -ComputerName 192.168.16.138 -Port 80 -WarningAction SilentlyContinue).TcpTestSucceeded` → 必须 `True`。`PingSucceeded=False` 不代表离线（防火墙拦 ICMP） |
| 2 | Python 3.9+（建议 3.11+） | `python --version` |
| 3 | 内网 CRM 的账号密码 | 找系统管理员要，不写在仓库里 |
| 4 | 想让 Agent 自动跑，需要 WorkBuddy 之类的 Skill 环境 | 不装也能手工跑脚本 |

**这是硬前提：新电脑不在公司内网 / 没配 VPN，clone 下来也出不了数。** 此时先解决网络，不要改代码。

## 1. 安装（一次）

```bash
git clone https://github.com/Jerry-Tang95/gd-crm-sanfang-daily.git
cd gd-crm-sanfang-daily/gd-crm-sanfang-daily/runtime

python -m pip install -r requirements.txt
python -m playwright install chromium

# Windows
copy config.example.json config.local.json
# macOS / Linux
# cp config.example.json config.local.json
```

编辑 `config.local.json`，填 `username` / `password`。该文件已被仓库根 `.gitignore` 排除，**不会进版本库**。

## 2. 跑日报

```bash
python run_daily.py        # 不带参数 = 昨天；约 1~8 分钟，别中途当卡死杀掉
```

产出同目录的 `三方营销媒介分析报告.html`，并自动留档到 `history/`（同窗口同内容只留一份）。中间数据在 `data/`：`window.json`、`range.xls`、`range_baseline.json`、`sanfang.json`。

**判成功（最关键）**：`analyze_sanfang.py` 必须打印 `建档 X | 来院 X | 成交 X 人 | 业绩 X 元` 累计行。没有这行 = 分析崩了，而 `gen_report` 仍可能拿旧 json 出一份「看起来成功」的 HTML → **判失败，不许沿用上一版报告**。

## 3. 跑完校验

```bash
python verify_days.py <最新日>        # 单日四项与区间逐项一致
python check_group_hl.py              # 4 表 × 5 档 = 20/20 PASS
python check_charts.py                # ECharts 类目标签全显
python verify_against_crm_export.py "<你从 CRM 导出的.xls>"   # 逐媒介并排比
```

## 4. 装 Skill（可选，让 Agent 自动跑）

```bash
# Windows：把整个 gd-crm-sanfang-daily 目录复制到
#   %USERPROFILE%\.workbuddy\skills\
# 只需说明书的话，只复制 SKILL.md + test-prompts.json 两个文件即可
```

装完问一句「跑一下今天的三方营销日报」验证触发；再问「用云客 CRM 拉一份团队周报」应**不**触发。

**定时任务搬不过来**：WorkBuddy 的自动化绑定账号/机器，仓库里没有。新电脑上要重建一个每天 08:00 的任务，prompt 只写「加载 `gd-crm-sanfang-daily` 并按《每日定时任务执行 SOP》执行」+ 最小兜底禁令，执行逻辑全在 `SKILL.md` 一处。

## 5. 可选环境变量

| 变量 | 作用 | 默认 |
|---|---|---|
| `CRM_BASE_URL` | 内网 CRM 地址变了时覆盖 | `http://192.168.16.138` |
| `CRM_CHROME` | 指定 `chrome.exe` / `chromium` 可执行文件 | 空 → 用 Playwright 自带浏览器 |

## 6. 哪些东西故意没进仓库

| 排除 | 原因 |
|---|---|
| `config.local.json` | 账号密码 |
| `data/` | 原始 xls / 中间 json，含真实业绩数据 |
| `history/` | 历史报告留档 |
| `*.html` / `*.xls` | 生成物，跑一次就有 |
| `probe*.py`、`备份_*`、各种 `one.html` | 一次性调试脚本与实验产物 |

## 7. 维护（只在源机器做）

生产真源是项目工作区里的 `gd-crm-媒介日报\`，本目录 `runtime/` 是**发布副本**，方向单向。源目录改了脚本后：

```bash
python tools/sync_runtime.py --src "<生产项目目录>"
```

它会重新生成 14 个脚本并自动打上 4 类可移植补丁（解释器 / 浏览器 / 内网地址 / 图表库），然后重新发布仓库。**不要反向把 runtime/ 的改动拷回源目录** —— 两份代码不同步正是当初「改了还是不行」的根因。
