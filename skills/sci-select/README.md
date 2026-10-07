# sci-select

查询 SCI/SCIE/ESCI/SSCI 期刊公开指标、根据论文内容生成候选期刊的 AI agent skill。

> 中文为主，English summary below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![Python 3.12 tested](https://img.shields.io/badge/Python-3.12%20tested-3776AB.svg)](../../.github/workflows/validate.yml)

## 功能

- **期刊查询**：按刊名查 IF、中科院分区、新锐分区、Nature Index、SCI 收录类型、OA/APC、h-index 和审稿速度。
- **候选发现**：根据题名、摘要、关键词或正文片段生成候选期刊，分列方向证据、期刊层级、风险、数据来源和待核验项。
- **风险标注**：标出范围匹配弱、数据缺失、预警名单、ESCI、WoS 收录异常的候选。
- **投稿前审查**：按目标期刊的 Author Guidelines 和同刊惯例检查稿件，见 `references/presubmission-review.md`（原 [journal-fit](https://github.com/keros68/journal-fit) 项目）。配置 `TAVILY_API_KEY` 后指南获取更稳定。

输出是待人工复核的候选和证据，不预测录用，不评价稿件水平。

## 安装

任选一种，同一台电脑只装一份。

**skills.sh（推荐，需要 Node.js）**

```bash
npx skills add keros68/xiaoyu-skill --skill sci-select -g
```

用 `-a claude-code -a codex` 指定 Agent；更新用 `npx skills update -g`。

**交给 Agent 安装**：把下面这段发给正在用的 Agent：

```text
用 skills.sh 安装 keros68/xiaoyu-skill 里的 sci-select：运行
npx skills add keros68/xiaoyu-skill --skill sci-select -g -a <你自己对应的 agent 名，如 claude-code、codex、kimi-code-cli、pi>
不要手动复制文件。装完检查本机是否有 Python 3（已测 3.12），在装好的 sci-select 目录里运行 pip install -r requirements.txt；再告诉我是否设置了 OPENALEX_API_KEY，没有设置时相似论文召回会跳过。
装完提醒我新开会话。
```

**克隆后复制**（以 Claude Code 为例）：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/sci-select ~/.claude/skills/sci-select
```

装好后新开会话。没有 skill loader 的环境可直接把 `SKILL.md` 作为 agent instruction。

## 使用

```text
使用 $sci-select 根据下面这篇论文摘要发现候选期刊，先总结研究方向，再列出方向证据、期刊层级、风险和待核验项；不要评价稿件水平或预测录用。
```

可追加筛选条件：IF 范围、JCR Q 区、2025中科院、2026新锐、SCIE/ESCI、排除预警期刊、返回数量。只有明确提出的条件才作硬筛选，默认按方向证据和发表先例排序。

正常工作时的表现：

- 给题名和摘要：先输出论文画像（研究对象、问题、贡献、目标读者等）和检索式，再列候选。每本期刊带状态（优先核验 / 可选 / 谨慎 / 排除）、匹配置信度与理由、近年同主题先例、官网 scope 状态、期刊层级和指标。不出现"冲刺""主投""保底"标签；未取到的指标标为未获取。
- 说"查一下 Environmental Pollution 的分区和 IF"：只返回该刊指标和各数据来源状态（成功、部分、失败或跳过）。
- 问"我这篇能不能被录用"：回答不预测录用，并列出需要研究者自行评估的方面。

## 候选生成流程

1. 生成结构化论文画像（研究对象、核心问题、贡献类型、方法角色、目标读者、排除方向）和 2–3 组检索式。
2. 从 OpenAlex 检索近 5 年相似论文，按「相似论文数 / 该刊近年发文量」计算密度，减少综合大刊占满候选。
3. 从本地索引按刊名词独立召回专业刊。
4. 从内置 SQLite 补 `2025中科院`、`2026新锐` 和 Nature Index；ISSN、IF、收录类型和审稿速度由 LetPub 补充。候选不足时回退 LetPub 分类检索。
5. 排名前 5 的期刊进入官网 scope 核验队列，补入官网证据后重排；取不到官网 scope 的标为待核验。

`期刊层级` 只描述期刊本身，取值为高位、中位、常规或待定，依次按分区、JCR Q 区、IF 判定。

官方 Journal Finder（Elsevier、Springer Nature、Wiley、Taylor & Francis）不参与默认评分，仅在用户要求或召回置信度低时作为人工核验入口给出。

## 内置数据

`assets/sci_select_journals.sqlite` 收录 22657 本期刊，按标准化刊名匹配：

| 字段 | 说明 |
|---|---|
| `cas_2025` | 2025 中科院分区 |
| `xuankan_2026` | 2026 新锐分区 |
| `nature_index` | 2026 Nature Index publication venue 标记，共 178 本 |
| `tags` | 分区和 Nature Index 标签 |

内置库不含 ISSN、JIF、JCR Q 区和收录类型：第三方表格的 ISSN 错位会把 JCR 字段挂到错误期刊上，未逐条核验的字段不入库。ISSN、IF、收录类型和审稿速度在线获取；**JCR Q 区只能来自自建索引**。仓库不含原始 Excel、ShowJCR 的 `jcr.db` 和运行缓存。

数据读取顺序：

```text
SCI_SELECT_JOURNAL_INDEX_DB
  ↓
SCI_SELECT_JOURNAL_INDEX_PATH / SCI_SELECT_JOURNAL_INDEX_URL
  ↓
assets/sci_select_journals.sqlite
  ↓
LetPub / OpenAlex / XinRui API（可选，需 XINRUI_API_KEY）
```

## Python 调用

```bash
pip install -r requirements.txt
export OPENALEX_API_KEY="your-key"   # 可选；OPENALEX_MAILTO 亦可选
```

[OpenAlex API](https://developers.openalex.org/) 需要 key。未设置时跳过相似论文召回和 OpenAlex 指标（h-index、OA、APC），改用本地专业刊召回与 LetPub，报告中注明原因。

查询单个期刊：

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Environmental Pollution")
print(format_metrics_line(metrics))
```

```text
SCIE | 实时IF≈7.2(非JIF) | NI=2026 | 2025中科院=2区 | 2026新锐=2区
```

以上为 2026-08-01 实跑输出（LetPub 仅给出实时 IF；未配 `OPENALEX_API_KEY`，故无 h-index 和 OA）。

发现候选期刊，硬筛选条件需显式传参：

```python
from scripts.select_journals import select_journals, format_selection_report, format_selection_csv

bundle = select_journals(
    text=paper_text,
    paper_profile=profile,       # 可选
    impact_low="5",
    impact_high="20",
    jcr_quartiles=["Q1", "Q2"],
    cas_partitions=["1区"],
    xinrui_partition="1区",
    coverage_types=["SCIE"],
    exclude_warnings=True,
    exclude_esci_only=True,
    max_candidates=10,
)
print(format_selection_report(bundle["profile"], bundle["results"]))
csv_text = format_selection_csv(bundle["profile"], bundle["results"])
```

高风险场景可让两个模型独立生成画像，以 `independent_profiles=[profile_a, profile_b]` 传入；方向分歧大时保留多组检索式、扩大召回并在报告中提示。示例见 [`examples/demo-report.md`](examples/demo-report.md)，画像字段见 [`references/paper-profile.schema.json`](references/paper-profile.schema.json)。

官网 scope 核验与重排（`bundle["scope_verification"]` 给出待核验期刊）：

```python
from scripts.scope_evidence import verify_official_scope
from scripts.select_journals import rerank_with_scope_evidence

scope_record = verify_official_scope(
    bundle["profile"],
    "Journal Name",
    official_scope_text,
    "https://publisher.example/journal/aims-and-scope",
    publisher_domain_confirmed=True,
)
reranked = rerank_with_scope_evidence(
    bundle["profile"], bundle["results"], [scope_record]
)
```

`verify_official_scope` 要求 HTTPS 链接、至少 120 字符正文，并由调用者确认域名属于期刊或出版社；openalex.org、letpub.com.cn、wikipedia.org、scansci 来源直接拒绝。程序不抓取出版社网站。

## 更新本地索引

```bash
python -m scripts.build_journal_index --cas-2025-xlsx "/path/to/cas_2025.xlsx" --sqlite-output "/path/to/sci_select_journals.sqlite"
export SCI_SELECT_JOURNAL_INDEX_DB="/path/to/sci_select_journals.sqlite"
```

```powershell
$env:SCI_SELECT_JOURNAL_INDEX_DB = "$HOME\journal-index\sci_select_journals.sqlite"
```

也可用 `SCI_SELECT_JOURNAL_INDEX_PATH` 或 `SCI_SELECT_JOURNAL_INDEX_URL` 指向本地或自托管 JSON（`{"journals": [...]}` 或数组）：

```json
[{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491", "cas_2025": "2区", "xuankan_2026": "2区"}]
```

构建参数（XinRui、JCR、Nature Index、ShowJCR 导入）和可识别字段见 [`references/data-sources.md`](references/data-sources.md)。

## 评测

`benchmarks/corpus_manifest.json` 含 60 篇 DOI，覆盖 20 个主题层、每层 3 篇，来自 60 本不同期刊；按主题分层拆为 40 篇开发集和 20 篇留出测试集，原发表期刊仅作辅助标签。正式评测前须人工审查语料。

指标为社区 Recall@K、专家可接受期刊 Recall@K、nDCG 和综合大刊暴露率。标注池合并多系统或冻结版本的候选，允许专家补充期刊；每个候选由至少两名研究者独立标注 `suitable` / `borderline` / `unsuitable`。标签不完整时评分脚本输出 `ready=false` 并以非零码退出。命令见 [`references/benchmarking.md`](references/benchmarking.md)。

## 数据发布检查

每次 push 和 pull request 运行测试和索引审计：检查标准化刊名重复、ISSN 格式与校验位、身份冲突、分区格式和字段来源；库中含 ISSN 时按固定种子抽样对照 Crossref。严重错配率高于 2% 或来源缺失时 CI 失败。当前内置库不含 ISSN，Crossref 抽样不适用（`external_identity_gate_applicable: false`）。

## 项目结构

- `SKILL.md`：skill 主说明和触发规则；`agents/openai.yaml`：OpenAI 侧 agent 清单。
- `scripts/select_journals.py`：主题识别、候选检索、排序和报告；`similar_works.py`：OpenAlex 相似论文召回；`scope_evidence.py`：官网 scope 核验；`journal_metrics.py`：单刊指标；`profile_consistency.py`：画像校验与跨模型一致性。
- `scripts/build_journal_index.py` / `audit_journal_index.py`：索引构建与审计。
- `scripts/benchmark_dataset.py` / `benchmark_run.py` / `benchmark_score.py`：评测数据、执行与评分。
- `references/`：数据源、评测协议、画像 schema、投稿前审查、常见错误。
- `examples/demo-report.md`：示例报告；`tests/`：77 项行为测试。

## 验证

```bash
python -m unittest discover -s tests -v
python -m scripts.audit_journal_index assets/sci_select_journals.sqlite --sample-size 20 --max-severe-mismatch-rate 0.02
```

```powershell
Get-ChildItem scripts -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## 已知限制

- 不预测录用，不评价创新性、实验设计、数据、图表或语言质量。
- 同一研究通常有多个合理去向，原发表期刊未进前几名不算推荐错误。
- 硬筛选会剔除字段缺失的候选：内置库无 JCR Q 区，传 `jcr_quartiles` 会清空结果；`impact_low` / `impact_high` 会剔除 IF 未获取的候选。
- 只给题名或摘要时只能判断主题范围；关键词宽泛会召回大量相近期刊，方法词过强时应用论文可能被带到方法类期刊。
- LetPub、OpenAlex、JCR、分区表和官网更新节奏不同，数据可能冲突或滞后。收录状态以 Clarivate Master Journal List 或 JCR 为准。
- 中科院分区字段写作 `2025中科院`，新体系写作 `2026新锐`，不存在「中科院2026分区」。
- 不替代阅读期刊官网、scope、author guidelines 和版面费政策；不自动登录出版社网站，不绕过验证码、付费墙或机构权限。

## Attribution and Redistribution

This project is the original sci-select skill by keros68: https://github.com/keros68/sci-select

Released under the MIT License. Redistributions, forks and modified versions must keep the copyright notice and license text, and must not be presented as the original project or imply endorsement by the original author.

## English

sci-select is an AI-agent skill that looks up public metrics for SCI/SCIE/ESCI/SSCI journals and turns a manuscript title, abstract, keywords or excerpt into an evidence-backed candidate list for manual review. It does not predict acceptance or review manuscript quality.

It builds a manuscript profile, retrieves recent similar works from OpenAlex normalized by each journal's publication volume, adds a specialist-journal recall channel, and fills partition data from a bundled SQLite index (22657 journals; 2025 CAS, 2026 XinRui, 2026 Nature Index). LetPub supplies ISSN, IF, coverage type and review speed. The top five candidates go through official-scope verification. Unverified ISSN/JIF/JCR fields are excluded from the bundled index; JCR quartiles come only from a user-built index. The repository includes a 60-paper blinded benchmark with expert labeling and a CI gate for index identity and provenance.

```bash
npx skills add keros68/xiaoyu-skill --skill sci-select -g
pip install -r requirements.txt   # Python 3, tested on 3.12; set OPENALEX_API_KEY for similar-work recall
```

```text
Use $sci-select to discover candidate journals for this abstract, with scope evidence, objective journal levels, risks, and missing-data notes. Do not evaluate manuscript quality or predict acceptance.
```

## License

MIT. See [LICENSE](LICENSE).

---

**同系列 Agent Skills**：[academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [abstract-fig](../abstract-fig/)（图形摘要） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
