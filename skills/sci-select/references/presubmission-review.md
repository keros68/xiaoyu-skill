
# Pre-Submission Review Mode

This file defines sci-select's pre-submission review mode. Precondition: the target journal is already chosen. This mode does not discover or recommend candidate journals; route journal discovery and metrics lookup to the default sci-select workflow. The statuses used here (`P0` must fix / `P1` recommended / `P2` optional / `Pass` / `Unable to assess`) belong to this mode only - do not mix them with the candidate statuses (`优先核验` / `可选` / `谨慎` / `排除`) or journal levels used by the discovery workflow.

Run a journal-specific pre-submission review: diagnose whether a manuscript meets the target journal's Author Guidelines, submission requirements, and observable same-journal conventions. This is not peer-review simulation or an acceptance/rejection judgment. This mode does two things only: check the draft and give revision directions. Do not draft replacement prose, rewrite sections, or create writing templates unless the user explicitly switches to a writing/polishing task.

Optional setup: guideline fetching works with zero configuration, but a `TAVILY_API_KEY` environment variable in the host improves Author Guidelines retrieval. Never write the key into any repository or output. Without a key, follow the fallback order in `guidelines-fallback-matrix.md` (Firecrawl no-key mode first, then Tavily when configured, then public readers, then search snippets and third-party summaries, then user-pasted text).

## Operating Rules

- For vague requests, default to Quick Check. Ask a scope question only when the user appears to want a deeper, narrower, or non-default diagnostic.
- Use real journal evidence for hard compliance claims. Do not replace missing Author Guidelines with publisher defaults.
- Treat third-party guideline aggregators as fallback evidence only. Label the source and tell the user to verify current official requirements before submission.
- Mark unsupported items as "unable to assess" rather than guessing.
- Keep outputs diagnostic: issue, evidence, risk, and revision direction.
- Do not simulate peer review, assign accept/reject decisions, or judge scientific contribution strength. Keep review claims tied to journal requirements, submission materials, and same-journal conventions.
- If the user writes in Chinese, answer in Chinese unless they request another language.
- Do not attempt to bypass paywalls, CAPTCHAs, login walls, or institutional access. When blocked, continue down the fallback order in `guidelines-fallback-matrix.md` (readers and proxies before search snippets and third-party summaries), and only then ask the user to paste the official text.

## Start Here — Default To Quick Check

Most users do not know which diagnostic scope they need. Do not force them to choose technical categories before they understand the problem. If the request is vague, default to **Quick Check** and proceed.

Vague requests include:

- "帮我看看这篇能不能投这个期刊"
- "投稿前帮我检查一下"
- "看看哪里需要改"
- "Check this against Journal X"

Collect only the minimum missing inputs:

1. Target journal name or ISSN.
2. Manuscript draft path or pasted text. Supported inputs are `.docx`, `.pdf`, `.md`, and `.txt`.

If both are available, do not ask the user to choose A/B/C/D/E. State the default and run:

> I will start with Quick Check: confirmed Author Guidelines requirements, abstract/keywords, required submission items, obvious missing statements, and clear format risks. I will not rewrite, polish, or run expensive deep benchmarking unless needed.

Ask at most one scope question when the user appears to want something beyond Quick Check:

> Do you want a quick check, a full pre-submission check, or a section-specific check? If unsure, I will start with Quick Check.

### Internal Scope Mapping

Use this mapping internally. Do not dump the table on novice users unless helpful.

| User concern | Internal scope | Run |
|---|---|---|
| "会不会被编辑部/投稿系统退回" | Quick Check / Format compliance | Author Guidelines essentials only |
| "准备正式投稿前帮我完整把关" | Submission readiness | Format compliance + selected same-journal benchmarks |
| "和这个期刊常见写法差多远" | Style alignment | Same-journal, same-topic benchmark |
| "只看摘要/引言/结论" | Section-specific fit | One named section compared with exemplars |
| "英语表达/语言风格像不像" | Language style | OA full-text language features, only when enough full text exists |

### Quick Check Defaults

Quick Check includes:

- confirmed Author Guidelines requirements;
- abstract word limit and structure;
- keyword count;
- required submission items such as Highlights, Graphical Abstract, Data Availability, CRediT, ethics/declaration items;
- reference format only if explicitly required by the journal;
- obvious missing sections or statements.

Quick Check excludes by default:

- language polishing;
- replacement prose;
- full same-journal style benchmarking;
- OA full-text language analysis;
- acceptance prediction.

After Quick Check, recommend an upgrade only when useful: full pre-submission check, same-journal benchmark, language-style analysis, or section-specific fit.

## Evidence Workflow

### 1. Journal And Guidelines

Resolve journal identity first: title, ISSN, publisher, article type, and target manuscript type when relevant.

For Author Guidelines, prefer sources in this order:

1. Firecrawl Scrape API (no API key required, free tier: 1000 requests/month). Works across Claude Code, Codex, Cursor, WorkBuddy, and any agent with HTTP access.
2. Tavily extract for the official page, only when `TAVILY_API_KEY` is already available.
3. Built-in Markdown reader cascade for the official page: try `https://r.jina.ai/{url}`, then `https://defuddle.md/{url}`, then `agent-fetch` only if it is already installed or available through `npx`.
4. Search results or third-party aggregators that summarize guidelines.
5. User-pasted guideline text.

If automatic retrieval is needed, read `guidelines-fallback-matrix.md` for tested retrieval patterns and failure modes. Do not require users to install another skill for Markdown proxy behavior; use the lightweight reader cascade directly. Do not block the task on Tavily or Firecrawl configuration.

Accept reader output only when it has substantial content and contains guideline signals such as `abstract`, `manuscript`, `word`, `figure`, `reference`, `submission`, or `author guidelines`. Reject security checks, cookie pages, access-denied pages, empty pages, and navigation-only fragments. If the page is only a hub with official subpage links, follow the relevant official links before falling back to third-party summaries.

If all automatic retrieval options fail (security check, cookie page, empty page, or navigation fragment), do not stop immediately. Try available web search for official mirrors, publisher help pages, or third-party guideline summaries. If those are still weak, ask the user to paste the guideline text.

Extract only requirements supported by the retrieved text:

| Area | Look For |
|---|---|
| Article type | manuscript type, article category, research article |
| Word limits | word, length, page, text limit |
| Abstract | abstract, structured, unstructured, word limit |
| Keywords | keyword count, keyword limit |
| Highlights | highlights, bullet count, character limit |
| Graphical abstract | graphical abstract, required, optional |
| References | reference count, style, format, limits |
| Figures/tables | figure, table, resolution, dpi, limit |
| Statements | data availability, CRediT, ethics, declaration |
| Formatting | line numbers, layout, language variant |

### 2. Draft Features

Parse only the fields needed for the selected scope.

- `.md` and `.txt`: read directly.
- `.docx`: use `python-docx` or an available document parser.
- `.pdf`: use `pymupdf` or an available PDF parser.

Record counts and locations that support the diagnosis: abstract words, keyword count, section headings, figure/table counts, reference count, statement presence, and section-level lengths.

Done when: word/keyword/reference counts, section headings, and required-statement presence are recorded for the selected scope.

### 3. Same-Journal Benchmarking

Use this only for style alignment, language style, section-specific fit, or full submission readiness. Do not run full benchmarking during Quick Check unless the user explicitly asks for it or the Quick Check reveals a specific need.

Select exemplars from the same journal and similar topic. Avoid high-citation but off-topic papers.

- Use journal ISSN plus topic keywords from the draft title, abstract, and keywords.
- Prefer recent research articles, commonly the last 5-6 years unless the field needs a different window.
- Aim for 8-12 usable exemplars. Fewer than 5 means low confidence.
- Use OpenAlex for discovery, Semantic Scholar for abstracts when available, CrossRef/OpenAlex for metadata, and Europe PMC or publisher OA pages for full text when needed.
- For abstracts, try Semantic Scholar first, then reconstruct OpenAlex `abstract_inverted_index` when present, then use a clean CrossRef abstract if available. Exclude no-abstract papers from abstract-length or language statistics and report the usable count.

Summarize benchmarks with median and IQR. Do not rely on mean plus standard deviation for small, skewed samples.

For language-style checks, require enough full text to support the claim. If fewer than 3 OA full texts are usable, label the result as insufficient rather than making a style recommendation.

Done when: at least 3 same-journal exemplars are compared on the selected soft conventions (report low confidence whenever fewer than 5), or the shortfall is reported.

## Diagnostics

### Format Compliance

Only produce hard compliance findings when the requirement came from real guideline text.

Treat official guideline text and user-pasted official text as eligible for confirmed P0 findings. Treat third-party aggregators and search snippets as fallback evidence only: label them clearly, use them for tentative direction, and mark the item Unable to assess or "needs official verification" before submission.

| Status | Meaning |
|---|---|
| P0 | Must fix: confirmed journal requirement is unmet |
| Pass | Confirmed compliant |
| Unable to assess | Requirement could not be verified from available evidence |

### Style Alignment

Use benchmarks for soft conventions, not hard rules.

| Status | Meaning |
|---|---|
| P1 | Strong recommendation: draft is clearly outside the benchmark and evidence confidence is high |
| P2 | Optional optimization: mild deviation or low-confidence evidence |
| Pass | Draft is within the observed journal convention |
| Unable to assess | Benchmark data is too thin |

## Output Format

Lead with a concise readiness call, then show evidence. Use this structure:

```markdown
## Readiness Call
[Ready / Needs targeted fixes / Not ready], based on [scope].

## Evidence Base
- Guidelines: [official / third-party / pasted / unavailable], source date if visible
- Exemplars: [not run for Quick Check / N papers, topic filter, data completeness]
- Draft: [file/path or pasted text], parsed fields

## P0 - Must Fix
1. [Issue]: current [value]; requirement [value/source] -> revision direction.

## P1 - Recommended
1. [Issue]: current [value]; journal convention [median/IQR, N] -> revision direction.

## P2 - Optional
1. [Issue]: reason and low-risk direction.

## Pass / Unable To Assess
- Pass: [...]
- Unable to assess: [...] because [...]
```

Do not include replacement sentences or rewritten paragraphs. If the user asks for actual wording after the diagnostic, state that this skill's job is complete and switch to an appropriate writing or polishing workflow.

## Common Pitfalls

- Do not infer STOTEN, Wiley, ACS, Springer, or Taylor & Francis requirements from publisher-wide defaults. Mark the item as Unable to assess and request the official page or user-pasted text instead.
- Do not use OpenAlex as an Author Guidelines search engine. Use it for journal identity, article metadata, and same-journal exemplar discovery.
- Do not treat security-check, cookie-consent, access-denied, or near-empty reader output as guideline text. Try the full fallback chain before moving to third-party summaries.
- Do not call a generic journal-information or LetPub-style skill unless it is installed and clearly relevant. If unavailable, skip nonessential metadata and continue with official or public sources.
- Do not treat Tavily, Firecrawl, or third-party aggregator coverage as guaranteed. Use the matrix as a dated test snapshot, not a current fact.
- Do not use CrossRef `page` fields to estimate Elsevier article length; those fields may be article numbers. Use OA full-text PDF parsing for length signals when needed.
- Do not benchmark by ISSN alone. Always add topic keywords.
- Do not consume the Firecrawl free tier on publishers that Tavily or the reader cascade can handle. Reserve Firecrawl for publishers where other tools fail (Wiley, ACS, Springer Nature).

## References

- `guidelines-fallback-matrix.md`: dated retrieval matrix and fallback examples for Author Guidelines.
- `pitfalls-and-solutions.md`: observed failure modes and practical corrections from test runs.
