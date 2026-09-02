# academic-reference-matcher

academic-reference-matcher 是一个 AI agent skill，为用户已提供的学术文本、明确论断或已有参考文献做有界的引用匹配：拆出需要引用的论断，检索候选文献，判断文献是否真的支撑该论断，输出带证据等级的引用结果。适用于论文段落、已写好的综述段落、基金申请、rebuttal 和已有的参考文献列表。

> 中文为主，English below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

## 功能

**五种任务模式**：Add 补引用，Verify 查已有引用是否支撑对应论断，Replace 换掉弱引用、错引用、过时引用和撤稿文献，Format 只转格式，Extract 只挑出需要引用的论断。

**四档工作深度**：Quick 处理几条论断，Standard 处理一个段落并出 claim 表，Deep 用于已给定的长小节或有争议论断，Audit 用于有界的引用证据审计和高风险稿件。深度提升核验与可追溯性，不扩大研究问题。

**证据分级**：候选发现和证据支撑分开记账，题名相似不算已验证。每条引用标注证据基础（元数据、摘要、摘录还是全文），只看得到元数据的文献不能当强支撑。查不到就进 Could not verify 小节，不补一条看起来合理的文献。

**输出**：小请求直接在对话里给带引用的正文和文献列表。较大的任务可写成 `reference-match-report.md`，含引用后的正文、claim-reference 对照表、参考文献和检索审计；APA、GB/T 7714、Vancouver、IEEE 格式的文献列表和 BibTeX/RIS 文件按需另出。

**模式短路与人工确认**：Format 仅转换已知文献格式，不搜新文献；Extract 只提取需引文论断后即停止；Verify 先核验现有引用，仅在身份、版本或必要缺口时补查；Add/Replace 才完整匹配。超过 10 条论断、高风险论断或批量替换时，先试跑 3–5 条并等待人工确认；批量替换先展示替换表。

## 安装与调用

从 `xiaoyu-skill` 仓库复制这个 skill 子目录到 agent 的 skills 目录：

```bash
# Claude Code 用 ~/.claude/skills/，Codex 用 ~/.codex/skills/
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/academic-reference-matcher \
  ~/.claude/skills/academic-reference-matcher
```

装完新开会话后调用：

```text
使用 $academic-reference-matcher 为下面这段话找参考文献，并输出 claim-reference 表。
```

没有 skill loader 的环境，把 `SKILL.md` 当作 agent instruction 使用，需要更严格的检索质量时再附带 `references/` 里的规则文件。更多写法见 `examples/example-requests.md`。

## 限制

- 不用于开放式“找某主题文献”、主题级查全、系统综述语料构建、PRISMA 流程或生成额外研究论断。这些请求应采用独立研究工作流；本 skill 只审计或匹配用户给出的有界文本与 claim。
- 不含搜索引擎、付费数据库权限和引用解析器，检索质量取决于宿主 agent 可用的工具和用户提供的文献库。
- 不绕过付费墙、验证码、登录墙，也不使用未授权的 cookie 或来源；付费墙文献可以留作候选。
- 除非用户给出限定的语料范围或可复现的数据库检索式，否则不宣称覆盖完整。
- 宿主 agent 没有检索或浏览工具时，skill 会要求用户提供文献列表、PDF、Zotero 导出或数据库检索结果，只在这些材料里核实。
- 期刊特定的最终格式和高风险稿件仍需人工复核。

## 文件结构

- `SKILL.md` - skill 主说明和触发规则。
- `references/` - 检索规划、来源路由、付费墙处理、证据评分、输出格式和审计模板。
- `examples/` - 常见请求示例。
- `agents/openai.yaml` - 显示名、一句话简介和默认提示词。

## Attribution and Redistribution

This repository is the original academic-reference-matcher skill by keros68, released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice, the license text, and `NOTICE.md`, and must not present themselves as the original project or imply endorsement by the original author.

## English

academic-reference-matcher is an AI agent skill that finds and verifies scholarly references for user-supplied academic text, explicit claims, existing citations, or known bibliographies. It extracts citation-worthy claims, searches candidates only for Add/Replace work, judges whether each candidate actually supports the claim, and reports each citation with its evidence basis. A metadata-only match is never treated as strong support, and a claim with no reliable match goes into a "Could not verify" section rather than getting a plausible-looking citation.

Copy `skills/academic-reference-matcher` from the `xiaoyu-skill` repository into the agent's skills directory (`~/.claude/skills/` or `~/.codex/skills/`) and start a new session:

```text
Use $academic-reference-matcher to find and verify scholarly references for this paragraph.
```

Format never searches new literature; Extract stops after claim extraction; Verify checks supplied citations before any necessary lookup. The skill is not for open-ended literature discovery, systematic-review corpus construction, or PRISMA work. Task modes, bounded depths, output formats, and limits are documented in `SKILL.md`; it does not bypass paywalls, CAPTCHAs, or login walls.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [abstract-fig](../abstract-fig/)（图形摘要） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
