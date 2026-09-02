# 派发设计依据：模型能力、并行边界、任务分解

## 这个 skill 填的是哪块空地（与 harness 内置功能的边界）

分两点，都经实测/核实：

**① 难度→成本/换模型路由：两个 harness 都不做。** Claude Code 主循环跑 `/model` 选定的模型；Codex `-m` 锁一个型号（2026-07 实测 `codex features list` 里 `remote_models` 已 removed、无 router）。harness 的"内部逻辑"只是**管道级家务**（CC 用 haiku 生成标题/摘要、自动 compaction），**不把用户任务按难度降档**。→ 这块是空地，本 skill 的"三步路由/分层保额度"补它。

**② 多 agent 编排：Claude Code 有内置的（ultracode / workflows），但只限同厂商。**
- Claude Code 的 `/effort` 滑到 **ultracode（= xhigh + workflows）** 会自动把任务拆成多 agent workflow（fan-out subagent、对抗验证、综合）。**这与本 skill 的"并行/全力模式"功能重叠**——别声称"编排是空地"。
- **但 ultracode 的 agent 全是 Claude**（workflow 的 subagent 都是 Claude 模型），失败模式相关。**它做不到跨厂商交叉验证**——一个 Claude 抓不出另一个 Claude 的系统性盲区。

**所以本 skill 唯一真正独有、且最硬的功能是「跨厂商交叉验证」**：用 codex/GLM/numpy 这些**非 Claude 的独立视角**抓 Claude（或任一单一模型）抓不出的错（实测战果：StepFun 算术错、GLM 规格偏差、"三方共识掩盖坏推导"）。ultracode 给"更多个 Claude 一起干"，本 skill 给"不同厂商互相挑错"——**这是本质区别，也是分享时该主打的点。**

（内部 subagent 通道复用的是 Claude Code 的 subagent 机制——那是"机制"；本 skill 提供的是"用哪个 subagent/哪个厂商干哪种活 + 怎么互查"的"决策"。）

## 载体与"要不要 Claude"（架构确认）

- **宿主**：任意能跑 shell + 认 SKILL.md 的 agent，**不必是 Claude Code**。host-agnostic。
- **claude CLI 二进制**：接 Anthropic 兼容端点 provider（GLM/StepFun/讯飞/Kimi）的便利载体。**免费安装，且配第三方端点不需要 Claude 订阅**——env 覆写替代认证。
- **完全不用 Claude 的用户也行**：GLM/StepFun 等多同时提供 OpenAI 兼容端点，可改走 aichat；codex/gemini provider 走各自 CLI。故**无硬性 Claude 依赖**，claude CLI 只是 Anthropic 端点的一个载体选项。
- 结论：全流程唯一"较硬"的前提是——**接哪个模型，就要有对应的载体**（Anthropic 端点→claude CLI 或 aichat；GPT→codex；Gemini→gemini）。载体缺失时该通道降级，不阻塞其余。

## 模型 ID 获取（对应"抓取所有模型 id"）

CLI 基本**不支持枚举**：claude/codex/gemini 均无 list-models（`codex --help` 实测无该子命令）；hermes/openclaw 只是把用户配过的后端再暴露一遍，不是发现新模型。所以别追求"问 CLI 要清单"。可靠来源三条：

1. **cc-switch 配置**：含端点 + 档位→模型映射，最全，已证实（`cc_switch.py list`）。
2. **provider 的 `/models` 端点**：有 key+base 时 `GET {base}/v1/models`（OpenAI/Anthropic 兼容通用）。`aichat --list-models` 就是这么做的。
3. **官方订阅 CLI 的静态档位表**：就 3-4 档（claude=haiku/sonnet/opus；codex=mini/标准/深度），无需抓取。

## 模型能力/边界（不靠猜）

- **能力档位继承 cc-switch/manifest 的映射**：用户把 haiku→便宜模型、opus→强模型这样映射，就是他对能力的判断。路由按**档位**（低/中/高）工作，不需我们判定某模型的绝对能力。
- 无映射的裸模型（如 aichat 里）：注册时让用户打一个档位标签，或按模型家族给默认；不做玄学自动探测。
- 边界信号：模型 ID 里的 `[1M]`/`[1m]` 表长上下文；上下文窗口、速率限制记录已知值（provider 文档）。路由主要用"档位 + 粗略上下文规模"。

## 多模型抉择（例：claude 4 档 + codex 4 档 + cc-switch 5 个 = 13 个模型怎么选）

**永远不做 13 选 1。** 盘点时把所有模型归一化成一张**厂商 × 档位矩阵**（行=厂商/源，列=低/中/高档；档位顺序官方 CLI 来自静态表、第三方来自用户在 cc-switch 里的 haiku/sonnet/opus 映射——**绝不按模型编号猜大小**）：

|  | 低 | 中 | 高 |
|---|---|---|---|
| Claude | haiku | sonnet | opus |
| Codex | gpt-mini | gpt-标准 | gpt-深度 |
| GLM | glm-5-turbo | glm-5.2 | glm-5.2[1m] |
| … | | | |

选择只剩三步，每步都小：
1. **任务 → 档位**：查路由表（列）。
2. **强度 → 厂商数**：标准=1 家；双保险/交叉=2 家不同厂商；全力=尽量全（行）。
3. **格子内取具体模型**：矩阵交叉点直接给出模型 ID（实时来自映射）。同档多家可选时：批量粗活选**最便宜的源**，关键审查选**与实现方不同厂商**的高档。

## 并行 agent 数量边界（取各上限的最小值）

```
并发数 = min( 可用不同模型数, 单源速率/额度余量, 本机并发上限, 任务类型上限 )
```

- **单源速率余量**：不确定就保守 2-3 并发/源，避免触发 plan 限流。
- **本机上限**：子进程 fan-out 参考 `min(16, CPU核数-2)`（与内部 Workflow 引擎同款经验值）。
- **任务类型上限**：
  - 交叉验证/评审面板：**3 个**（奇数便于多数表决，>3~5 收益递减）——LLM-as-judge、self-consistency、对抗验证的通行做法。
  - 广度 fan-out（分头调研/多路实现）：**~5**，再多靠"全力"模式显式放开。
- "全力"模式抬高任务类型上限，但仍受**单源速率 + 本机上限**硬约束——不是无脑开满。

## 任务分解原则（借鉴成熟方案）

- 按"**错误代价 × 任务类型**"路由（见 SKILL.md 路由表）。
- 只对**相互独立、无共享状态**的子任务并行（参考 superpowers:dispatching-parallel-agents）。
- 子任务提示**自包含**：被派 agent 看不到主会话历史，须给全背景+目标+边界+输出格式。
- **闭环验证**：产出必须验证后才算完；coding review→修正→再 review ≤3 轮，仍分歧上报。
- **验证要视角多样而非重复**：每个验证者给不同透镜（正确性/安全/可复现），比 N 个相同复核更能抓不同失败模式（对抗验证模式）。

## 自测基准（2026-07-08，5 臂 × 4 任务 × 3 轮 = 60 次，可靠仪器 + 程序化 verifier）

臂：`codex-low`(gpt-5.4-mini/low)、`codex-high`(gpt-5.5/xhigh)、`glm-low`(glm-5-turbo)、`step-low`(step-router-v1)、`step-mid`(step-3.5-flash)。
每 trial 注入唯一 nonce；verifier 经 9 项正/负样本自检（无假阴性/假阳性）；代码类任务**剥掉模型自带的自测块、跑我们自己的用例**。

| 任务 | 臂 | 正确率 | input 中位 | out 中位 | 秒 | 工具轮 |
|---|---|---|---|---|---|---|
| null | codex-low | 100% | 19,652 | 19 | 62 | 0 |
| null | codex-high | 100% | 21,942 | 80 | 63 | 0 |
| null | glm-low | 100% | 29,176 | 35 | **5** | — |
| null | step-low | 100% | 30,049 | 49 | **7** | — |
| **recon-count** | codex-low | 100% | **81,824** | 524 | 90 | **3** |
| **recon-count** | codex-high | 100% | **44,826** | 757 | 75 | **1** |
| **recon-count** | glm-low | 100% | 58,585 | 125 | 8 | — |
| **recon-count** | **step-low** | **33%** | 61,474 | 686 | 14 | — |
| **recon-count** | **step-mid** | **33%** | 60,878 | 917 | 13 | — |
| impl-roman | 全部 5 臂 | **100%** | 19.7k–30.2k | 274–778 | 7–74 | 0 |
| impl-chunk | 全部 5 臂 | **100%** | 19.7k–30.2k | 62–295 | 5–70 | 0 |

### 三条站得住的结论

1. **厂商差异 >> 档位差异（本任务集内）**：StepFun **两个档位都只有 33%**（计数系统性偏大：报 17/18，实为 16），而 codex 与 GLM 的各档位全 100%。与另一次统计任务中 StepFun 方法标注错误 + 两处算术错误**独立互证** —— 同一厂商在精确计数/算术上系统性不可靠。**路由时"哪家"比"哪档"更要紧。**
2. **thrash 可测且真实**：同样答对 recon-count，codex-low 用 **3 轮工具调用 / 81,824 input**，codex-high 用 **1 轮 / 44,826**。便宜档要多花近 **1.8 倍上下文**才到达同一答案。（这是早先被撤回的"70%"结论的正确版本——用稳定的 input 总量测，不用会跳的计费数。）
3. **延迟按厂商差一个数量级**：codex 62–90s，GLM/StepFun 5–14s。延迟敏感场景是硬约束。

### ⛔ 本数据【不能】支持的结论

- **不能**说"便宜档在中难度任务上不行"。两个实现任务上**全部 5 臂都是 100%**。早先"mini 失败"是**它自带的自测与自身实现矛盾**（交付物缺陷，n=1），与"实现正确性"是两个不同指标，当时被混为一谈。
- 因此**本任务集难度不足以区分档位**，不能用来验证路由表的"中难度→中档"边界。需要更难的任务。

### 仪器缺口（诚实标注）

`run_ccsw` 的 `tool_calls` 恒为 0（从未解析 GLM/StepFun 的工具调用事件）。故"是否主动用工具核实决定了计数准确性"这一假设，**用当前数据无法检验**——glm-low 显示 tools=0 却 100% 正确，但那个 0 是假的。

### ⚠️ 固定开销与缓存：外派的隐藏成本（2026-07-08 实测，结构化用量）

一个"只回复两个字"的空任务，各通道的 input 上下文总量（系统提示 + 工具定义）与计费部分：

| 通道 | input 总量（稳定） | 冷调用 fresh | 热调用 fresh |
|---|---|---|---|
| `codex exec`（mini/low） | 19,652 | 16,196 | **324** |
| `claude -p`（官方 haiku） | 30,230 | — | 9,164（cache_read 21,089） |
| `claude -p` → GLM 端点 | 29,177 | 28,473 | **3,064** |
| `claude -p` → StepFun 端点 | 30,052 | 30,048 | **100**（cache_read 29,952） |

### 决定性对照：固定开销是「壳」的，不是「模型」的

同一个 **haiku 模型**、同一个"只回复两个字"的空任务：

| 路径 | token | 差距 |
|---|---|---|
| **内部 subagent**（Claude Code 内的 scout） | **3,963** | — |
| **外部 `claude -p --model haiku`** | **30,230** | **7.6×** |

模型相同、任务相同，唯一变量是**是否新起一个 harness**（系统提示 + 工具定义 + 技能索引）。

**裸 API 地板（实测，硅基流动 Qwen3.6-35B-A3B，2026-07-09）**：同一句"你好"，**无系统提示 = 11 prompt tokens**；+ 短系统提示 = 20；+ ~500 字系统提示 = 241。对比内部 subagent 3,963、`claude -p` ~30,000。**harness 税是裸调用的 360×–2700×**，其中系统提示把 11 抬到几百，工具定义 + 技能索引再抬到 ~30k。这坐实了 FrugalGPT/RouteLLM 的省钱基线：它们 benchmark 的是**无 harness 的裸 API 单轮问答**，地板 ~11 token —— 我们经 harness 永远够不到，能逼近它的只有裸 API / aichat 直调纯文本任务。

**推论（改变路由的第一选择）**：
- 宿主有内部通道时（Claude Code 的 scout/worker/heavy），**分层派发几乎免费**——`workflow` / ultracode 式扇出在经济上完全成立。
- **跨 CLI 外派才要算账。** 外派的正当理由只有一个：**换厂商**（交叉验证、独立第二意见、失败模式独立）。为了"省钱"而把小任务外派给便宜模型，多半是净亏损。

两条推论：

1. **每次跨 CLI 外派自带 ~12k–30k input 的固定上下文足迹**（系统提示 + 工具定义），任务本身可能只占几十 token。**该值随工具白名单浮动 2.5 倍**——`claude -p` 实测 `--tools ""` 12,239 / `--tools Read,Grep,Glob` 14,238 / 不传 31,275（claude 2.1.232，2026-08-14，见 `evidence.md`）。本节下方 2026-07-09 的绝对值是**不收窄工具**时测的，比例结论（harness 税 360×–2700×、内部 vs 外部 7.6×）不受影响。
2. **计费成本是双峰的**：冷调用付全额（~16k–30k fresh），热调用几乎全走缓存（~0.1k–3k fresh）。**所测四个端点（含两个第三方）在热状态下都重度缓存。**
   - **实践含义**：**成串的同类派发很便宜（第一次之后几乎白送）；零散的一次性派发每次都付全额**（缓存 TTL 通常约 5 分钟）。所以"批量合并小任务"的收益主要来自**把冷调用摊薄成一次**，而非省 token 本身。

这一点是单轮 cascade（FrugalGPT 等）未覆盖的：它们假设"调便宜模型 = 便宜"，但 agentic 调用有固定上下文足迹，且**计费随缓存状态双峰跳变**，是成本模型的关键调节变量。

### 🔁 方法学教训：我们在这里连续犯了三次同类错误

1. 据一次冷调用断言"GLM 端点零缓存、全额付费" → **错**，热调用 fresh 仅 3,064。
2. 修正后又断言"StepFun 几乎不缓存（cache_read 仅 384）" → **仍错**，那也是冷/半热态；热调用 cache_read 达 29,952。
3. 更早据 `tokens used` 断言"便宜档多烧 70% token" → **错**，那个数字随缓存在 188~19,538 间跳。

**共同根因：拿单次测量当稳态，且没意识到缓存状态是隐藏的主导变量。**

固化为规则：
- **任何 token/成本测量必须区分冷/热，并报告 `cache_read`；单次测量不得用于下结论。**
- 做基准时每 trial 注入唯一 nonce 只能破**任务文本**的缓存，**系统提示前缀仍会命中缓存** —— 所以 trial 1 与 trial 2/3 天然不同质，必须分别记录。

### ⛔ 已撤回的结论：「便宜档反而多烧 70% token」

早先基于 codex 打印的 `tokens used` 得出"mini 用 36,148 vs gpt-5.5 用 21,274"。**该结论已撤回**——`tokens used` 是**未命中缓存的计费部分**，随 prompt 缓存状态在 188 ~ 19,538 之间乱跳（同一任务同一档，实测 43 倍波动）。用它做跨档比较会得出完全错误的结论。

**可靠仪器**：`codex exec --json` → `turn.completed.usage`（含 `input_tokens` / `cached_input_tokens`）；`claude -p --output-format json` → `usage`（含 `cache_read_input_tokens`）。**做基准前先证明尺子是准的。**

### 档位边界的结论（正确性维度，不依赖 token 测量）

**诚实标注**：n=3/格，方差仍大，不是统计意义上的严格基准；跨厂商 token 数可比、**成本不可比**（单价差数量级）；订阅制账号无法换算美元。经典题目（罗马数字等）可能存在训练集污染，需自造任务复核。**不支持任何"省 X%"的精确结论。**

## ⚠️ 外派继承目标 CLI 的人格（2026-07-08 实测，影响所有跨 CLI 派发）

`codex exec` / `claude -p` 并非"裸模型"，它们启动时会加载**用户自己的全局指令与全部 skills**。本机实测：codex 加载 **44 个 skill**（含整套 superpowers：`test-driven-development`、`verification-before-completion`、`systematic-debugging`、`using-superpowers`）+ 一份 `~/.codex/AGENTS.md`。

**因果链已坐实**：

| 现象 | 来源 |
|---|---|
| 面对一道纯计算题不给答案，改列"我可以帮你：1…2…3…" | `AGENTS.md`："If multiple interpretations would lead to meaningfully different changes, **ask or present the options**" |
| 明确要求"不要执行任何命令"，仍跑 6–16 轮工具调用 | superpowers 的 TDD / verification-before-completion / using-superpowers |
| 最终消息是验证总结，代码留在中间消息或 shell 命令里 | 同上 |

**三条推论（已写入 SKILL.md 稳健性规则）**：

1. **你的任务指令与目标 CLI 的全局指令竞争，且常常输。** 外派得到的不是"模型的能力"，而是"被配置过的 agent 的行为"。
2. 固定足迹里含一份**技能索引**，但它是**限额**的（codex 约 2% 上下文预算）。实测移除 14 个 superpowers 子技能后，模型可见 prompt 从 42,802 → 43,052 字符（**不减反增**：剩余技能的描述被补全）。**故"少装 skill 能省固定开销"是错的**，已撤回该说法。固定开销主要来自系统提示与工具定义本身。
3. **绝不能依赖"只输出 X"的格式约束。** 派发时给明确分隔符并取最后一次出现，或容忍散文包裹、宽松解析。**判定失败前先排除解析问题。**

**对基准测量的影响**：跨 CLI 的"模型对比"实际是"agent 对比"。做严格模型对比必须控制环境（干净的 `CODEX_HOME` / 停用 skills），否则结论无效。本项目的高难度基准 codex 臂即因此全部作废——详见 `bench/RESULTS-HARD-INVALID.md`。

## Advisor 模式参照（Anthropic，2026）

**机制**：执行者（Haiku/Sonnet）全程跑任务，遇到不确定的**决策点**时调用顾问（Opus/Fable 5），顾问返回计划/纠正/叫停，执行者继续。原生实现是 Messages API 的工具：

```python
tools=[{"type": "advisor_20260301", "model": "claude-opus-4-6", "max_uses": 3}]
```

单个 `/v1/messages` 请求内完成模型切换，**不重发上下文**；advisor 与 executor 的 token 分别计费。

**基准数据**：

| 基准 | 配置 | 效果 | 成本 |
|---|---|---|---|
| SWE-bench Multilingual | Sonnet + Opus 顾问 | 74.8% vs 单独 72.1%（+2.7pp） | **−11.9%** |
| BrowseComp | Haiku + Opus 顾问 | 41.2% vs 单独 19.7% | 比 Sonnet 低 85% |

**成本为何反降**：更好的规划减少了执行者的试错轮数，省下的迭代费用超过顾问的开销。这与本项目观察到的 **thrash** 现象是同一枚硬币的两面。

**对我们的启示（已写入 SKILL.md 升级阶梯）**：
- 在**决策点咨询** > **事后审查**。事后审查要为坏实现付全款 + 审查费 + 修正费。实测：一次 tuple 规格分歧引发 5 次调用（实现→审查→修→引入新错→再修→复审）。
- 顾问只要方案/纠正/叫停，不重做任务，输出仅几百 token。Fable 5 的 $10/$50 定价正是为这个角色设计的（高单价 × 小体量）。

**⚠️ CLI 架构下的适配警告（本项目独有的发现）**：
原生 advisor 在**同一请求内**切换模型，不重发上下文。而我们经**独立 CLI 进程**咨询，每次要付 **20k–30k 固定上下文足迹**（见上方固定开销实测）。**"每次咨询几百 token"的经济学在 CLI 模拟下不成立。**

要让顾问模式在 CLI 下仍然划算：
1. **咨询次数受限**（对齐 `max_uses=3`）；
2. **一次把问题批量问完**，别多次往返；
3. 尽量在**同一热缓存窗口内**咨询（热调用 fresh 可降至 0.1k–3k）。

**待验证**：Fable 5 的 SWE-Bench Pro 80.3% 有独立评测方提出质疑，本文档不将其作为既定事实引用。

## Loop Engineering 六组件 / Matt Pocock 五步链路 参照

六组件（Automations / Skills / MCP / Subagents / Worktrees / State-Memory）里，与本 skill 直接相关的是后三个：

- **Subagents 的三种模式**：串行流水线（pipeline）、并行扇出（fan-out/fan-in）、主从委派（delegation）。本 skill 用的是「扇出 + 审查回路」；委派深度不超过一层（层级深了信息丢失）。
- **Worktrees = 工作隔离**：并行 agent 写同一文件会打架。非编程场景不需要真 git worktree，**路径隔离即可**（各写各的输出文件，编排者合并）。
- **State/Memory ≠ 记忆力，而是任务可恢复**。本 skill 据此新增 `.dispatch/STATE.md`：留痕是**事后可审计**，STATE 是**事中可恢复**，两者不可互替。

**已吸收的两条（都对上了我们踩过的坑）**：

1. **「子 Agent 不能 clarify，只有主 Agent 能」** —— 实测中 `codex exec` 返回过"请补充算法步骤、位宽、字节序…"这类**反问**，而 runner 把它当成失败的答案。生产派发里必须**检测反问并处理**（先查输入是否送达，再补齐重派，否则升级给用户），绝不落库。
2. **「子 Agent 的『完成』必须被验证，不是自述 DONE」** —— 与本项目独立得出的「共识只对结论生效、可验证量必须编排者亲验」同源。文档还指出 completion-promise（约定 "DONE" 字符串）不可靠，因为模型会**过早乐观**。

**设计哲学的坐标**（文档给的两极）：

| | Superpowers | Matt Pocock |
|---|---|---|
| 对模型的假设 | 会偷懒，红旗表逐条堵退路，hook 强制注入 | 大概率做对，只给最小锚点，多数 skill 手动 `/` 触发 |
| 适合 | 高风险/不可逆、丢给 agent 自己跑几小时 | 日常/可迭代、每个决策过人手 |

**ai-cross 的定位是混合**：主体是「查表即派」的最小干预（避免让主模型反复斟酌，判断本身在花钱），但在**证据逼出来的地方用硬约束**——密钥六铁律、通道熔断、共识不可信、修正后必须重跑验证。**约束只加在实测吃过亏的地方，不做预防性说教。**

## OpenSquilla 参照（2026-07，5.5k star，同题项目）

[opensquilla](https://github.com/opensquilla/opensquilla)："令牌高效微核 agent"，与本 skill 同题——按任务复杂度（C0-C3 四级）路由到**最便宜的能力足够模型**，其基准显示分层调度相对单一 Opus 方案成本 $6.23→$0.688，验证了分层派发的核心论点。已借鉴：cheapest-capable 升级阶梯、通道熔断（重复失败自动停）、主备切换、输出有界、成本留痕、输出防注入（见 SKILL.md 稳健性规则）。**不采用**：它的本地 ML 分类器（LightGBM+ONNX，要装模型资产，违背零门槛）——我们的路由表+主 agent 兜底就是 skill 原生的免安装等价物；它的网关/UI/频道形态（又一个壳，与 host-agnostic skill 定位冲突）。

成熟框架参照：
- **MoA（Mixture-of-Agents）**：分层聚合，每层 3-6 个提议者，后层综合前层——多模型协作的代表范式。
- **Self-Consistency**：单模型多采样 + 多数表决，适合便宜模型做可验证任务。
- **LLM-as-a-Judge**：3 评审面板 + 多数/均值，是交叉验证的标准配置。
- 这些共同指向：**独立性 + 奇数面板 + 多数表决 + 视角多样**，是"科学分配"的核心，而非盲目堆并发。
