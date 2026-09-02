# sci-select

sci-select 是一个 AI agent skill，用于查询 SCI/SCIE/ESCI/SSCI 期刊的公开指标，以及根据题名、摘要、关键词或正文片段生成一组待人工复核的候选期刊，并给出方向证据、期刊层级、风险和数据来源说明。

> 中文为主，English summary below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![Python 3.12 tested](https://img.shields.io/badge/Python-3.12%20tested-3776AB.svg)](../../.github/workflows/validate.yml)

## 功能

- **期刊查询**：按刊名查 IF、中科院分区、新锐分区、Nature Index、SCI 收录类型、OA/APC、h-index 和审稿速度。
- **候选发现**：从论文内容生成候选期刊，分开输出方向匹配、期刊客观层级、证据强弱、来源状态和待核验项。
- **风险标注**：标出范围匹配弱、数据缺失、预警名单、ESCI、WoS 收录异常的候选。
- **投稿前定向审查**：选定目标期刊后，按该刊 Author Guidelines 和同刊惯例检查稿件。原独立项目 [journal-fit](https://github.com/keros68/journal-fit) 已并入本仓库，见 `references/presubmission-review.md`；配置 `TAVILY_API_KEY` 可提升指南获取成功率。

研究方案、稿件质量、目标期刊选择和最终投稿由作者与研究团队负责；本 skill 只提供候选、证据、核验和不确定性，不预测录用或把指标包装成适配度。

## 安装

在支持 skills / agent instructions 的工具里：

```text
请从 GitHub 安装这个 skill，并在 SCI 期刊查询、论文投稿选刊、候选期刊对比时优先使用它：
https://github.com/keros68/xiaoyu-skill/tree/main/skills/sci-select
```

也可以从 `xiaoyu-skill` 仓库复制到所用工具的 skills 目录，例如 Claude Code：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/sci-select ~/.claude/skills/sci-select
```

安装后新开窗口或重启 agent。没有 skill loader 的环境，把 `SKILL.md` 直接作为 agent instruction 使用。

调用时可以只给摘要：

```text
使用 $sci-select 根据下面这篇论文摘要发现候选期刊，先总结研究方向，再列出方向证据、期刊层级、风险和待核验项；不要评价稿件水平或预测录用。
```

也可以追加筛选条件（IF 范围、JCR Q 区、2025中科院、2026新锐、SCIE/ESCI、排除预警期刊、返回数量）。这些条件只在明确提出时才作为硬筛选，默认仍按方向证据和发表先例排序。

## 候选如何生成

1. AI 生成结构化论文画像：研究对象、核心问题、贡献类型、方法角色、目标读者、排除方向，并产出 2–3 组检索式。
2. 从 OpenAlex 检索近 5 年相似论文，按「相似论文数 / 该刊近年发文量」计算密度，减少综合大刊靠发文量占满候选的偏差。
3. 同时从本地索引按刊名词召回专业刊。这是独立召回通道，不依赖大刊黑名单。
4. 内置 SQLite 补 `2025中科院`、`2026新锐` 和 Nature Index。内置库不含 ISSN 和收录类型，因此选刊模式下每个候选仍会访问 LetPub 补 ISSN、IF、收录类型和审稿速度；候选数不足时再回退 LetPub 分类检索。
5. 为排名前 5 的期刊建立官网 scope 核验队列。补入真实官网证据后，对同一候选池重排；无法合法、稳定取得官网 scope 时标为待核验，不伪装成已验证。

`期刊层级` 只描述期刊本身，取值为高位、中位、常规或待定，依次按分区、JCR Q 区、IF 判定。它不代表稿件水平，也不转换成冲刺、主投或保底。

官方 Journal Finder（Elsevier、Springer Nature、Wiley、Taylor & Francis）不参与默认评分。只有用户主动要求，或候选召回置信度较低时，才生成这些人工核验入口。

## 内置数据

下载后即可用。`assets/sci_select_journals.sqlite` 收录 22657 本期刊，按标准化刊名匹配：

| 字段 | 说明 |
|---|---|
| `cas_2025` | 2025 中科院分区 |
| `xuankan_2026` | 2026 新锐分区 |
| `nature_index` | 2026 Nature Index publication venue 标记，共 178 本 |
| `tags` | 分区和 Nature Index 标签 |

内置库不打包 ISSN、JIF、JCR Q 区和收录类型：第三方表格的 ISSN 错位会把一本期刊的 JCR 字段挂到另一本上，未逐条核验的字段一律不入库。ISSN、IF、收录类型和审稿速度由 LetPub 在线补充，缺失时显式标为未获取；**JCR Q 区没有在线来源，只有自建索引才会有这个字段**。仓库同样不打包原始 Excel、ShowJCR 的 `jcr.db` 或源码、运行缓存。

运行时读取顺序：

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
```

[OpenAlex 当前 API](https://developers.openalex.org/) 要求使用 key。未设置时跳过相似论文召回和 OpenAlex 指标（h-index、OA、APC），降级到本地专业刊召回与 LetPub，并在报告中写明降级原因，而不是把失败当成无相似论文。`OPENALEX_MAILTO` 是可选的联系信息。

```bash
export OPENALEX_API_KEY="your-key"
```

查询单个期刊：

```python
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

metrics = get_journal_metrics("Environmental Pollution")
print(format_metrics_line(metrics))
```

```text
SCIE | 实时IF≈7.2(非JIF) | NI=2026 | 2025中科院=2区 | 2026新锐=2区
```

上面是 2026-08-01 的实跑输出。当时 LetPub 该刊页面只给出实时 IF，未配 `OPENALEX_API_KEY`，所以没有 h-index 和 OA 字段。

根据论文内容发现候选期刊：

```python
from scripts.select_journals import select_journals, format_selection_report

bundle = select_journals(text=paper_text, paper_profile=profile, impact_low="3")
print(format_selection_report(bundle["profile"], bundle["results"]))
```

完整调用示例见 [`examples/demo-report.md`](examples/demo-report.md)，论文画像字段见 [`references/paper-profile.schema.json`](references/paper-profile.schema.json)。高风险场景可让两个模型独立生成画像，通过 `independent_profiles=[profile_a, profile_b]` 传入；方向分歧较大时，程序保留多组检索式、扩大召回，并在报告中提示分歧，不强行合成一个共识方向。

筛选面板式的硬约束要显式传参，不要只写在提示词里：

```python
from scripts.select_journals import select_journals, format_selection_csv

bundle = select_journals(
    text=paper_text,
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

csv_text = format_selection_csv(bundle["profile"], bundle["results"])
```

第一阶段返回 `bundle["scope_verification"]`。取得前几本期刊的官网 aims and scope 正文与 URL 后，做第二阶段核验和重排：

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

`verify_official_scope` 要求 HTTPS 链接和至少 120 字符的正文，并由调用者显式确认域名属于期刊或出版社；openalex.org、letpub.com.cn、wikipedia.org、scansci 会被直接拒绝。程序本身不抓取出版社网站，不自动登录，也不绕过验证码。

## 更新本地索引

用自己的数据覆盖默认库：

```bash
python -m scripts.build_journal_index --cas-2025-xlsx "/path/to/cas_2025.xlsx" --sqlite-output "/path/to/sci_select_journals.sqlite"
export SCI_SELECT_JOURNAL_INDEX_DB="/path/to/sci_select_journals.sqlite"
```

Windows PowerShell（路径换成你自己的位置，不要求固定盘符）：

```powershell
$env:SCI_SELECT_JOURNAL_INDEX_DB = "$HOME\journal-index\sci_select_journals.sqlite"
```

也支持本地或自托管 JSON，用 `SCI_SELECT_JOURNAL_INDEX_PATH` 或 `SCI_SELECT_JOURNAL_INDEX_URL` 指向 `{"journals": [...]}` 或裸数组：

```json
[{"title": "ENVIRONMENTAL POLLUTION", "issn": "0269-7491", "cas_2025": "2区", "xuankan_2026": "2区"}]
```

完整构建参数（XinRui、JCR、Nature Index、ShowJCR 导入）和可识别的行字段见 [`references/data-sources.md`](references/data-sources.md)。

## 负责任评测

`benchmarks/corpus_manifest.json` 提交了 60 篇 DOI，覆盖 20 个主题层、每层 3 篇，采样器保证 60 篇来自不同期刊。正文摘要只在本地物化，按主题分层拆为 40 篇开发集和 20 篇完全留出的测试集；原发表期刊单独封存，只作辅助标签。采样器会排除会议/论文集信号和争议收录状态的刊源，并检查摘要长度、ISSN、参考文献数和主题命中，但正式评测前仍须由研究者人工审查语料质量。

主指标是社区 Recall@K、专家可接受期刊 Recall@K、nDCG 和综合大刊暴露率。标注池必须合并多系统或冻结版本的候选，并允许专家独立补充期刊，不能只评价当前系统自己召回的名单。每个候选须由至少两名研究者独立标注 `suitable` / `borderline` / `unsuitable`，模型不能冒充专家。标签不完整时评分脚本输出 `ready=false` 并以非零码退出，此时不得发布准确率。完整命令见 [`references/benchmarking.md`](references/benchmarking.md)。

## 数据发布门槛

每次 push 和 pull request 都会运行测试和索引审计。审计检查标准化刊名重复、ISSN 格式与校验位、身份冲突、分区格式和字段来源；数据库包含 ISSN 时还会按固定种子抽样对照 Crossref。严重错配率高于 2% 或来源缺失时 CI 失败，不发布数据库更新。当前内置库为避免错误身份关联而不含 ISSN，因此外部 Crossref 抽样报告为不适用（`external_identity_gate_applicable: false`），实际执行的是全库结构与来源检查。

```bash
python -m scripts.audit_journal_index assets/sci_select_journals.sqlite \
  --sample-size 20 --max-severe-mismatch-rate 0.02
```

## 项目结构

- `SKILL.md` — skill 主说明和触发规则；`agents/openai.yaml` — OpenAI 侧 agent 清单。
- `scripts/select_journals.py` — 主题识别、候选检索、排序和报告生成；`similar_works.py` — OpenAlex 相似论文召回；`scope_evidence.py` — 官网 scope 核验；`journal_metrics.py` — 单刊指标聚合；`profile_consistency.py` — 画像校验与跨模型一致性。
- `scripts/build_journal_index.py` / `audit_journal_index.py` — 索引构建与发布前审计。
- `scripts/benchmark_dataset.py` / `benchmark_run.py` / `benchmark_score.py` — 盲测数据、执行与评分。
- `references/` — 数据源、评测协议、论文画像 schema、投稿前审查、常见错误。
- `examples/demo-report.md` — 示例报告；`tests/` — 77 项行为测试。

## 验证

```bash
python -m unittest discover -s tests -v
python -m scripts.audit_journal_index assets/sci_select_journals.sqlite --sample-size 20 --max-severe-mismatch-rate 0.02
```

Windows PowerShell 语法检查：

```powershell
Get-ChildItem scripts -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## 已知限制

- 不预测录用概率，不评价创新性、实验设计、数据质量、图表或语言质量，也不把摘要初筛包装成全文评价。
- 不声称存在唯一最优期刊；同一研究通常有多个合理去向，原发表期刊未进前几名不算推荐错误。分区不机械翻译成冲刺、主投、稳妥或保底，默认只报告期刊客观层级。
- 硬筛选按字段值过滤，字段缺失的候选会被剔除。内置库不含 JCR Q 区，此时传 `jcr_quartiles` 会清空结果；`impact_low` / `impact_high` 同样会剔除 IF 未获取的候选。
- 只给题名或摘要时，只能判断主题范围。期刊 scope 很细，宽泛关键词会召回大量看起来相关的期刊；方法词太强时，应用论文可能被带到方法类期刊。
- LetPub、OpenAlex、JCR、分区表和期刊官网更新节奏不同，第三方数据可能冲突或滞后。SCI/SCIE/SSCI/ESCI 收录状态最终应以 Clarivate Master Journal List 或 JCR 复核。
- 不写「中科院2026分区」。中科院分区字段用 `2025中科院`，新体系用 `2026新锐`。
- 不替代作者阅读期刊官网、scope、author guidelines 和版面费政策；不自动登录出版社网站，不绕过验证码、付费墙、机构权限或账号限制。

## Attribution and Redistribution

This project is the original sci-select skill by keros68:

https://github.com/keros68/sci-select

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

sci-select is an AI-agent skill for journal lookup and candidate-journal discovery. It queries public metrics for a known journal, or turns a manuscript title, abstract, keywords, or excerpt into an evidence-backed list of SCI/SCIE/ESCI/SSCI candidates for manual review. It is not a best-journal predictor, manuscript-quality reviewer, or acceptance-probability estimator.

The default workflow builds a model-neutral manuscript profile, retrieves recent similar works from OpenAlex, normalizes that evidence by each journal's recent publication volume, adds a separate specialist-journal recall channel, and fills partition data from the bundled title-keyed SQLite index (22657 journals; 2025 CAS partitions, 2026 XinRui partitions, 2026 Nature Index venue flags). LetPub supplies ISSN, IF, coverage type, and review speed, and backs up recall when it is too small. The top five candidates enter a second-pass official-scope verification queue. Output separates scope-fit evidence, objective journal level, data gaps, and risks.

Unverified ISSN/JIF/JCR fields are deliberately excluded from the bundled index; a user-built SQLite/JSON index is the only source of JCR quartiles. The repository also includes a 60-paper, 20-stratum blinded benchmark protocol, an expert relevance-labeling protocol, Recall@K/nDCG/generalist-exposure scoring, and a CI release gate for journal-index identity and provenance. Human expert labels are required before any accuracy claim is published.

```text
Use $sci-select to discover candidate journals for this abstract, with scope evidence, objective journal levels, risks, and missing-data notes. Do not evaluate manuscript quality or predict acceptance.
```

## License

MIT. See [LICENSE](LICENSE).

---

**同系列 Agent Skills**：[academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [abstract-fig](../abstract-fig/)（图形摘要） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
