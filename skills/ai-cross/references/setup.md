# 接入与盘点向导（探测先行，申报兜底）

面向不会安装配置的新人。逐步执行，每步失败就停下报错，不要跳步。

盘点由随附脚本 `inventory.py` 承担三件事：只读探测本机模型入口、把用户确认过的清单存成 manifest、派发时按 manifest 选默认人选。manifest 在用户主目录下（`$AICROSS_HOME/skill/manifest.json`，未设 `AICROSS_HOME` 时是 `~/.aicross/skill/manifest.json`），各宿主共用一份，skill 更新不影响它。**盘点每台机器做一次，不是每个宿主做一次。**

**"不盲扫本机" ≠ 什么都不看**：它指的是不读密钥文件、不凭猜测翻目录。第 1 步的只读探测是随附工具、安全边界明确（白名单见 `security.md`），**必须先跑**——新人答不上"我有哪些订阅"，探测就是替他回答这个问题的。盘点阶段只需读本文件；`channels.md` 的命令模板到逐项验证时才按通道查阅，不要预先全读。

## 第 0 步 — 识别宿主

判断当前跑在哪个 agent 里。**宿主自己不算外部通道。**

- 宿主是 **Claude Code**：内部 subagent 三档可用；claude CLI 仍可作 coding plan 载体（分支 B）。
- 宿主是 **Codex / WorkBuddy / Qoder / 其他**：**无内部通道**，全部走外部命令。盘点阶段第一个实际动作是**第 1 步的只读探测**（不是提问），不要尝试内部派发。

记下宿主名，选人时 `pick --host` 要用：`claude-code` / `codex` / `kimi` / `antigravity`。其他宿主（Qoder、WorkBuddy、ZCode 这类聚合型或底层模型不确定的）照实写它的名字——脚本不认识的宿主不算作交叉验证的一方，默认改选两家外部厂商互审。

**壳 ≠ 模型**：zcode(ZCode)、Qoder 桌面、Hermes、OpenClaw、WorkBuddy 这类是 harness/壳，不是可派发的模型。派发目标永远是**模型**，经三种方式之一触达：①官方 CLI（claude/codex/gemini/qoder）②Anthropic/OpenAI 兼容端点（GLM/Kimi/DeepSeek）③按量 API。用户报"我有 zcode/z.ai"时，其底层模型是 GLM，走分支 B 直连智谱端点，**不需要装它的桌面，也不需要经过任何路由壳**。只有桌面 GUI、无 CLI 也无 API 的工具无法被任何方式派发（路由壳也救不了——它自己也得靠 API 触达模型）。

## 第 1 步 — 只读探测（先做，不等用户回答）

新人往往答不上"我有哪些订阅"，所以**探测先行、申报兜底**：先跑探测，拿到事实再提问。**绝不允许空着检测结果直接反问用户"你有哪些订阅"**——那是把盘点的工作推回给最回答不了它的人。

```
python <本skill目录>/references/inventory.py detect --human   # 给用户看的摘要
python <本skill目录>/references/inventory.py detect           # JSON：每个通道的完整模型清单，第 2 步拟方案用
```

Windows 上若 `python` 不存在，改用 `py -3`。脚本一次做完这些事，约十秒：

- 找 `claude` / `codex` / `kimi` / `pi` / `agy` 并取版本号（kimi、agy 在 Windows 上装完不进 PATH，脚本会补试默认安装位置）；`aichat` / `qoder` / `codebuddy` / `hermes` 只查在不在。
- 读各家的模型清单事实源：codex 的 `~/.codex/models_cache.json`、kimi 的 `~/.kimi-code/config.toml` `[models]` 段、`agy models`、`pi --list-models`（只列已登录的 provider）、cc-switch 里已存 key 的 Anthropic 兼容供应商。claude 没有清单，用静态档位 haiku / sonnet / opus。
- 按模型 ID 标出权重厂商；认不出的留空，不猜。
- 读 `~/.claude/settings.json`、`~/.codex/config.toml`、kimi 配置里的当前默认模型，作为 `preferred_model`。

**这是"探测"，不是"盲扫"，默认直接执行**：在同一条消息里告知用户"正在只读检测本机模型入口"即满足知情原则（白名单见 `security.md`），无需停下等许可。它不登录、不发模型请求、不读密钥字段、不写任何文件、零费用。

**不要自己再逐条跑 `--version`，也不要凭记忆写模型 ID**——后面每一步用到的模型 ID 只从这份输出里取。输出里带 `warning` 的通道原样转告用户（例如 `settings.json` 里被写了全局 `ANTHROPIC_BASE_URL`）。

### cc-switch 只读桥：细节与铁律

很多多模型用户用 [cc-switch](https://github.com/farion1231/cc-switch) 管配置。它把用户**手动添加**的各 CLI 供应商存在 `~/.cc-switch/cc-switch.db`（SQLite）。注意：这是用户申报过的清单，不是探测结果——信任级别同申报，好处是免重输。`inventory.py detect` 已经把其中能直接派发的供应商列为 `cc-switch:<名字>` 通道；想单看原始清单用 `python <本skill目录>/references/cc_switch.py list`，**token 从不输出**。

- **派发时**用同一脚本的 exec 模式：
  ```
  python cc_switch.py exec --provider "Zhipu GLM" --tier sonnet --task "..."
  python cc_switch.py exec --provider "Zhipu GLM" --tier sonnet --task-file task.txt
  ```
  任务含引号/花括号/换行时**务必用 `--task-file`**（shell 会拆碎 `{}` 和转义引号，实测踩过）。token 只在脚本子进程内读取注入，**绝不进主 agent 上下文**。仅支持 `app_type=claude`（Anthropic 端点）；codex/gemini 官方订阅走各自 CLI。

- **实测边界（cc-switch v3.8+，2026-07-08）**：有保存 key 的 provider，token 明文存于 `settings_config.env.ANTHROPIC_AUTH_TOKEN`（cn_official 订阅模板 GLM/StepFun 与 custom 类讯飞均如此，cc-switch 不加密第三方 key）。空/陈旧条目无 token → 不列为通道，key 让用户去 cc-switch 里补。
- **额外红利**：env 里的 `ANTHROPIC_DEFAULT_HAIKU/SONNET/OPUS_MODEL` 就是**用户配的当前档位→模型映射**，探测结果里直接标成 low / mid / high，模型 ID 取实时值、免猜、免维护漂移。
- **铁律**：只读，绝不修改其 db；**绝不采用它的"切换"机制**（它靠把当前供应商写进 `~/.claude/settings.json` 来切换、一次只激活一个，正是要避开的全局污染）。我们的价值恰是把它存的多个供应商用**按进程环境变量并发跑起来**。提取到的 key 只在派发时按进程注入，manifest 只记通道名与端点，不记 key。

### usage_probe：用量痕迹（可选，耗时数十秒）

`python <本skill目录>/references/usage_probe.py --days 30` 聚合本机各 CLI 用量日志，输出每个 (来源 CLI, 模型) 的调用次数与首末时间。**只出元数据，对话内容一律不读不输出。** 盘点不依赖它；用户想知道"我实际在用哪些模型"或要查模型漂移时再跑：

- **预填**：近期高频的模型 ID 就是"用户实际在用的"，拟方案时优先选它。
- **信任边界**：模型字段多为**请求值**，不代表服务端真身——第三方端点仍必须过 `verify_model.py`；日志只证明"用过"，不证明"现在可用"。

## 第 2 步 — 拟方案，一次性确认（只问一次）

从第 1 步的 JSON 拟一份登记方案，规则：

- 每个要纳入的通道一条，**一条只放一家厂商的模型**。
- `tiers` 里的模型 ID 逐字取自该通道的 `models`。探测结果已标 `tier` 的（claude、cc-switch）直接用；其余按清单里的说明（`note`）、命名和 `preferred_model` 判断：`low` 取便宜快速的，`high` 取最强的，`mid` 可以不填。拿不准的只填一档，在确认表里标"待确认"。
- 用户说要纳入的通道都登记。同一家厂商经两个通道可达（如智谱同时在 `pi:zai-coding-cn` 和 `cc-switch:Zhipu GLM`）时两条都建，选人时同厂商只会取排在前面的那条；它们走同一份额度的话，`billing_source` 填同一个名字。
- **只有聚合通道例外**（一个通道里有多家权重：`agy`、pi 下的聚合 provider）：只为**别处没有的厂商**建条目（如 `agy` 取 Gemini），不把里面每家都建一遍；`billing_source` 填聚合平台名——同一份额度的条目会一起熔断。
- `billing`：订阅或 coding plan 内的填 `subscription`，按次真扣钱的填 `per-call`，不知道就在确认时问。
- 探测不到的入口（环境变量里的 coding plan key、按量 API）用 `manual:<名字>` 申报，必须写 `vendor`；这类条目的模型 ID 不经核对，来源记为"申报"。

把方案摆成一张表，用当前宿主的交互提问机制**一次问完**：

| 宿主 | 提问机制 |
|---|---|
| Claude Code | `AskUserQuestion`（支持多选） |
| Codex | `request_user_input`；不可用时退化为逐条文本提问 |
| 其他 | 逐条文本提问 |

**推荐提问模板**（按实际检测结果改写）：

> 我在你机器上只读检测到这些模型入口（没有读取或显示任何密钥），打算这样登记：
>
> | 通道 | 厂商 | 低档 | 高档 | 计费 |
> |---|---|---|---|---|
> | codex | OpenAI | gpt-x-luna | gpt-x-sol | 订阅内 |
> | cc-switch:Zhipu GLM | Zhipu | glm-x-flash | glm-x | 待确认 |
>
> 未找到：claude / kimi / aichat…
>
> ① 哪些不要纳入？档位选得不对的直接改。
> ② 标了"待确认"的，哪些是按次扣钱的？
> ③ 还有没有探测不到的入口？（按量 API key——DeepSeek / OpenRouter，或存在环境变量里的 coding plan key）

用户确认后，把方案写成 JSON 文件（放 `${AICROSS_HOME:-~/.aicross}/scratch/`，存完删掉）再保存：

```json
{"entries": [
  {"channel": "codex", "billing": "subscription", "tiers": {"low": "gpt-x-luna", "high": "gpt-x-sol"}},
  {"channel": "agy", "billing": "subscription", "billing_source": "Antigravity",
   "tiers": {"low": "gemini-x-flash-low", "high": "gemini-x-flash-high"}},
  {"channel": "manual:deepseek-api", "vendor": "DeepSeek", "billing": "per-call",
   "tiers": {"low": "deepseek-chat"}}
]}
```

```
python <本skill目录>/references/inventory.py save --plan <方案文件>
```

`save` 会重新探测一遍并逐个核对模型 ID。它拒收时照报错改方案，不要绕过：「模型不在清单里」说明 ID 写错了或已下线；「认不出厂商」时在该条目写明 `vendor`。重新保存同名条目会覆盖，其余条目保留；模型没变的条目沿用原来的冒烟记录。

**确认之后才有动作**：冒烟是真实的（订阅内）调用；代为安装 CLI、写配置、读含 key 的字段，都必须等用户点头。

### 兜底：没有 Python 或探测全失败

没有 Python 时脚本跑不了，改为手工：逐条跑 `claude --version`、`codex --version`、`kimi --version`（Windows 补试 `~/.kimi-code/bin/kimi.exe`）、`pi --version`、`agy --version`（Windows 补试 `%LOCALAPPDATA%\agy\bin\agy.exe`），读上面列的事实源文件里的模型字段，把确认结果按下面的模板手写成 `~/.aicross/skill/manifest.md`，之后每次读它；默认审查者写在文件末尾一行。

```markdown
# 能力清单 manifest
盘点日期:YYYY-MM-DD

| 通道 | 厂商 | 低档 | 高档 | 计费 | 来源 | 冒烟结果 |
|---|---|---|---|---|---|---|
| codex | OpenAI | gpt-x-luna | gpt-x-sol | 订阅内 | 读:~/.codex/models_cache.json | ✅ YYYY-MM-DD |

默认审查顺序：<通道> → <通道>
```

全新机器（无任何 CLI、无 cc-switch）时用下表逐条问：

> 请勾选你已有的模型入口（可多选）：
> ① Claude（Claude Code / Pro / Max 订阅）
> ② Codex（ChatGPT 订阅）
> ③ Gemini（⚠️ 独立 CLI 已下线，2026-07 核实；Antigravity 的 `agy` 可用，见 `channels.md`）
> ④ Qoder（CLI 与 IDE 共享 Credits，算一个源）
> ⑤ CodeBuddy / WorkBuddy（同账号通用，算一个源）
> ⑥ 智谱 GLM Coding Plan（订阅制 → 分支 B）
> ⑦ Kimi 会员 / Kimi Code（订阅制：装了 kimi CLI（OAuth）→ 分支 A；有控制台 API key → 分支 B）
> ⑧ 按量 API（DeepSeek / OpenRouter / 其他 → 分支 C）
> ⑨ 其他 agent 或模型（请说明名字）

## 第 3 步 — 逐项验证（只验证登记的条目）

每个条目冒烟一次，结果当场记进 manifest：

```
python <本skill目录>/references/inventory.py set --smoke <条目>=ok
python <本skill目录>/references/inventory.py set --smoke "<条目>=fail:<一句话原因>"
```

条目名看 `save` 的输出（形如 `codex.openai`、`cc-switch-zhipu-glm.zhipu`）。冒烟失败的条目留在清单里并标失败，选人时自动跳过，避免下次重复试错。

用户是带着具体任务来的、盘点只是顺带时，只冒烟这次要用的那一条，其余留到第一次用到时再做（SKILL.md「新人从这里开始」第 2 条）。

### 分支 A：官方 agent CLI

每项三小步：存在检测 → 登录 → 冒烟。冒烟用该条目的低档模型，下表的模型名只是示例。

| CLI | 冒烟（最便宜档） |
|---|---|
| claude | `claude -p --model haiku "只回复OK"` |
| codex | `codex exec -m <低档模型> -c model_reasoning_effort="low" -s read-only --skip-git-repo-check "reply OK"` |
| kimi | `kimi -p "只回复OK" -m <低档模型>`（不在 PATH 时用 manifest 里记的 `path`） |
| agy | `agy --model <低档模型> --output-format json --print="只回复OK"`（解析 `response`，为空即失败） |
| pi | `pi --provider <provider> --model <低档模型> -p --no-tools --no-extensions --mode json --no-context-files "只回复OK"`（真身看 `responseModel`） |
| hermes | `hermes chat -q "只回复OK" -Q`（以其配置为准，额度归属问用户） |

- **CLI 不存在**：按下方附录给出安装命令，征得同意后代为安装；装不了则不登记。
- **版本**：版本号已由探测记入 manifest，**不自动升级**（可能有破坏性变更）；仅冒烟失败且疑似过旧时才建议升级。
- **认证错误**：agent 无法代替用户完成 OAuth 登录——提示用户在自己终端运行登录命令（`claude` 首次启动 / `codex login` / `kimi login`），完成后回来重测。
- **参数报错**（`unrecognized arguments` 等）：跑 `<cli> --help` 看当前参数，去掉非必要项用最小命令重试，并提示更新 `channels.md`。

### 分支 B：coding plan（GLM / Kimi 等订阅）

载体是 claude CLI + 按进程环境变量。**不要用 aichat 接 coding plan**——多数条款限定其只能用于 coding agent，且网关常拒非 agent 流量。

1. 确认本机有 claude CLI，没有则先装（**免费；装了不等于要买 Claude 订阅**，第三方端点用 env 覆写认证）。
2. 引导用户到对应控制台创建 API key（智谱：开放平台 → 个人编程套餐 → 套餐概览建 key；Kimi：Kimi Code 控制台）。此 key 与 zcode/ZCode 桌面用的是同一个、同一份订阅额度池，直连端点即可，无需装桌面。
3. key 存为用户级环境变量，不落明文：Windows `setx GLM_CODING_KEY <key>`（Kimi 同理），类 Unix 写入 shell profile。**若 key 已在 cc-switch 里，探测结果里已有对应的 `cc-switch:<名字>` 通道，直接用 `cc_switch.py exec`，跳过本步。**
4. 用 `channels.md` 的 coding plan 模板冒烟；第三方端点必须过 `verify_model.py` 真身核对。
5. 存在环境变量里的 key 探测不到，用 `manual:<名字>` 登记，额度归属写对应 coding plan。

### 分支 C：按量 API（aichat，最后的兜底）

1. **检测**：`aichat --version`，已装跳到第 3 小步。
2. **代为安装**：Windows `winget install sigoden.aichat`（失败试 `scoop install aichat`）；macOS `brew install aichat`；Linux 从 https://github.com/sigoden/aichat/releases 下载二进制入 PATH。全部失败才让用户手动装并停在这步。
3. **收集三项**：先选预设，预设内只需粘贴 API key：

| 预设 | api_base | 默认模型 ID |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 智谱按量 API（非 Coding Plan） | `https://open.bigmodel.cn/api/paas/v4` | 以官网当前型号为准 |
| OpenRouter | `https://openrouter.ai/api/v1` | 用户指定 |
| 自定义 | 用户填 URL | 用户填模型 ID |

4. **写配置**：Windows `%APPDATA%\aichat\config.yaml`；macOS `~/Library/Application Support/aichat/config.yaml`；Linux `~/.config/aichat/config.yaml`。**已存在则先读再追加 client，绝不整体覆盖**：

```yaml
model: <name>:<model_id>
clients:
  - type: openai-compatible
    name: <name>
    api_base: <api_base>
    api_key: <api_key>
```

5. **冒烟**：`aichat -m <name>:<model_id> "只回复两个字：正常"`。已配置的全部模型可用 `aichat --list-models` 枚举。
6. 用 `manual:<名字>` 登记，`billing` 填 `per-call`。

## 第 4 步 — 默认人选与备注

**默认审查顺序由脚本排**：订阅内的先于按次计费的，盲审隔离完整的通道（claude `--restricted`、pi `--no-context-files`）先于只做到空目录的，其余按方案里的先后。看结果：

```
python <本skill目录>/references/inventory.py show --human
python <本skill目录>/references/inventory.py pick --role reviewer --host <宿主名>
```

用户有自己的偏好时改默认值，一次改完以后都生效：

```
python <本skill目录>/references/inventory.py set --reviewers <条目>,<条目>    # 这几家排最前，其余顺延
python <本skill目录>/references/inventory.py set --executor <条目>:low        # 默认执行者；不设就按路由表
python <本skill目录>/references/inventory.py set --billing <条目>=per-call
python <本skill目录>/references/inventory.py set --note "<一句话备注>"
```

- 聚合型订阅（一份额度里含多家权重，如千问 Token Plan 含 GLM/DeepSeek/Kimi/MiniMax）：按**权重厂商**分条目登记，`billing_source` 填**聚合平台名**。这类源的权重独立性成立（可交叉验证）、计费独立性不成立（熔断一起没）。
- 备注只记**可复现的具体缺陷**（如"肉眼计数 33%"、"统计推导方法标注错误"）和用户当场纠正的路由偏好。

### ⛔ 不要给通道打「自算可靠性」评级（实测：这个抽象是错的）

曾计划用一道递推题给每个通道打 `自算 k/n` 分。**实测证明该评级不稳定、会误导**：

| 同一道 51 步递推题 | GLM | StepFun |
|---|---|---|
| 硬基准（n=3） | 3/3 | 1/3 |
| 独立探针（n=3） | **1/3** | **2/3** |
| 合计 | 4/6 | 3/6 |

**完全反转，都接近抛硬币。** 对照 `tools` 字段：答对的那几次模型**写了代码去跑**，答错的那几次它**心算**了。

**「自算准不准」不是厂商属性，是「它这次选没选择写代码」的随机结果。** 而探针里那句「你可以心算、手算或写代码，方式不限」正是邀请失败的元凶。

**→ 正确做法（见 SKILL.md 铁律）**：不评级，而是在**每次派发精确计算任务时**，prompt 明确命令「写代码并执行，给出运行结果」；模型不能执行代码时，**编排者独立核验**。

**判定"它不会算"之前，先排除传参问题**：多行 prompt 经 argv 传给 `codex exec` 会在首个换行截断（见 `channels.md`）。**先确认它收到了完整题目。**

## 第 5 步 — 报告（含期望校准）

把 `show --human` 的输出给用户，并说明：清单存在哪、有几家厂商、当前宿主下默认派谁审查、哪些条目冒烟失败。

**告诉用户以后怎么用**——只需要记住这几句话，不用写记忆、不用改配置文件：

| 用户说 | 发生什么 |
|---|---|
| 「让别家审一下」「交叉验证一下」 | 用默认审查者，派发前给一行建议，点头才发 |
| 「这次让 Gemini 审」 | 只改这一次 |
| 「以后审查都先用 Gemini」「以后实现都派 GLM」 | 改默认值，以后都生效 |
| 「重新盘点」「更新模型」 | 重跑第 1–3 步 |

**必须包含「组合解锁表」——按用户实际组合如实校准期望，不吹不瞒**：

| 你的组合 | 能做什么 | 做不了什么 | 最便宜的下一步 |
|---|---|---|---|
| 仅 Claude Code（单厂商） | 内部三档分层（scout/worker/heavy，几乎免费）、留痕、闭环 | **跨厂商交叉验证**（本 skill 核心价值）——同厂商复查只算"复核" | 接入任一第二厂商即解锁：GLM/Kimi coding plan（订阅制，走分支 B）或 DeepSeek 等按量 API（充几元即可，走分支 C），以各家官网当前价为准 |
| 仅 Codex（单厂商） | 外部分层（codex 三档）、留痕、闭环 | 同上；且无内部 subagent，分层全走外部 | 同上 |
| Claude Code + Codex | **完整能力**：交叉验证、双保险、分层、熔断主备 | — | 可选：再加一家中文厂商做三方面板 |
| 任一宿主 + ≥1 个 coding plan/按量 key | 交叉验证（宿主厂商 × 第三方厂商）、额度分摊 | — | — |
| 聚合型或底层不确定的宿主 | 两家外部厂商互审（宿主不算一方） | 宿主与外部一对一的交叉验证 | 至少登记两家不同厂商 |

单厂商用户要**明确告知**："当前组合只有分层收益，交叉验证要等第二家厂商接入"——这不是 skill 故障，是能力门槛（SKILL.md「派发单元与门槛」）。

## 第 6 步 — 首次派发演示（可选，建议做）

盘点报告后问用户一句："要不要跑一次演示派发，直观看看交叉验证长什么样？（约一次冷调用 × 2 的成本，全程只读、不碰你的项目文件）"。同意后执行：

1. **选通道**：`inventory.py pick --role reviewer --host <宿主名> --author none --n 2 --tier low` 给出两家**不同厂商**的最便宜档。只凑得出一家时退化为分层演示（低档执行 + 编排者核验），并**明说这不是交叉验证**。
2. **派发**：用 SKILL.md 的冻结盲验模板 + 下面这段内置演示代码（**不读用户项目文件**——演示的安全边界就是它自己），并行发给两路，prompt 为中性审查请求：「请独立审查这段代码，列出你发现的问题、依据与不确定处。不要猜测提供者想听什么。」
3. **留痕**：两路原始输出存 `.dispatch/`（顺带演示留痕机制，`.gitignore` 一并建好）。
4. **核对与汇总**：对照下方「已知缺陷答案」（⚠️ 答案绝不进派发 prompt），给用户三样东西：**共识**（两家都抓到的）、**分歧**（只有一家抓到的/意见相反的）、**账单**（每路 token 与耗时）。两家高度一致也是合法结果，如实展示即可。

演示代码（含植入缺陷，自包含）：

```python
def summarize_scores(scores, top_n=3):
    """返回全体平均分与前 top_n 名。scores: {姓名: [各次得分]}"""
    avgs = {}
    for name, vals in scores.items():
        avgs[name] = sum(vals) / len(vals)
    top = sorted(avgs, key=avgs.get)[:top_n]
    total_avg = sum(avgs.values()) / len(scores)
    return {"total": round(total_avg), "top": top}
```

已知缺陷答案（仅编排者核对用）：① `vals` 为空列表时 `ZeroDivisionError`；② `sorted` 默认升序，`[:top_n]` 取到的是**倒数** top_n，应 `reverse=True`；③ `scores` 为空 dict 时除零；④ `total_avg` 是"各人平均的平均"，人数不等权时 ≠ 全体总平均（判断型缺陷，规格歧义）；⑤ `round` 取整丢精度（弱缺陷，规格未明）。①②③是硬伤，④⑤是判断题——通常正好能引出两家的分歧，这就是演示想让用户看到的东西。

---

## 附录：常见 CLI 安装命令

| CLI | Windows | macOS | Linux |
|---|---|---|---|
| claude | `npm i -g @anthropic-ai/claude-code` | 同左 | 同左 |
| codex | `npm i -g @openai/codex` | 同左 | 同左 |
| gemini | ⚠️ 独立 CLI 已下线（2026-07 核实，见 `channels.md`），不建议安装；若未来恢复再执行 `npm i -g @google/gemini-cli` | — | — |
| aichat | `winget install sigoden.aichat`（或 `scoop install aichat`） | `brew install aichat` | [releases](https://github.com/sigoden/aichat/releases) 下载二进制入 PATH |

以上为通用形态，**以各家官方文档当前值为准**；安装前先跑 `<cli> --version` 确认是否已装。装完让用户自行完成 OAuth 登录（agent 代替不了）。
