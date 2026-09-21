<div align="center">

English | [简体中文](README.md)

# xiaoyu-skill

An open-source collection of Agent Skills for academic research: references · journal selection · thesis formatting · scientific figures · multi-model orchestration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Skills](https://img.shields.io/badge/skills-6-blueviolet)
[![Tests](https://github.com/keros68/xiaoyu-skill/actions/workflows/test.yml/badge.svg)](https://github.com/keros68/xiaoyu-skill/actions/workflows/test.yml)

</div>

Each skill is a self-contained directory with a `SKILL.md` that defines its trigger conditions, workflow, and deliverables. The agent matches the right skill automatically from the task description — no manual invocation needed. Install any single skill on its own, or keep the whole repository and update everything in one place.

## Contents

- [Skills](#skills)
- [Quick Start](#quick-start)
- [Supported Agents](#supported-agents)
- [Updating](#updating)
- [Provenance](#provenance)
- [License](#license)

## Skills

| Category | Skill | Purpose | Requirements | Upstream |
| --- | --- | --- | --- | --- |
| References & Citations | [`academic-reference-matcher`](skills/academic-reference-matcher/) | Add, verify, replace, and format citations for existing academic text (GB/T 7714 and common formats) | Internet access for literature search | [keros68/academic-reference-matcher](https://github.com/keros68/academic-reference-matcher) |
| Journals & Submission | [`sci-select`](skills/sci-select/) | SCI journal candidate discovery, metric and risk lookup, pre-submission compliance checks (incl. CAS partition) | Python; internet access for public data | [keros68/sci-select](https://github.com/keros68/sci-select) |
| Thesis Formatting | [`cugb-doctoral-thesis-format`](skills/cugb-doctoral-thesis-format/) | DOCX format pre-check and final review for China University of Geosciences (Beijing) doctoral theses | Python (DOCX processing) | [keros68/cugb-doctoral-thesis-format](https://github.com/keros68/cugb-doctoral-thesis-format) |
| Scientific Figures | [`abstract-fig`](skills/abstract-fig/) | Editable graphical abstracts, concept/mechanism diagrams, and research roadmaps in draw.io | draw.io viewer/editor; image generation optional | [keros68/abstract-fig](https://github.com/keros68/abstract-fig) |
| Scientific Figures | [`study-area-map`](skills/study-area-map/) | Study-area locator maps, shaded-relief basemaps, and multi-panel map compositions | R (ggplot2 + sf + terra) | [keros68/study-area-map.skill](https://github.com/keros68/study-area-map.skill) |
| Multi-Model Orchestration | [`ai-cross`](skills/ai-cross/) | Multi-model task dispatch, tiered execution, and cross-vendor verification | Access to models from multiple providers; shell-capable host | [keros68/ai-cross](https://github.com/keros68/ai-cross) |

## Quick Start

**1. Clone the repository**

Windows PowerShell:

```powershell
git clone https://github.com/keros68/xiaoyu-skill.git "$env:USERPROFILE\xiaoyu-skill"
```

macOS / Linux:

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
```

**2. Copy the skills you need into your agent's user skills directory**

The examples below install `sci-select`; substitute any other skill directory name. After installing, the skill directory should contain `SKILL.md` directly.

Windows PowerShell:

```powershell
Copy-Item -Recurse "$env:USERPROFILE\xiaoyu-skill\skills\sci-select" "$env:USERPROFILE\.codex\skills\sci-select"
```

macOS / Linux:

```bash
mkdir -p ~/.codex/skills
cp -R ~/xiaoyu-skill/skills/sci-select ~/.codex/skills/
```

**3. Describe your task in the conversation**

Matching skills activate automatically by their trigger rules; you can also name one explicitly:

```text
Use sci-select to suggest candidate journals for this paper's title and abstract.
```

Each skill directory has its own `README.md` with detailed usage; `SKILL.md` defines the workflow, triggers, and deliverables.

## Supported Agents

Skills follow the [Agent Skills specification](https://agentskills.io) (`SKILL.md` format) and work with any host that reads it:

| Agent | User skills directory |
| --- | --- |
| Codex | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |
| Other compatible hosts | See host documentation |

Note: some skills depend on host capabilities (internet access, shell, Python/R runtime) — see the Requirements column in [Skills](#skills). Skills may not be fully functional on hosts lacking the required capability.

## Updating

Pull the latest version in your local clone, then re-copy the installed skill directories.

Windows PowerShell:

```powershell
git -C "$env:USERPROFILE\xiaoyu-skill" pull --ff-only
$source = "$env:USERPROFILE\xiaoyu-skill\skills\sci-select"
$target = "$env:USERPROFILE\.codex\skills\sci-select"
New-Item -ItemType Directory -Force $target | Out-Null
Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $target -Recurse -Force
```

macOS / Linux:

```bash
git -C ~/xiaoyu-skill pull --ff-only
mkdir -p ~/.codex/skills/sci-select
cp -R ~/xiaoyu-skill/skills/sci-select/. ~/.codex/skills/sci-select/
```

For Claude Code, replace `.codex` with `.claude` in the paths above.

## Provenance

Each skill originates from an independently maintained repository by the same author (see [Skills](#skills)); original licenses and notices are preserved inside each skill directory. The initial merge baseline commits are listed in [docs/PROVENANCE.md](docs/PROVENANCE.md).

## License

This repository is released under the [MIT License](LICENSE). Each skill directory also retains its original project license and required notices.
