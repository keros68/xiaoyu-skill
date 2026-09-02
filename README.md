# xiaoyu-skill

面向科研工作的开源 Skill 合集，覆盖参考文献、期刊选择、论文格式、学术制图和多模型协作。

可以按需安装任意一个 Skill，也可以保留完整仓库，统一更新。

## Skills

| Skill | 用途 | 原项目 |
| --- | --- | --- |
| [`academic-reference-matcher`](skills/academic-reference-matcher/) | 为学术论述检索、核实和格式化参考文献 | [keros68/academic-reference-matcher](https://github.com/keros68/academic-reference-matcher) |
| [`sci-select`](skills/sci-select/) | SCI/SCIE/ESCI/SSCI 期刊查询、候选期刊发现和投稿前检查 | [keros68/sci-select](https://github.com/keros68/sci-select) |
| [`cugb-doctoral-thesis-format`](skills/cugb-doctoral-thesis-format/) | 中国地质大学（北京）博士论文 DOCX 格式预检 | [keros68/cugb-doctoral-thesis-format](https://github.com/keros68/cugb-doctoral-thesis-format) |
| [`abstract-fig`](skills/abstract-fig/) | 制作可编辑的 draw.io 论文图形摘要、概念图和技术路线图 | [keros68/abstract-fig](https://github.com/keros68/abstract-fig) |
| [`study-area-map`](skills/study-area-map/) | 使用 R 绘制论文研究区区位图和地形底图 | [keros68/study-area-map.skill](https://github.com/keros68/study-area-map.skill) |
| [`ai-cross`](skills/ai-cross/) | 多模型分工、分层派发和跨厂商交叉验证 | [keros68/ai-cross](https://github.com/keros68/ai-cross) |

`sci-select` 已集成原 `journal-fit` 的投稿前期刊定向审查能力。

## 安装

先克隆仓库，再将需要的 Skill 目录复制到 Codex 的用户 Skill 目录。以 `sci-select` 为例。

Windows PowerShell：

```powershell
git clone https://github.com/keros68/xiaoyu-skill.git "$env:USERPROFILE\xiaoyu-skill"
Copy-Item -Recurse "$env:USERPROFILE\xiaoyu-skill\skills\sci-select" "$env:USERPROFILE\.codex\skills\sci-select"
```

macOS 或 Linux：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/sci-select ~/.codex/skills/sci-select
```

安装其他 Skill 时，将示例中的 `sci-select` 换成对应目录名。安装后，Skill 目录内应直接包含 `SKILL.md`。

## 使用

在 Codex 中描述任务，符合用途的 Skill 会按其触发规则启用。也可以在提示词中直接指定 Skill，例如：

```text
使用 sci-select，根据这篇论文的标题和摘要给出候选期刊。
```

各目录的 `README.md` 介绍具体用法，`SKILL.md` 定义执行流程、触发条件和交付要求。

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

macOS 或 Linux：

```bash
git -C ~/xiaoyu-skill pull --ff-only
mkdir -p ~/.codex/skills/sci-select
cp -R ~/xiaoyu-skill/skills/sci-select/. ~/.codex/skills/sci-select/
```

## 合并基线

本仓库于 2026-09-02 从各原项目的 GitHub `main` 分支完成首次合并：

| Skill | Commit |
| --- | --- |
| `abstract-fig` | `75e955b49d3dfa5cc7f2e9ba43d0597e60554cc1` |
| `academic-reference-matcher` | `189a5ddbeaca8e1a594c28ac5d4c694741c01db9` |
| `ai-cross` | `c05c6ac42fa48ad083a6f25f0c68b721a3ab20f2` |
| `cugb-doctoral-thesis-format` | `2f89e6261075ae382324671309e76d42559e725c` |
| `sci-select` | `ad03233015af343ad3c013c9477cb314d69574dd` |
| `study-area-map` | `4179ef5115359d6f997362d9e34e27c803d8b598` |

## License

仓库采用 MIT License。各 skill 目录同时保留了原项目的许可证和必要声明。
