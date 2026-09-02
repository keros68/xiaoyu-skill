# 外部通道命令模板

抽象定义："命令模板 + 模型参数"。换任何等价 CLI 只需替换模板，其余逻辑不变。模型名会过时，以各 CLI 当前版本为准替换。

**所有外部派发统一附 `AI_CROSS_PEER=1` 环境变量**（防套娃标记）：bash 用前缀 `AI_CROSS_PEER=1 codex exec …`；PowerShell 先 `$env:AI_CROSS_PEER='1'` 再调用；`cc_switch.py exec` 已自动注入。被派方若也装有 ai-cross，检测到该变量即知自己是子任务，只执行不再外派（规则见 SKILL.md 稳健性规则「防套娃」条）。

**验证者一律在空目录里跑**（盲验目录隔离，规则见 SKILL.md「验证的框架隔离」）。项目目录里的 `.dispatch/`、`STATE.md`、`CLAUDE.md`/`AGENTS.md` 都携带我方结论，`codex exec`/`claude -p` 会加载项目指令文件，kimi 会自行打开 cwd 里的文件。两种写法：

```bash
# ① 纯文本材料：不给工具，材料走 stdin，cwd 无所谓
AI_CROSS_PEER=1 claude -p --model X --tools "" < blind.txt
AI_CROSS_PEER=1 codex exec -s read-only --skip-git-repo-check - < blind.txt

# ② 必须带工具（要读多个文件/跑代码）：原始材料拷进空目录，在那里跑
mkdir -p /tmp/blind-$$ && cp <原始材料...> /tmp/blind-$$/ && cd /tmp/blind-$$
AI_CROSS_PEER=1 codex exec -s read-only --skip-git-repo-check - < prompt.txt
```

`cc_switch.py exec` 的 cwd 就是调用时的目录，同样先 `cd` 进空目录再调。执行者（本来就要改项目文件的活）不受此限。

## 大材料怎么交给被派方（>30KB 必读）

「材料」指要被派方读的**那段内容本身**（一份稿件、几个源码文件拼起来的、你直接粘的一大段文字），不是"文件"这个概念。同一份材料有三种交法，代价差一个数量级——60KB 材料实测，末行埋标记核对是否完整送达（2026-08-24，Windows）：

| 交法 | 命令形态 | 60KB 实测 | 上限 |
|---|---|---|---|
| **从文件/stdin 读进去**（首选） | `cc_switch.py exec --task-file f.txt`、`codex exec < f.txt` | **6.8s 单轮**（DeepSeek-flash，25782 tokens）/ 31.6s（codex） | 无 |
| **内联进命令行** | `kimi -p "…整篇正文…"` | **命令发不出去** | Windows 命令行 ≈32KB 字节（中文约 1 万字） |
| **只给路径让它自己读** | `kimi -p "读 draft.md，审一下"` | 58.7s | 无上限，但最慢 |

- **32KB 那道墙是操作系统的，不是某个 CLI 弱。** 同样长度的 argv 喂给 `python.exe` 在同一位置失败（实测 32600 字节 ok、32700 字节 `Argument list too long`）。按 **UTF-8 字节**算，不按字符算：10000 汉字（30000 字节）通过、16000 汉字（48000 字节）失败。Linux/macOS 的 argv 约 2MB，**这是 Windows 专属故障**。
- **有 stdin 或文件入口的通道就绕开了这堵墙**：`claude -p`（prompt 走 stdin，`cc_switch.py --task-file` 即此路）、`codex exec`（`--help` 明载 stdin 作为 `<stdin>` 块附加）、裸 API（材料在请求体里，没有 argv 这回事）。**`kimi` CLI 三者皆无**（见下方 Kimi 段）。
- **"只给路径让它自己读"是最慢的形态**：模型要多轮调工具去读，每轮重发全部上下文，规模越大越超线性。能内联就别让它自己读——内联 + `--tools ""` + 单轮完成是最省也最快的形态。
- **换入口不等于能一次吃完。** 入口解决的是"能不能送进去"，送进去之后的时间由解码速度决定（他方报告转述、本机未复现：240KB 单轮内联仍要 8m30s）。超过单轮舒适区就**分块 map-reduce**，别指望找个更大的入口。
- **症状识别**：进程活着、CPU 近乎为零、stdout 长时间为空 → 看起来像"通道挂了"，实际优先怀疑两件事：**任务形态错了**（让模型自己读大文件）、**额度耗尽**（端点欠费时是挂住不返回、不报错，实测 GLM 挂满 180s 超时）。两者都不是性能问题，别按过载去重试。

## Codex 三档

```bash
# 低档：快速琐事（gpt-5.6-luna = fast and affordable）
codex exec -m gpt-5.6-luna -c model_reasoning_effort="low" -s read-only \
  --skip-git-repo-check "[任务]"
# 中档：常规第二意见（gpt-5.6-terra = balanced everyday）
codex exec -m gpt-5.6-terra -c model_reasoning_effort="medium" -s read-only \
  --skip-git-repo-check "[任务]"
# 高档：深度分析/关键审查（gpt-5.6-sol = latest frontier，effort 支持到 max/ultra）
codex exec -m gpt-5.6-sol -c model_reasoning_effort="xhigh" -s read-only \
  --skip-git-repo-check "[任务]"
# 代码特化档（可选，ultra-fast）
codex exec -m gpt-5.3-codex-spark -c model_reasoning_effort="high" -s read-only \
  --skip-git-repo-check "[任务]"
# 长文本走 stdin（会作为 <stdin> 块附加到 prompt 后）
cat file.txt | codex exec -m gpt-5.6-terra -c model_reasoning_effort="medium" -s read-only \
  --skip-git-repo-check "总结要点"```

- **stderr 别丢弃**：模板已不再接 `2>/dev/null`——codex 的 `tokens used` 与错误信息都走 stderr，丢弃它与"检查错误体/报告用量"的规则冲突。留痕时 stdout/stderr 都落盘；程序化消费用 `--json` 解析，别靠丢弃 stderr 换干净输出。
- **档位映射（2026-07-17 冒烟 5/5 全 OK）**：gpt-5.6 代三档 luna(低)/terra(中)/sol(高)按官方描述定档；上一代 `gpt-5.4-mini`/`gpt-5.4`/`gpt-5.5`/`gpt-5.3-codex-spark` 仍在售仍可用（用量日志漂移预警 → 冒烟确认的完整闭环首例）。
- **本地事实源：`~/.codex/models_cache.json`**——CLI 自己缓存的官方模型清单（slug/描述/默认与可用 effort/priority/`fetched_at`）。此前"codex 不支持枚举、用静态表"的说法**作废**：接入与刷新读这个文件，别手抄本文件里的 ID。
- **Codex 支持 stdin 管道**（实测 2026-07-08：`echo "1,2,3" | codex exec ... "求和"` → 正确返回）。`--help` 明载：stdin 被 pipe 时作为 `<stdin>` 块附加；prompt 用 `-` 亦可全部从 stdin 读。
- **⚠️ 后台/无 TTY 运行必须给 stdin EOF**（2026-07-17 实测）：正因为上一条，`codex exec` 见到非 TTY 的 stdin 会**一直等它关闭**；后台任务的 stdin 是永不关闭的管道 → 永久挂起（实测 4 连发挂 25 分钟零输出零报错）。前台交互（stdin=TTY）无此问题。脚本/后台里写法：PowerShell `'' | codex exec …`，POSIX `codex exec … < /dev/null`。
- **续聊：`codex exec … resume <thread_id> -`，选项必须放在 `resume` 之前**（codex-cli 0.149.1，2026-08-30 两轮口令实测 PASS）。首轮用 `--json`，从 `thread.started` 事件取 `thread_id`；续轮写成 `codex exec -s read-only --json --skip-git-repo-check resume <thread_id> -`，prompt 从 stdin 进。`-s`/`--json`/`--skip-git-repo-check` 是 `exec` 的选项，`resume` 子命令只认 `-c`；写在 `resume` 后面报 `unexpected argument '-s'`、exit 2。`--last` 取最近一次会话，`exec fork <id>` 分叉。每轮仍付一次冷启动足迹。
- 推理强度旋钮：`-c model_reasoning_effort="low|medium|high|xhigh"`。
- 不要用 `--full-auto`：当前 `codex exec --help` 已不列出该参数（虽仍被接受，属未文档化遗留别名，随时可能移除）。`-s read-only` 已够。
- **`gpt-5.3-codex` 不存在**（实测 2026-07-08：ChatGPT 账号报 `The 'gpt-5.3-codex' model is not supported when using Codex with a ChatGPT account`）。ChatGPT 订阅可用型号实测为：`gpt-5.4-mini` / `gpt-5.4` / `gpt-5.5` / `gpt-5.3-codex-spark`。**这是"未冒烟就别假设可用"的活教材**——该型号曾被本文件当作高档默认，直到实测才发现全线不可用。

## Kimi Code CLI（kimi，外部 agent CLI）

Moonshot 官方 agent CLI，OAuth 登录（`kimi login` 设备码流程），**无需 API key**——没配 `KIMI_CODING_KEY` 时这是唯一的 Kimi 通道。**Windows 实测（0.26.0，2026-07-17）装完不进 PATH**，二进制在 `~/.kimi-code/bin/kimi.exe`：模板用全路径，或让用户把该目录加进 PATH。

```bash
# 高档：K3（1M 上下文；effort low/high/max，默认 high，旋钮在 config.toml 无命令行参数
#       ——即 thinking 档位无法按次派发切换，路由时把 kimi 视为固定档通道）
kimi -p "[任务]" -m kimi-code/k3

# 低档：快速琐事
kimi -p "[任务]" -m kimi-code/kimi-for-coding-highspeed

# 冒烟
kimi --version && kimi -p "只回复OK" -m kimi-code/kimi-for-coding-highspeed
```

- **模型别名不要手抄，读本地事实源**：`~/.kimi-code/config.toml` 的 `[models."…"]` 段完整列出当前可用别名、真实模型 ID、上下文长度、effort 支持——派发前读它，别依赖本文件记的值。本机 2026-07-17 实测三个：`kimi-code/k3`（1M，efforts low/high/max）、`kimi-code/kimi-for-coding`（K2.7，256k）、`kimi-code/kimi-for-coding-highspeed`（K2.7 高速）。
- **⚠️ 无只读档（0.26.0 实测）**：`-p` 模式**不加 `-y` 也默认可写盘**（实测让它建文件，直接 Write 成功落盘）；`--plan` 与 `-p` 互斥（`error: Cannot combine --prompt with --plan`）；`--help` 无 tools 白名单参数。护栏只剩**工作目录隔离**：每次派发在专用空目录里跑（审查材料拷进去），**绝不在宿主项目目录里跑 kimi 并发派发**。**目录隔离只防相对路径误写，不是沙箱**——kimi 仍可按绝对路径写任何位置，不要对用户暗示这是"只读"。敏感工作区的咨询/审查任务，优先走有硬白名单的 `claude -p --tools Read,Grep,Glob` + Kimi 端点覆写（下方 coding plan 通道，需 API key）。
- **⚠️ 没有大输入入口（0.38.0 实测，2026-08-24）**：`-p` 只收 argv，**管道 stdin 被完全忽略**（实测 `echo "口令 PANDA-4417" | kimi -p "看到口令就回答它"` → 答 NONE），`--help` 也无 `--prompt-file`。于是 Windows 命令行 ≈32KB 的硬顶对 kimi 成了**没有出口的硬顶**——同一堵墙 `claude -p` 和 `codex exec` 都能靠 stdin 绕开，kimi 绕不过去。**>1 万汉字的材料别派给 kimi CLI**：走 `cc_switch.py exec --task-file` 或 `codex exec < file`，或分块。这不是模型能力问题，是壳少一个入口（壳 ≠ 模型的又一实例）。详见上方「大材料怎么交给被派方」。
- **思考关不掉**：`config.toml` 里 k3/K2.7 的 capabilities 均含 `always_thinking`，`[thinking] enabled = true`。即每次派发都付思考 token，**kimi 不能作为"关思考的便宜执行者"用**。实测 k3 可见输出吞吐 ~33 tok/s（1261 字 / 34s），长产出任务的耗时大头在解码，不在预填。
- **会主动读工作目录里的无关文件**（0.38.0 实测）：一次派发中它自行打开了 cwd 里残留的 `prompt.txt`，还在思考里纠结"这文件说不要调工具"。**目录隔离不只防误写盘，也防上下文污染**——作为验证者派发时，cwd 里的脏文件会破坏盲验。
- **超长行文件（0.26.0 实测，0.38.0 已不复现）**：旧版 Read 工具对单行数千字符的 Markdown 反复返回截断预览，10 轮零产出。0.38.0 复测（单行 20000 字符）模型改用 Bash `tail` 绕开，16.6s 正常完成。**若再遇到零产出**，仍按老办法把材料按 ≤100 字符换行（`textwrap.wrap`）后重派——这是升级阶梯第①条「先查输入是否送达」的实例。
- 输出混有 thinking 行（stderr）与 `To resume this session` 提示；程序化消费用 `--output-format stream-json` 解析，别整段当答案。
- 定位：**执行者通道**（本来就要写盘的活，在隔离目录里跑没问题）+ 无 API key 时的 Kimi 兜底。作为跨厂商验证者用时，记住上一条的目录隔离。

## pi（外部 agent harness，接多家 coding plan）

Earendil 出品的开源 agent CLI（github.com/earendil-works/pi），组织方式是 **provider → 模型数组** 两级：一个 pi 下能挂多个第三方 coding plan/API provider，每个 provider 下多个模型。用户已用它替代 cc-switch 接入多个 coding plan。

```bash
# 冒烟/低档：指定 provider + 模型，非交互单轮，JSON 输出，不加载项目指令，无工具
AI_CROSS_PEER=1 pi --provider zai-coding-cn --model glm-4.7 -p --no-tools \
  --no-extensions --mode json --no-context-files "[任务]"

# 只读（能读不能写，pi 自带的工具白名单预设）
AI_CROSS_PEER=1 pi --provider zai-coding-cn --model glm-4.7 -p --tools read,grep,find,ls \
  --no-extensions --mode json --no-context-files "[任务]"

# 大材料走 stdin（不给正文位置参数，pi 把 stdin 整体当消息）
cat file.txt | AI_CROSS_PEER=1 pi --provider zai-coding-cn --model glm-4.7 -p --no-tools \
  --no-extensions --mode json --no-context-files

# 续聊：固定 --session-id，跨进程能接上下文（无需保存/传递 session 文件路径）
AI_CROSS_PEER=1 pi --provider zai-coding-cn --model glm-4.7 -p --no-tools \
  --no-extensions --mode json --no-context-files --session-id <固定id> "[任务]"
```

- **模型清单事实源、别手抄**：`~/.pi/agent/models-store.json`（provider→模型数组，含 baseUrl/cost/contextWindow/是否支持 thinking 等元数据，可能含未鉴权条目）+ `pi --list-models`（运行时枚举，只报**已鉴权可用**的模型，更贴近"能不能派"）。`pi auth check --provider <名字> --json` 查 provider 是否就绪（只输出 `status`/`authType`，不吐 key）。本机 2026-08-30 实测 `pi --list-models` 列出两个 provider：`qwen-token-plan-cn`（deepseek-v3.2/v4-flash/v4-pro、glm-5/5.1/5.2、kimi-k2.5/2.6/2.7-code、MiniMax-M2.5、qwen3.6~3.8 系列）与 `zai-coding-cn`（glm-4.7/5-turbo/5.2/5.2-highspeed/5.3）。
- **`qwen-token-plan-cn` 经 pi 派发可用**（用户确认，2026-08-30）：走 pi 自己的 harness 就是该 plan 的正常用法，不属于「千问 Token Plan 合规注」拦的裸 key 脚本调用。它是**聚合型订阅**：一个计费源下挂 deepseek / glm / kimi / MiniMax / qwen 多家权重——独立性按权重厂商算（deepseek-v4-flash 与 glm-5.2 可互为交叉验证），额度按 `qwen-token-plan-cn` 一个源算（熔断一起没），manifest 里厂商列与额度归属列分开填（见 setup.md「聚合型订阅」）。
- **真身核对**：`--mode json` 的每条消息事件都带 `provider`/`model` 字段，可直接比对响应是否命中请求的模型（本机实测 `--model glm-4.7` 请求 → 响应 `provider":"zai-coding-cn","model":"glm-4.7"` 一致，未观察到静默降级；但只测了一个模型，不代表全体型号都不降级）。
- **⚠️ exit code 会假阴性（0.84.2 实测，2026-08-30）**：默认加载扩展时，`-p --mode json` 一轮正确应答（`agent_end`/`agent_settled` 均已出现、答案正确）之后，本机装的 `~/.pi/agent/extensions/advanced-footer.ts` 在渲染收尾时抛出未捕获异常（"ctx is stale after session replacement"），导致进程仍以 **exit 1** 退出——纯粹是这一个本地扩展的 bug，与任务本身无关。**派发命令一律加 `--no-extensions`** 可让 exit code 恢复为 0；即便加了，程序化消费也不该只信 exit code，应解析 JSON 流里是否出现 `agent_settled` 且末条 assistant 消息含 `text` 类型内容块。
- **⚠️ 答案可能只出现在 thinking 块里、text 块为空**（0.84.2 实测，2026-08-30，`--no-extensions` 下亦复现一次）：同一句"只回复 OK"，某次响应的 assistant content 只有一个 `type:"thinking"` 块（内容是"OK"），没有任何 `type:"text"` 块。这正是 `AGENTS.md`"判分绝不回退读 reasoning_content"那条铁律的活例子——解析 pi 输出时必须显式要求 `text` 类型内容块存在，为空不能回退去读 thinking/reasoning 字段当答案。
- **stdin 可行**：不给正文位置参数、把内容整段管道进去，pi 把 stdin 当消息，多行内容原样送达（2026-08-30 实测两行文本无截断）——与 `claude -p`/`codex exec` 同属"有 stdin 入口"的通道，不受 Windows argv 换行截断限制。
- **只读性优于 kimi**：pi 有真正的工具层白名单——`--no-tools` 关全部工具（已冒烟验证不落盘写不了）；`--tools read,grep,find,ls` 是官方文档给的只读预设（`--help` 自带示例，本次未逐条验证每个工具确实被挡，护栏来自工具注册层而非仅目录隔离）。也支持 `--no-context-files` 跳过 AGENTS.md/CLAUDE.md 加载，作验证者派发时能避免读到我方结论。
- **续聊**：`--session-id <固定id>` 在两个独立进程间可靠接上下文（2026-08-30 两轮口令 OTTER-2210 实测 PASS）；`--continue/-c` 续最近一次、`--resume/-r` 交互选择，未逐一冒烟。
- **思考旋钮**：`--thinking off|minimal|low|medium|high|xhigh|max`（`--help` 列出的档位），比 codex 的四档更细；`off` 是否真能关闭思考本次未冒烟验证，别假设等同 kimi 那种"关不掉"。
- 定位：**pi 是壳不是模型**，它下面每个 provider 按其权重厂商算独立性、按其计费源算额度（与 `setup.md`「聚合型订阅」一条同理）。

## ⚠️ 已停用/不适用的通道（2026-07 核实，勿再假设可用）

- **gemini / qoder / codebuddy CLI**：这些产品的独立 CLI **已下线**（用户 2026-07 核实）。曾经的命令模板（`gemini -m …` / `qoder -p …` / `codebuddy …`）**不再有效**，别再照抄。若将来它们恢复 CLI，先 `<cli> --version` 冒烟确认存在再用。**注意区分**：下线的是 Qoder 作为**被派发通道**的 CLI；Qoder 作为**宿主**（在 Qoder 里装本 skill）仍受支持，适配见仓库 `qoder/` 目录。
- **Hermes**：`hermes chat -q "…" -Q`（跨供应商路由壳）——需单独部署，多数场景不划算（多一层壳、多一层折损）。仅当用户已在某机器上部署好、且明确要用时才走。

结论：**当前实测可用的外部通道就是 `codex exec` + `kimi`（Kimi Code CLI）+ `pi`（外部 agent harness）+ coding plan（claude -p + 端点覆写）+ cc_switch 桥 + 裸 API/aichat**。上面这些是历史遗留，保留仅为说明"命令模板+模型参数"抽象可随时接新 CLI。

## coding plan（GLM / Kimi 等，载体为 claude CLI）

环境变量**按进程生效**：每次派工新开子进程并只给它设覆写变量，宿主会话登录不受影响（宿主是 Claude Code 也不冲突）。key 引用用户级环境变量，不落明文。

**安全铁律（不遵守就会串官方订阅）**：`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` 只能作为**子进程环境变量临时传入**，**绝不写进 `~/.claude/settings.json` 的 env 或任何全局配置**——一旦写全局，所有 claude 调用（含官方订阅的宿主会话）都会被重定向到第三方端点，这是最常见的冲突根因。智谱等厂商的"一键助手"常写全局配置，若用户已被它改过，盘点时提示用户清掉 settings.json 里的这两行。

只对 **Anthropic 协议端点**有效（GLM/Kimi/DeepSeek-anthropic 等）；GPT 走 codex、Gemini 走 gemini，不要硬塞进 claude CLI。覆写是否成功盖过 OAuth 因 CLI 版本而异，接入时务必冒烟测试确认走到了第三方端点。

**⚠️ 冒烟判据必须是「回答的是不是它」，不是「有没有回答」（2026-07-09 实测，血泪）**：GLM 的 Anthropic 兼容端点对**格式合法但它不提供**的模型名（如任何 Anthropic 官方 ID、`haiku`/`sonnet`/`opus` 别名）**不报错，而是静默用 `glm-4.7` 应答**；只有完全无法解析的名字才吃 400。后果：你以为在用 opus 档，其实拿到的是最便宜模型的回答，全程零报错。
- **冒烟不能只看"有回复"**——必须直接打 `{base}/v1/messages`，比对**响应体的 `model` 字段**与请求是否一致；不一致即静默降级，结论记入 `manifest.md`。现成工具：`python <本skill目录>/references/verify_model.py --provider "<cc-switch里的名字>"`（只读 cc-switch 取端点，逐档打端点比对真身；也可 `--models "a,b,c"` 测指定 ID）。**连官方文档给的 ID 也要过这一关**——实测出现过文档说可用、该账号却 400 的情况（如某些 1M 长上下文版按套餐开通）。
- CLI 的 `modelUsage` 记的是**请求值**不是服务端返回值，**不能**用来判断真身。

**已验证（claude 2.1.204 实测，2026-07-08）**：子进程覆写 `ANTHROPIC_BASE_URL`+token 时，CLI 明确以注入 auth 源**优先于 claude.ai 登录**（会打印一行提示说明这点）；实测宿主会话登录、`~/.claude/settings.json`（env 保持 `{}`）、宿主进程环境三者均不受影响；被重定向的子进程与走官方订阅的子进程可**并发共存、互不干扰**。隔离是操作系统进程级的，前提是覆写只按子进程传、不写全局配置（见上条铁律）。

```bash
# 智谱 GLM Coding Plan（zcode/ZCode 壳底层就是这个模型，直连端点即可，不碰桌面）
# 变量名是 AUTH_TOKEN 不是 API_KEY。
# 模型 ID 必须小写、精确（官方文档 docs.bigmodel.cn/cn/coding-plan，2026-07-09 核实）：
#   在售仅三个：glm-4.7 / glm-5-turbo / glm-5.2；glm-5.2[1m] = 5.2 的 1M 长上下文版（方括号小写 m 是 ID 一部分）
#   ⚠️ glm-5.1 / glm-5 已下线（调用会被静默切到 glm-5.2）；大写 [1M] 会吃 400；不认识的名字静默降级到 glm-4.7
#   下面是示例，具体以官方文档 / 你 cc-switch 里的实时配置为准
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic ANTHROPIC_AUTH_TOKEN=$GLM_CODING_KEY \
  claude -p --model glm-4.7 "[任务]"          # 粗活
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic ANTHROPIC_AUTH_TOKEN=$GLM_CODING_KEY \
  claude -p --model "glm-5.2[1m]" "[任务]"    # 硬活/长上下文（1M），常规硬活用 glm-5.2 即可

# Kimi Code（需控制台建的 API key；只有 OAuth 订阅时走上方 kimi CLI 通道）
# 端点在售模型 ID 以官方文档为准（K3 上线后是否开放此端点、ID 为何未核实——接入时必过 verify_model 真身核对）
ANTHROPIC_BASE_URL=https://api.kimi.com/coding/ ANTHROPIC_API_KEY=$KIMI_CODING_KEY \
  claude -p --model kimi-for-coding "[任务]"
```

**⚠️ 密钥不得展开进命令行**：`cmd /c "set ANTHROPIC_AUTH_TOKEN=<明文> && …"` 这类拼接会把展开后的 key 放进子进程命令行，本机进程列表可见（`Win32_Process.CommandLine`）——与六铁律的"不回显"冲突，**别用**。安全写法按优先级：① `cc_switch.py exec`（env 注入，key 永不进 argv 与上下文）；② bash 的 `VAR=$KEY cmd` 前缀形式（走环境块不进 argv，上方示例即此写法，安全）；③ PowerShell 宿主用 `$env:` 赋值再调用，用完清掉：`$env:ANTHROPIC_BASE_URL='…'; $env:ANTHROPIC_AUTH_TOKEN=$env:GLM_CODING_KEY; claude -p …; Remove-Item Env:ANTHROPIC_AUTH_TOKEN, Env:ANTHROPIC_BASE_URL`。端点 URL 以各家官方文档当前值为准。

**⚠️ API 错误可能伪装成正常回答**：`claude -p` 在 API 报错时（如 529 过载、或 400「模型 ID 不存在」）**仍可能 exit 0**，并把错误文本塞进 `result` 字段。必须用 `--output-format json` 并检查 `is_error` / `api_error_status`，否则会把 `"API Error: 400..."` 当成模型答案交付。`cc_switch.py` 现已**始终**走 json 并在**任何**模式下校验（错误时 exit 8、stdout 为空），不再只在 `--usage` 分支检查。自己写命令模板时务必同样处理——纯文本直连时也要看响应体是不是 error。

**若 key 已在 cc-switch 里**：优先用 `python <本skill目录>/references/cc_switch.py exec --provider "<名字>" --tier haiku|sonnet|opus --task "..."`——它只读取 token 注入子进程、绝不回显进上下文，档位→模型映射也直接取 cc-switch 里用户配的实时值（免手填模型 ID），并默认加只读护栏（见下）。这是 B 类用户的首选派发方式。

### 只读护栏：`claude -p` 用 `--tools`，不是 `--permission-mode`

被派发的模型**继承宿主的 cwd**。它们只出意见、不落盘（落盘由宿主 agent 负责），所以必须显式剥夺写能力，否则并发派发时几个子进程会在同一个工作区里互相覆盖。

`codex exec` 用 `-s read-only`。`claude -p` 的等效物是 **`--tools` 白名单**：

```bash
# 只读咨询/代码审查：能读能搜，不能写
echo "[任务]" | claude -p --model X --tools Read,Grep,Glob
# 纯文本任务：禁用全部工具，最省
echo "[任务]" | claude -p --model X --tools ""
```

**实测（claude 2.1.205，2026-07-09）**：

- `--permission-mode` **没有只读档**（枚举只有 `acceptEdits/auto/bypassPermissions/manual/dontAsk/plan`），别指望它。`plan` 档虽禁编辑，但会改变模型输出形态，不适合当咨询通道。
- `--tools` 作用在**工具注册层**，比权限层更硬：`--tools Read,Grep,Glob` 叠加 `--permission-mode bypassPermissions`，写依然失败（`Write exists but is not enabled in this context`）。**bypass 压不过白名单。**
- 该护栏是 CLI 本地行为，**与端点无关**：GLM 覆写端点下同样生效（已冒烟）。
- 不加任何参数时，默认 `-p` 也会拒写——但那是靠"非交互无法确认"兜底，且**被拦截时 exit 0**、把"需要你批准"当成正常答案返回（与下方 529 伪装同源）。**别依赖默认值，显式写死。**
- ⚠️ **`--tools` 是 variadic**，`claude -p --tools Read,Grep,Glob "任务"` 会把任务当成第四个工具名吞掉，然后报 `Input must be provided either through stdin or as a prompt argument`——看着像"没给 prompt"，实为参数被吞。**prompt 一律走 stdin。**

`cc_switch.py` 已默认 `--tools Read,Grep,Glob` 并把 task 经 stdin 送入；纯文本任务传 `--tools ""`。

**`--tools` 不只是安全护栏，也是最大的一笔省额度（claude 2.1.232 + haiku 实测，2026-08-14）**：

| 配置 | 固定 input | 相对默认 |
|---|---|---|
| `--tools ""` | **12,239** | **−61%** |
| `--tools Read,Grep,Glob` | 14,238 | −54% |
| 不传 `--tools` | 31,275 | 基准 |

一直被引用的"`claude -p` ≈30k"就是**最后那一行**。手写命令模板漏掉 `--tools` = 白付 2.5 倍固定足迹，且失去只读护栏——**两件事同一个参数管，没有理由不写**。砍不掉的是 ~12k 系统提示底座（要更低只能走裸 API，地板 11）。

**别抄的负结果**：`--exclude-dynamic-system-prompt-sections` 只省 1.3%（12,229→12,071），它是为跨用户共享缓存设计的，不是单机省 token 手段。

**`--fallback-model <a,b>`（claude 2.1.232 有）**：主模型过载/不可用时自动按序换模型。可作为本 skill「通道熔断」的 CLI 层兜底——但**它换的是模型不是厂商**，同厂商 fallback 不构成交叉验证的独立源；熔断后要不要换厂商仍由编排者按 SKILL.md 规则判。

**合规注**：多数 coding plan 条款限定用于 coding agent（Claude Code 等）。本通道载体就是 claude CLI，属限定范围内的用法；**不要**用 aichat 直连 coding plan 端点（可能违反条款，网关也常拒非 agent 流量）——aichat 只兜按量 API。

**⚠️ 千问 Token Plan（`sk-sp-` 开头的 key）不作为派发通道**（2026-08-14 核实）：

- 可观察的事实两条：①千问官方 skill 仓库（`QianWen-AI/qianwen-ai`）明文写 `sk-sp-` keys are *"strictly forbidden in automation scripts, application backends, batch jobs, API testing tools, and workflow platforms"*，并点名禁止覆写 `QWEN_BASE_URL` 重定向该 key；②其客户端确实硬失败——`skills/*/scripts/qianwen_lib.py` 检测到 `key.startswith("sk-sp-")` 直接 `sys.exit(1)`，提示"requires a standard API key (sk-...)"。
- **但平台公开文档（`platform.qianwenai.com/docs/token-plan/overview`）里查不到对应条款**，那些措辞目前只有厂商 skill 单一来源。代码里的实际提示也只说"本脚本要标准 key"，没提封号。
- **结论：要接千问就用标准 `sk-` 按量 key 走裸 API/aichat**。Token Plan 额度留给交互式宿主自己用，别接进 ai-cross 的批量派发——风险不明确时不赌。
- 顺带记一条**边界案例**：千问 Token Plan 的模型清单里含第三方权重（`glm-5.2`/`glm-5.1`、`deepseek-v4-*`、`kimi-k2.*`、`MiniMax-M2.5`）。这是**一个计费源内含多厂商权重**——按本 skill 的定义，权重独立性成立（可做交叉验证）、计费独立性不成立（熔断时一起没）。真接入这类"聚合订阅"时，manifest 的厂商列按**权重厂商**填，额度归属列填**聚合平台**，两者不可合并成一列。

## 纯文本任务：裸 API 直调（最省，地板 ~11 token）

纯文本任务（分类/摘要/翻译/抽取/自包含问答，**不需要工具**）**不该走 harness**，主 agent 直接打端点即可——无系统提示、无工具定义，input 地板实测 **11 token**（对比 `claude -p --tools ""` 12k、不收窄工具时 31k，见上节实测表）。下面示例是 **OpenAI 兼容格式**（`/v1/chat/completions`）；Anthropic 协议端点走 `/v1/messages`，请求体格式不同（`max_tokens` 必填、消息结构不同），别混用同一模板。

```bash
# OpenAI 兼容端点（DeepSeek/硅基流动/OpenRouter 等）
curl -s https://<host>/v1/chat/completions \
  -H "authorization: Bearer $API_KEY" -H "content-type: application/json" \
  -d '{"model":"<model>","max_tokens":512,
       "messages":[{"role":"user","content":"[任务]"}],
       "enable_thinking":false}'
# 只取 .choices[0].message.content。
# ⛔ content 为空时【绝不】回退去读 .reasoning_content —— 那是没写完的思考草稿，不是答案。
#    content 空 + finish_reason=="length" ⇒ 被截断，应加大 max_tokens 重试，而不是从草稿里抠答案。
```

- **⚠️ `-H "… Bearer $API_KEY"` 展开后进 curl 的命令行**，本机进程列表可见。单人本机通常可接受，但多用户/受审计环境用 config-from-stdin 把 header 挪出 argv：

  ```bash
  curl -s https://<host>/v1/chat/completions -K - -d @payload.json <<EOF
  header = "authorization: Bearer $API_KEY"
  header = "content-type: application/json"
  EOF
  ```

- **`enable_thinking:false`（或各家等价参数）** —— 纯文本任务必加。实测（5 模型均证实该参数真实生效）：推理模型开着思考纯烧 output，Qwen 抽取任务 1159→18 token（**64×**），**正确率无变化**（预算给够时两边都对）。省的是 token，不是错误率。
- **开着思考时 max_tokens 必须给到关思考时的 50× 以上。** 推理 token 与答案 token **共享同一个输出预算**。同一个 Qwen 抽取任务：关思考 18 token 够用，开思考要 ~1200；给 512 会把思考掐断在半路，`content` 直接为空。`completion == max_tokens` 就是撞顶的指纹。**"≥512 就够"是错的**（本项目曾据此得出错误结论）。
- **批量合并**：50 条要分类的，拼成一次调用，别发 50 次——固定开销才摊得开。
- key 用用户级环境变量引用（`$API_KEY`），不落明文；**这是纯按量 API，不是 coding plan**（后者不能这么直连）。本节所有带凭据出网的命令都受 `security.md` 的密钥六铁律约束（绝不回显、绝不进模型上下文、绝不落盘），接入前先读那一页。

## aichat（按量 API 的 CLI 封装，不想写 HTTP 时用）

`aichat` 是裸 API 的薄封装，适合不想手写 curl 的场景；它的系统提示极短，成本接近裸调用。功能同上，命令更短：

```bash
aichat -m <provider>:<model> "[任务]"
cat file.txt | aichat -m <provider>:<model> "总结要点"   # 长文本走 stdin
```

关思考的参数以 aichat 的 provider 配置为准（`enable_thinking` 等写进 config.yaml 的 `patch` 段）。

多数按量模型无推理强度旋钮；个别推理模型有专用参数，以 provider 文档为准。

## 复用与维护

**一次配好，永久复用**：API key（用户级环境变量 `setx`）、aichat config.yaml、manifest.md 三者都持久化，跨会话跨重启有效。之后每次派工自动读取，用户无需重输。每次派工"重新设置"的只有子进程那次性环境变量——自动、隐形，且正是隔离安全的来源，不算重复配置。key 过期/轮换时重跑一次 `setx` 即可（当前 shell 需重启才见新值，新开的 shell 直接生效）。

**模型 ID 漂移**（模型在迭代，如 glm-4.6→GLM-4.7→GLM-5.2、gpt-5.4→5.5）：
- **权威来源分两类**：有本地事实源的（codex `models_cache.json`、kimi `config.toml`、cc-switch 映射、aichat `--list-models`）**运行时读，本文件只记"去哪读"**；没有事实源的（如 coding plan 端点在售 ID）才把值记在本文件。本文件模板里出现的具体 ID 都是**示例快照**，以事实源/官方文档当前值为准。漂了改这里即可，skill 其余逻辑不动。
- 派发命中"unknown model / 模型不存在"类错误：先去掉 `-m`/`--model` 用该 CLI **默认模型**重试（默认通常跟随当前版），再提示用户更新本文件对应行。
- 支持枚举/有本地缓存的以其为准（`aichat --list-models`、codex 的 `~/.codex/models_cache.json`、kimi 的 `config.toml`）；都没有的（claude/gemini）以各家官方文档当前型号为准。

**CLI 参数漂移**（命令行参数被改名/移除，如本文件曾误用已下线的 `--full-auto`）：
- 命中 `unrecognized arguments` / `unknown option` / `error: unexpected argument` 类错误时：
  1. 跑 `<cli> --help`（或 `<cli> <子命令> --help`）看当前可用参数；
  2. 去掉所有非必要参数，用**最小可用命令**重试（只保留模型、沙箱/只读、必要的跳过检查）；
  3. 成功后提示用户更新本文件对应模板行，并在 manifest 备注该 CLI 版本。
- 任务文本含引号/花括号/换行时，**用文件传参**（如 `cc_switch.py --task-file`）或 stdin，别在 shell 里拼——PowerShell/cmd 会把 `{}` 和转义引号拆碎（实测踩过）。
- **⚠️ 多行 prompt 绝不能走 argv（Windows 实测）**：`codex exec ... "<多行文本>"` 会在**第一个换行处截断**，模型只收到第一行。它会（完全正确地）回答"你没把规格贴出来"，而你会误以为它能力不行。**正确做法：`codex exec ... -` 并把 prompt 从 stdin 送入**（`cat spec.txt | codex exec ... -`，或 Python `subprocess.run(cmd, input=prompt)`）。
  - 这个 bug 曾让一整套高难度基准误判为"codex 全线 0%"，而单行 prompt 的简单基准却全 100%——差点被错误归因为"目标 CLI 的技能污染"。**判定模型失败前，先确认它到底收到了什么。**

**CLI 二进制版本**：记录版本号、**不自动升级**（升级可能带破坏性变更）；仅冒烟失败且疑似过旧时才向用户建议升级命令。

**本地有事实源的值不手抄**：kimi 的 `~/.kimi-code/config.toml [models]` 段、cc-switch 的档位→模型映射（`cc_switch.py list`）、aichat 的 `--list-models`、`~/.claude/settings.json` / `~/.codex/config.toml` 的用户偏好——这些派发前**运行时读**，本文件与 manifest 只记"去哪读"和实测结论，不当值的权威来源。值不会过期，因为根本不存。

**⛔ 不得静默降级用旧值**（原则落地，2026-08-14 补）：manifest 每行带**来源**列——`读:<命令/路径>` / `文档(日期)` / `申报(日期)`。标了 `读:` 的行，派发前按该来源实读；读失败（CLI 没装、配置被删、命令报错）时**可以**用 manifest 的记录值顶上，但必须在路由决策行或汇总里当场说明「事实源读取失败，用的是 <日期> 的记录值，未实读」。理由：模型 ID 漂移本身不致命，**漂移变成静默故障才致命**——记录值一旦被无声当成实读值，静默降级（GLM 那种）就查不出来了。

**过期检测（TTL + 冒烟）**：manifest 每行的冒烟日期就是新鲜度。派发前扫一眼：目标通道条目**超过 30 天**未验证 → 先跑该档最便宜冒烟；第三方 Anthropic 兼容端点还必须过 `verify_model.py` 真身核对（防静默降级），通过后刷新 manifest 日期再派。失败才进入上面的漂移处理流程。原则：**自动化的是"发现过期"，改配置必须用户确认**——端点会谎报（静默降级实测在案），唯一可信的更新依据是冒烟，自动改写配置只会把谎报固化进配置。

**免费续期与漂移预警（usage_probe）**：`python <本skill目录>/references/usage_probe.py --days 30` 聚合本机各 CLI 用量日志（只出元数据）。两个用法：①**官方 CLI** 条目若在近 7 天日志里成功出现过，可视作新鲜、免冒烟续期（claude 日志的 model 是响应侧值；第三方端点仍必须 verify_model）；②日志里出现了 manifest/本文件**没有**的模型 ID（如 CLI 升级换了默认模型），就是漂移信号——冒烟确认后走"更新模型清单"流程。实测首跑即抓到 codex 主用模型已从 gpt-5.5 代漂移到 gpt-5.6 代（2026-07-17）。

**用户说「更新模型 / 升级清单」**：重跑盘点流程（`setup.md`）+ 逐 CLI 核对当前模型 ID（能枚举的枚举、不能的查文档或问用户）+ 刷新本文件与 manifest.md 的 ID 和日期。
