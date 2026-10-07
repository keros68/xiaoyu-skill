# academic-reference-matcher

为已有学术文本补充、核验、替换和格式化参考文献的 AI agent skill。逐条拆出需引用的论断，检索候选文献，判断是否真正支撑，输出带证据等级的结果。适用于论文段落、综述、基金申请、rebuttal 和已有文献列表。

> 中文为主，English below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

## 功能

**任务模式**

| 模式 | 作用 | 是否检索新文献 |
|---|---|---|
| Add | 补引用 | 是 |
| Verify | 核验已有引用是否支撑论断 | 仅在身份、版本有疑问或有必要缺口时 |
| Replace | 替换弱引用、错引用、过时和撤稿文献 | 是 |
| Format | 转换文献格式 | 否 |
| Extract | 挑出需要引用的论断 | 否 |

**工作深度**：Quick（1–3 条论断）、Standard（一个段落或短小节，出 claim 表）、Deep（长小节或有争议论断）、Audit（引用证据审计、高风险稿件）。深度越高核验越细，处理范围不变。

**证据分级**：每条引用标注证据基础（元数据、摘要、摘录或全文）。题名相似不算核验通过，只有元数据的文献不作强支撑。查不到的论断列入 Could not verify，不补凑文献。

**输出**：小请求直接给带引用的正文和文献列表。大任务可写成 `reference-match-report.md`，含正文、claim-reference 对照表、参考文献和检索记录。可按需输出 APA、GB/T 7714、Vancouver、IEEE 格式及 BibTeX/RIS。

**人工确认**：超过 10 条论断、高风险论断（临床、安全、监管、政策）或批量修改时，先试跑 3–5 条，确认后继续；批量替换先给替换表。

## 安装

任选一种，同一台电脑只装一份。

**skills.sh（推荐，需要 Node.js）**

```bash
npx skills add keros68/xiaoyu-skill --skill academic-reference-matcher -g
```

用 `-a claude-code -a codex` 指定 Agent；更新用 `npx skills update -g`。

**交给 Agent 安装**：把下面这段发给正在用的 Agent：

```text
用 skills.sh 安装 keros68/xiaoyu-skill 里的 academic-reference-matcher：运行
npx skills add keros68/xiaoyu-skill --skill academic-reference-matcher -g -a <你自己对应的 agent 名，如 claude-code、codex、kimi-code-cli、pi>
不要手动复制文件。装完告诉我你能不能联网检索文献；不能的话，我需要自己提供文献列表、PDF 或数据库导出。
装完提醒我新开会话。
```

**克隆后复制**（Claude Code 用 `~/.claude/skills/`，Codex 用 `~/.codex/skills/`）：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/academic-reference-matcher ~/.claude/skills/academic-reference-matcher
```

没有 skill loader 的环境可直接把 `SKILL.md` 作为 agent instruction，需要更严格的检索时附上 `references/` 中的规则文件。

## 使用

```text
使用 $academic-reference-matcher 为下面这段话找参考文献，并输出 claim-reference 表。
```

更多写法见 `examples/example-requests.md`。正常工作时的表现：

- 给一段文字要求补文献：先确定模式和深度，再逐条给出候选文献、证据基础和支撑理由，每条标为接受、拒绝或未核验。
- 要求把已有文献转成 GB/T 7714：只转格式，缺的字段标出。
- 只说"帮我找关于某主题的文献"、没给具体文本时不触发。

## 限制

- 不做开放式文献检索、主题查全、系统综述语料构建或 PRISMA 流程，也不用于一般事实核查和法律、新闻引用。
- 不含搜索引擎、付费数据库和引用解析器，检索质量取决于宿主 agent 的工具和用户提供的文献。宿主不能联网时，只在用户提供的文献列表、PDF、Zotero 导出或检索结果中核实。
- 不绕过付费墙、验证码和登录墙；付费墙文献可留作候选。
- 没有限定语料范围或可复现检索式时，不声称覆盖完整。
- 期刊最终格式和高风险稿件仍需人工复核。

## 文件结构

- `SKILL.md`：主说明和触发规则。
- `references/`：检索规划、来源选择、付费墙处理、证据评分、输出格式和审计模板。
- `examples/`：请求示例。
- `agents/openai.yaml`：显示名、简介和默认提示词。

## Attribution and Redistribution

This is the original academic-reference-matcher skill by keros68, released under the MIT License. Redistributions, forks and modified versions must keep the copyright notice, the license text, and `NOTICE.md`, and must not be presented as the original project or imply endorsement by the original author.

## English

academic-reference-matcher is an AI-agent skill that adds, verifies, replaces, and formats scholarly references for user-supplied academic text. It extracts citation-worthy claims, searches candidates (Add/Replace only), checks whether each one supports the claim, and reports the evidence basis for every citation. Metadata-only matches are never strong support; claims with no reliable match go into a "Could not verify" section.

```bash
npx skills add keros68/xiaoyu-skill --skill academic-reference-matcher -g
```

```text
Use $academic-reference-matcher to find and verify scholarly references for this paragraph.
```

Format does no new search; requests with more than 10 claims run a 3–5-claim sample first. It is not for open-ended literature discovery or systematic reviews, and does not bypass paywalls, CAPTCHAs, or login walls.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [abstract-fig](../abstract-fig/)（图形摘要） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式） · [study-area-map](../study-area-map/)（研究区区位图） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
