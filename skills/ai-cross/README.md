# ai-cross

ai-cross 是给 AI agent 用的 skill：按任务类型把工作派给不同档位的模型，用不同厂商的模型交叉复查关键产出，每次派发的任务全文和原始输出落盘留痕。

交叉验证用来暴露单个模型漏掉的错误和分歧，不做多数表决：可独立验证的量由编排者跑代码或跑测试核验，其余分歧并列双方证据交用户裁决。

> 中文为主，English summary below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

## 适用场景

- 重要代码改动、科研分析或长文档处理完成后，让另一家厂商的模型独立复查。
- 手里有多个模型入口，想按任务分配：粗活走低成本档，强模型额度留给架构与审查。
- 事后要能查某个结论是哪个模型、哪一档、拿什么输入得出的。

## 环境要求

- 宿主：任意能跑 shell、能加载 `SKILL.md` 的 agent。内部 subagent 分层（scout/worker/heavy/advisor）只有 Claude Code 有，其他宿主全部走外部通道。不能跑 shell 的纯聊天环境用不了外部派发。
- 交叉验证需要至少两家不同厂商的模型。只有一家时分层派发照常可用，盘点报告会明确写出交叉验证不可用，同厂商复查只记为"复核"。
- 凭据：外部通道用各 CLI 自己的 OAuth 登录、用户级环境变量里的 API key，或已配好的 [cc-switch](https://github.com/farion1231/cc-switch)。只用 Claude Code 内部 subagent 时不需要额外凭据。

## 功能

**盘点。** 只读探测本机已装的 agent CLI、cc-switch 供应商清单和各 CLI 的用量日志（不登录、不发模型请求、不输出密钥），摆成一张表让用户勾选一次，确认后才冒烟；结果写进 skill 目录下的 `manifest.md`（厂商 × 档位矩阵与冒烟日期），路由按它走。

**路由与分层。** 分级标准是 `SKILL.md` 的路由表：任务类型决定档位与推理强度两个旋钮，档位语义继承 manifest（哪个模型算低/中/高由用户自己标）。每次派发前先输出一行路由决策行（通道/模型、档位、thinking、理由）供当场纠正。需要精确数值的任务，prompt 要求模型写代码执行，编排者再独立核验，不采信模型自述的计算结果。

**交叉验证。** 验证 prompt 只给原始材料和中性问题，不写入我方结论和解释框架。coding 闭环是实现 → 换厂商审查 → 修正 → 重跑验证 → 再审，最多三轮。

**通道。** 命令模板在 `references/channels.md`：`codex exec`、Kimi Code CLI、`claude -p` 接 Anthropic 兼容端点（GLM / Kimi coding plan）、`cc_switch.py exec` 桥、裸 API 与 aichat。gemini / qoder / codebuddy 的独立 CLI 已下线（2026-07 核实），不再作为派发通道，Qoder 作为宿主仍支持。模型 ID 不写死，派发前从本地事实源读实时值。

**留痕。** 每次外部派发和每轮 review 存为 `<项目>/.dispatch/<日期时间>-<通道>-<档位>-<角色>.md`，含任务全文、模型与原始输出；该目录首次创建时写入一行 `*` 的 `.gitignore`，不随代码库提交。多轮闭环的进度写入 `.dispatch/STATE.md`，中断后从断点继续。

**防错。** 第三方 Anthropic 兼容端点可能对不认识的模型名静默改用默认模型应答，`references/verify_model.py` 比对响应体的 `model` 字段来判定。同一通道连续失败 2 次熔断走备选；外派带 `AI_CROSS_PEER=1`，被派方据此不再往下派。

## 安装

从 `xiaoyu-skill` 仓库复制这个 skill 子目录到宿主的 skills 目录：

```text
# Claude Code
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/ai-cross ~/.claude/skills/ai-cross
# agents/*.md 另拷到 ~/.claude/agents/，内部 subagent 分层才可用
```

Windows 上 `~` 即 `C:\Users\<用户名>`，装完新开会话生效。其他宿主放进各自的 skills 目录（Qoder 见 `qoder/HOWTO.md`），不支持 skill loader 的把 `SKILL.md` 当项目规则用。

## 快速开始

```text
使用 $ai-cross 盘点模型
```

盘点后可选跑一次演示派发：内置的含缺陷代码（不读你的项目文件）发给两家厂商盲审，给出共识、分歧和 token 账单。之后是真实任务：

```text
使用 $ai-cross：实现 XX 功能，完成后让另一家厂商的模型交叉审查。
```

## 凭据处理

key 留在你原本存放它的地方（CLI 登录态、用户级环境变量、cc-switch 数据库），ai-cross 只在派发那一刻引用。代码层做到的：`cc_switch.py` 只读打开 cc-switch 数据库，不改数据、不用它的全局切换机制（那会写 `~/.claude/settings.json`，污染宿主的官方登录），`list` 只输出端点、档位映射和 `has_token` 布尔，`exec` 在脚本自己的进程里读 token 注入子进程环境变量，不进命令行 argv、不回到 agent 的上下文（`tests/test_cc_switch.py` 的 6 个用例覆盖这几条）；`verify_model.py` 只把 token 放进发往你自己那个端点的请求头；`usage_probe.py` 只出模型 ID、次数与时间戳，不读对话内容。

其余是 `references/security.md` 里约束 agent 行为的规则，不是代码强制：key 不写进 manifest 与 `.dispatch/` 留痕、输出里一律打码、读凭据库前先告知用户、`ANTHROPIC_BASE_URL` 与 `ANTHROPIC_AUTH_TOKEN` 只按子进程传而不写进全局配置。

## 仓库结构

- `SKILL.md` - 决策核心：路由规则、执行闭环、稳健性规则
- `references/` - 盘点向导、通道模板、密钥规则、派发设计、实测证据，以及三个只读脚本
- `agents/` - Claude Code 用的 scout / worker / heavy / advisor
- `tests/` `qoder/` - 单元测试与 Qoder 宿主适配。基准原始材料保存在维护者本地归档，不随公开仓库发布。

## 已知限制

- `references/evidence.md` 中的基准数字来自维护者本地实验归档，样本量小（n=3–5，任务多为自造），只作方向性证据，不是精确测量，也不应外推到新模型或新 CLI 版本。
- 模型 ID 和 CLI 参数会漂移。manifest 里超过 30 天未验证的条目派发前先冒烟，第三方端点还要过 `verify_model.py`。
- 密钥纪律只有 `cc_switch.py` 部分做到代码级，其余是规则，挡不住被改过的副本。建议只从可信来源获取本 skill。
- Claude Code 和 Codex 是主要支持对象，其他宿主需按各自规则适配，不承诺开箱即用。

## Attribution and Redistribution

This project is the original ai-cross skill by keros68:

https://github.com/keros68/ai-cross

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

ai-cross is a skill for AI agents: it routes each task to a model tier chosen by task type, has models from a different vendor cross-check important outputs, and writes every dispatch to `.dispatch/` for later review. It is not a majority-voting tool: verifiable facts are validated by running code or tests, and unresolved disagreements are presented side by side. Cross-vendor review needs at least two vendors; with one, tiered dispatch still works and the inventory report says so explicitly.

Install by cloning into `~/.claude/skills/ai-cross`, then run `Use $ai-cross to inventory my available models.` The first run read-only detects installed CLIs, cc-switch providers and local usage logs (no login, no model calls, no keys printed), asks you to confirm once, smoke-tests each entry, and writes `manifest.md`.

## License

MIT. See [LICENSE](LICENSE).

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [abstract-fig](../abstract-fig/)（图形摘要） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式）｜[返回总览](../../)
