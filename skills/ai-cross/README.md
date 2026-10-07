# ai-cross

多模型分工与跨厂商交叉验证的 AI agent skill。粗活派给低成本模型，关键产出交给另一家厂商的模型独立复查。装在 Claude Code、Codex 等工具里，用日常说法调用：

| 你说 | 它做什么 |
|---|---|
| 让别家审一下这段代码 / 交叉验证一下 | 选一家与当前模型不同厂商的模型审查。先说明派给谁、发什么，你同意后才发送；结果回来后跑代码核对，再汇总 |
| 把这个活派给 GLM 做 | 交给指定模型。返回的代码由当前模型写入项目并跑测试 |
| 这次让 Gemini 审 | 仅本次更换 |
| 以后审查都先用 Gemini | 修改默认审查者 |
| 重新盘点 | 装了新工具或换了订阅后重新登记 |

首次使用时会只读检测本机可用的模型（不登录、不读密钥），每台电脑登记一次，各工具共用。

审查结果不做多数表决：能跑代码核对的由当前模型核对，核对不了的分歧连同双方理由交给你。每次派发的任务原文和回答都会存档。

> 中文为主，English summary below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

## 适用场景

- 重要代码改动、科研分析或长文档完成后，让另一家厂商的模型独立复查。
- 有多个模型可用，想按任务分配：粗活用低成本档，强模型留给架构与审查。
- 需要追溯某个结论来自哪个模型、哪一档、什么输入。

## 环境要求

- 宿主：能跑 shell、能加载 `SKILL.md` 的 agent。内部 subagent 分层（scout/worker/heavy/advisor）仅 Claude Code 支持，其他宿主只走外部通道。
- 交叉验证需要至少两家厂商的模型。只有一家时仍可分层派发，同厂商复查记为"复核"。
- 凭据：各 CLI 的 OAuth 登录、用户级环境变量中的 API key，或已配置的 [cc-switch](https://github.com/farion1231/cc-switch)。只用 Claude Code 内部 subagent 时无需额外凭据。

## 工作原理

**盘点**：`references/inventory.py` 只读检测本机的 agent CLI、模型清单和 cc-switch 供应商（不登录、不调用模型、不输出密钥），用户确认后做冒烟测试。模型 ID 与检测结果不符的拒收。结果存于 `~/.aicross/skill/manifest.json`（设了 `AICROSS_HOME` 则在其下），各宿主共用，skill 更新不影响。

**默认人选**：未指定时由脚本选择。审查者避开被审产出的厂商，订阅内模型优先于按次计费；宿主底层模型不确定时，改由两家外部厂商互审。用户说"以后审查都先用某家"即修改默认值。

**路由与分层**：按 `references/rules.md` 的路由表，由任务类型决定档位和推理强度；哪个模型算低、中、高档由用户在 manifest 中标注。每次派发前先输出一行路由决策（通道/模型、档位、thinking、理由）。需要精确数值时要求模型写代码执行，再由编排者独立核验。

**盲审**：`references/dispatch.py review` 一条命令完成跨厂商盲审：每家在空目录中运行，只收到固定模板和原始材料，结果存档并核对应答模型。不带 `--go` 只列出发送计划，加 `--go` 才发送。`dispatch.py run` 把任务派给默认执行者，被派方只返回文字；加 `--read-dir <项目目录>` 可只读访问该目录。

**交叉验证**：验证 prompt 只含原始材料和中性问题，不带我方结论。代码闭环为实现、换厂商审查、修正、重跑验证、再审，最多三轮。

**通道**：命令模板见 `references/channels.md`，包括 `codex exec`、Kimi Code CLI、`claude -p` 接 Anthropic 兼容端点（GLM / Kimi coding plan）、`cc_switch.py exec`、裸 API 与 aichat。gemini、qoder、codebuddy 的独立 CLI 已下线（2026-07 核实），不再作为派发通道；Qoder 仍可作宿主。模型 ID 在派发前从本地读取，不写死。

**存档**：每次外部派发存为 `<项目>/.dispatch/<日期时间>-<通道>-<档位>-<角色>.md`，含任务全文、模型和原始输出；该目录自带 `.gitignore`，不随代码提交。多轮闭环进度写入 `.dispatch/STATE.md`，中断后可续。

**防错**：第三方 Anthropic 兼容端点可能把不认识的模型名静默换成默认模型，`references/verify_model.py` 核对响应中的 `model` 字段。同一通道连续失败 2 次切换备选；外派时设 `AI_CROSS_PEER=1`，被派方不再向下派发。

## 安装

任选一种，同一台电脑只装一份。

**skills.sh（推荐，需要 Node.js）**

```bash
npx skills add keros68/xiaoyu-skill --skill ai-cross -g
```

用 `-a claude-code -a codex -a kimi-code-cli -a pi` 指定 Agent；更新用 `npx skills update -g`。

**交给 Agent 安装**：把下面这段发给正在用的 Agent：

```text
用 skills.sh 安装 keros68/xiaoyu-skill 里的 ai-cross：运行
npx skills add keros68/xiaoyu-skill --skill ai-cross -g -a <你自己对应的 agent 名，如 claude-code、codex、kimi-code-cli、pi>
不要手动复制文件。如果你是 Claude Code，再把装好的 ai-cross/agents/ 下的 *.md 复制到 ~/.claude/agents/。
装完提醒我新开会话，然后说"使用 ai-cross 盘点模型"。
```

**克隆后复制**（以 Claude Code 为例）

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/ai-cross ~/.claude/skills/ai-cross
```

Claude Code 的内部 subagent 分层需另把 `agents/*.md` 复制到 `~/.claude/agents/`，skills.sh 不会自动复制。装完新开会话。其他宿主放入各自的 skills 目录（Qoder 见 `qoder/HOWTO.md`）；不支持 skill loader 的把 `SKILL.md` 作项目规则使用。

## 使用

```text
使用 $ai-cross 盘点模型
```

也可直接说"让别的模型看看这段代码"，首次使用会先登记本机模型。盘点后可选跑一次演示：把一段埋了错误的示例代码发给两家厂商审查，对比各自找到的问题和 token 用量（不读取你的项目文件）。

正常工作时的表现：

- 盘点：列出检测到的 CLI 与模型，确认后生成 `manifest.json`。
- 说"让别家审一下这段代码"：先给出路由决策和外发说明（发给谁、多大、脱敏几处），同意前不发送。
- 发送后项目下出现 `.dispatch/<日期时间>-...md`，记录任务原文、应答模型和原始输出。
- 只说"帮我检查一下"、没提其他模型时不触发。

## 凭据处理

密钥保留在原处（CLI 登录态、用户级环境变量、cc-switch 数据库），只在派发时引用。

代码层面：

- `cc_switch.py` 只读打开 cc-switch 数据库，不使用其全局切换（会改写 `~/.claude/settings.json`）。`list` 只输出端点、档位映射和 `has_token`；`exec` 在自身进程中读取 token 并注入子进程环境变量，不进命令行参数，也不返回给 agent（`tests/test_cc_switch.py` 覆盖）。
- `verify_model.py` 只把 token 放在发往你自己端点的请求头中。
- `usage_probe.py` 只输出模型 ID、次数和时间戳，不读对话内容。
- `inventory.py` 只读取配置中的模型字段，只写入自己的 manifest（`tests/test_inventory.py` 覆盖）。
- `dispatch.py` 不读密钥，带 `--go` 才外发，外发前脱敏，存档不含环境变量值（`tests/test_dispatch.py` 覆盖）。

规则层面（`references/security.md`，约束 agent 行为，非代码强制）：密钥不写入 manifest 和 `.dispatch/`，输出中打码，读凭据库前先告知用户，`ANTHROPIC_BASE_URL` 与 `ANTHROPIC_AUTH_TOKEN` 只传给子进程、不写入全局配置。

## 仓库结构

- `SKILL.md`：入口与每次必做的判断；完整路由、闭环和稳健性规则见 `references/rules.md`。
- `references/`：盘点向导、通道模板、密钥规则、派发设计、实测证据，以及盘点、派发、cc-switch 桥、模型核对、用量统计五个脚本。
- `agents/`：Claude Code 用的 scout / worker / heavy / advisor。
- `tests/`：单元测试；`qoder/`：Qoder 宿主适配。

## 已知限制

- `references/evidence.md` 中的基准数据样本小（n=3–5，任务多为自造），只作方向参考，不适用于新模型或新 CLI 版本。
- 模型 ID 和 CLI 参数会变化。manifest 中超过 30 天未验证的条目派发前先冒烟，第三方端点还要过 `verify_model.py`。
- 密钥保护只有 `cc_switch.py` 部分由代码保证，其余为规则约束，对被改过的副本无效。请从可信来源获取。
- 主要支持 Claude Code 和 Codex，其他宿主需自行适配。

## Attribution and Redistribution

This is the ai-cross skill maintained in the [xiaoyu-skill](https://github.com/keros68/xiaoyu-skill) repository by keros68.

Released under the MIT License. Redistributions, forks and modified versions must keep the copyright notice and license text, and must not be presented as the original project or imply endorsement by the original author.

## English

ai-cross is an AI-agent skill that routes tasks to model tiers by task type, has a model from a different vendor cross-check important outputs, and logs every dispatch to `.dispatch/`. It does not use majority voting: checkable facts are verified by running code or tests, and unresolved disagreements are shown side by side. Cross-vendor review needs at least two vendors; with one, tiered dispatch still works.

```bash
npx skills add keros68/xiaoyu-skill --skill ai-cross -g
```

Then run `Use $ai-cross to inventory my available models.` The first run detects installed CLIs, model lists and cc-switch providers read-only (no login, no model calls, no keys printed), asks you to confirm, smoke-tests each entry, and saves `~/.aicross/skill/manifest.json`, shared by all hosts on the machine.

## License

MIT. See [LICENSE](LICENSE).

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [abstract-fig](../abstract-fig/)（图形摘要） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式）｜[返回总览](../../)
