<div align="center">

简体中文 | [English](README.en.md)

# xiaoyu-skill

科研用 Agent Skill 合集：文献引用、期刊选刊、论文格式、学术制图、多模型协作。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Skills](https://img.shields.io/badge/skills-6-blueviolet)
[![Tests](https://github.com/keros68/xiaoyu-skill/actions/workflows/test.yml/badge.svg)](https://github.com/keros68/xiaoyu-skill/actions/workflows/test.yml)

</div>

每个 Skill 是一个独立目录，`SKILL.md` 定义触发条件、流程和交付要求。Agent 按任务描述自动匹配，也可单独安装任意一个。

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
| 学术制图 | [`study-area-map`](skills/study-area-map/) | 研究区区位图、地形晕渲底图、土地利用与采样点等专题图层、多面板地图组织 | R（ggplot2 + sf + terra） | [keros68/study-area-map.skill](https://github.com/keros68/study-area-map.skill) |
| 多模型协作 | [`ai-cross`](skills/ai-cross/) | 多模型分工派发、分层执行与跨厂商交叉验证 | 宿主需支持 shell；交叉验证需两家以上厂商的模型 | — |

## 快速开始

任选一种安装方式。同一个 Skill 只装一份，否则宿主会加载两次。

**方式一：skills.sh（推荐）**

需要 Node.js。以 `sci-select` 为例，`-g` 装到用户目录，去掉则只装进当前项目：

```bash
npx skills add keros68/xiaoyu-skill --skill sci-select -g
```

用 `-a claude-code -a codex` 指定 Agent，`--list` 列出全部 Skill。

**方式二：交给 Agent 安装**

把下面这段发给 Agent，`<skill 名>` 换成要装的 Skill：

```text
用 skills.sh 安装 keros68/xiaoyu-skill 里的 <skill 名>：运行
npx skills add keros68/xiaoyu-skill --skill <skill 名> -g -a <你自己对应的 agent 名，如 claude-code、codex、kimi-code-cli、pi>
不要手动复制文件。装完读一遍该 Skill 目录里的 README.md，告诉我是否需要新开会话，以及第一次使用要说的话。
```

**方式三：克隆后复制**

Windows PowerShell：

```powershell
git clone https://github.com/keros68/xiaoyu-skill.git "$env:USERPROFILE\xiaoyu-skill"
Copy-Item -Recurse "$env:USERPROFILE\xiaoyu-skill\skills\sci-select" "$env:USERPROFILE\.codex\skills\sci-select"
```

macOS / Linux：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
mkdir -p ~/.codex/skills
cp -R ~/xiaoyu-skill/skills/sci-select ~/.codex/skills/
```

Skill 目录下应直接是 `SKILL.md`。装好后新开会话，直接描述任务即可，也可点名调用：

```text
使用 sci-select，根据这篇论文的标题和摘要给出候选期刊。
```

## 支持的 Agent

采用 [Agent Skills 规范](https://agentskills.io)，兼容读取 `SKILL.md` 的宿主：

| Agent | 用户 Skill 目录 |
| --- | --- |
| Codex | `~/.codex/skills/` |
| Claude Code | `~/.claude/skills/` |
| 其他兼容宿主 | 见各宿主文档 |

部分 Skill 需要联网、shell 或 Python/R，见上表"环境要求"列。

## 更新

用 skills.sh 安装的：

```bash
npx skills update -g
```

克隆安装的：拉取仓库后重新复制 Skill 目录。

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

Claude Code 把路径中的 `.codex` 换成 `.claude`。

## 来源与合并基线

各 Skill 原为独立仓库（见上表），合并基线 commit 见 [docs/PROVENANCE.md](docs/PROVENANCE.md)。

## License

[MIT License](LICENSE)。各 Skill 目录保留原项目的许可证和声明。
