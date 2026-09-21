<div align="center">

简体中文 | [English](README.en.md)

# xiaoyu-skill

面向科研工作的开源 Agent Skill 合集：文献引用 · 期刊选刊 · 论文格式 · 学术制图 · 多模型协作

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Skills](https://img.shields.io/badge/skills-6-blueviolet)
[![Tests](https://github.com/keros68/xiaoyu-skill/actions/workflows/test.yml/badge.svg)](https://github.com/keros68/xiaoyu-skill/actions/workflows/test.yml)

</div>

每个 Skill 是一个自带 `SKILL.md` 的独立目录，定义了触发条件、执行流程和交付要求。Agent 根据任务描述自动匹配合适的 Skill，无需手动调用。可以按需安装任意一个 Skill，也可以保留完整仓库统一更新。

## 目录

- [Skill 一览](#skill-一览)
- [快速开始](#快速开始)
- [支持的 Agent](#支持的-agent)
- [更新](#更新)
- [来源与合并基线](#来源与合并基线)
- [License](#license)

## Skill 一览

| 分类 | Skill | 用途 | 环境要求 | 原项目 |
| --- | --- | --- | --- | --- |
| 文献与引用 | [`academic-reference-matcher`](skills/academic-reference-matcher/) | 为已有论述补充、核验、替换和格式化参考文献（支持 GB/T 7714） | 需联网检索文献 | [keros68/academic-reference-matcher](https://github.com/keros68/academic-reference-matcher) |
| 期刊与投稿 | [`sci-select`](skills/sci-select/) | SCI 期刊候选发现、指标与风险查询、投稿前合规检查（含中科院分区） | Python；需联网查询公开数据 | [keros68/sci-select](https://github.com/keros68/sci-select) |
| 论文格式 | [`cugb-doctoral-thesis-format`](skills/cugb-doctoral-thesis-format/) | 中国地质大学（北京）博士论文 DOCX 格式预检与定稿审查 | Python（DOCX 处理） | [keros68/cugb-doctoral-thesis-format](https://github.com/keros68/cugb-doctoral-thesis-format) |
| 学术制图 | [`abstract-fig`](skills/abstract-fig/) | 可编辑的论文图形摘要、概念/机制图、技术路线图（draw.io） | draw.io 查看与编辑；图像生成工具可选 | [keros68/abstract-fig](https://github.com/keros68/abstract-fig) |
| 学术制图 | [`study-area-map`](skills/study-area-map/) | 研究区区位图、地形晕渲底图与多面板地图组织 | R（ggplot2 + sf + terra） | [keros68/study-area-map.skill](https://github.com/keros68/study-area-map.skill) |
| 多模型协作 | [`ai-cross`](skills/ai-cross/) | 多模型分工派发、分层执行与跨厂商交叉验证 | 需接入多个厂商的模型；宿主需支持 shell | [keros68/ai-cross](https://github.com/keros68/ai-cross) |

## 快速开始

**1. 克隆仓库**

Windows PowerShell：

```powershell
git clone https://github.com/keros68/xiaoyu-skill.git "$env:USERPROFILE\xiaoyu-skill"
```

macOS / Linux：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
```

**2. 把需要的 Skill 复制到 Agent 的用户 Skill 目录**

以 `sci-select` 为例，安装其他 Skill 时换成对应目录名。安装后，Skill 目录内应直接包含 `SKILL.md`。

Windows PowerShell：

```powershell
Copy-Item -Recurse "$env:USERPROFILE\xiaoyu-skill\skills\sci-select" "$env:USERPROFILE\.codex\skills\sci-select"
```

macOS / Linux：

```bash
mkdir -p ~/.codex/skills
cp -R ~/xiaoyu-skill/skills/sci-select ~/.codex/skills/
```

**3. 在对话中直接描述任务**

符合用途的 Skill 会按其触发规则自动启用，也可以在提示词中点名：

```text
使用 sci-select，根据这篇论文的标题和摘要给出候选期刊。
```

各目录内的 `README.md` 介绍具体用法，`SKILL.md` 定义执行流程、触发条件和交付要求。

## 支持的 Agent

Skill 采用 [Agent Skills 规范](https://agentskills.io)的 `SKILL.md` 格式，适用于所有读取该格式的宿主：

| Agent | 用户 Skill 目录 |
| --- | --- |
| Codex | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |
| 其他兼容宿主 | 见各宿主文档 |

注意：部分 Skill 依赖宿主能力（联网、shell、Python/R 运行时），见 [Skill 一览](#skill-一览)中的"环境要求"列；宿主不具备相应能力时，对应 Skill 可能无法发挥完整功能。

## 更新

在本地仓库中拉取最新版本，再重新复制已安装的 Skill 目录。

Windows PowerShell：

```powershell
git -C "$env:USERPROFILE\xiaoyu-skill" pull --ff-only
$source = "$env:USERPROFILE\xiaoyu-skill\skills\sci-select"
$target = "$env:USERPROFILE\.codex\skills\sci-select"
New-Item -ItemType Directory -Force $target | Out-Null
Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $target -Recurse -Force
```

macOS / Linux：

```bash
git -C ~/xiaoyu-skill pull --ff-only
mkdir -p ~/.codex/skills/sci-select
cp -R ~/xiaoyu-skill/skills/sci-select/. ~/.codex/skills/sci-select/
```

使用 Claude Code 时，把路径中的 `.codex` 换成 `.claude` 即可。

## 来源与合并基线

各 Skill 来自作者独立维护的原仓库（见 [Skill 一览](#skill-一览)），本仓库保留各目录内的原许可证与必要声明。首次合并的基线 commit 见 [docs/PROVENANCE.md](docs/PROVENANCE.md)。

## License

仓库采用 [MIT License](LICENSE)。各 Skill 目录同时保留了原项目的许可证和必要声明。
