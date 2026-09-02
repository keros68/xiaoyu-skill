# xiaoyu-skill

一组面向科研写作、投稿、论文制图和 AI agent 协作的开源 skills。每个 skill 都是独立、可安装的目录；仓库根目录不是一个总入口 skill。

## Skills

| Skill | 用途 | 原项目 |
| --- | --- | --- |
| [`academic-reference-matcher`](skills/academic-reference-matcher/) | 为学术论述检索、核实和格式化参考文献 | [keros68/academic-reference-matcher](https://github.com/keros68/academic-reference-matcher) |
| [`sci-select`](skills/sci-select/) | SCI/SCIE/ESCI/SSCI 期刊查询、候选期刊发现和投稿前检查 | [keros68/sci-select](https://github.com/keros68/sci-select) |
| [`cugb-doctoral-thesis-format`](skills/cugb-doctoral-thesis-format/) | 中国地质大学（北京）博士论文 DOCX 格式预检 | [keros68/cugb-doctoral-thesis-format](https://github.com/keros68/cugb-doctoral-thesis-format) |
| [`abstract-fig`](skills/abstract-fig/) | 制作可编辑的 draw.io 论文图形摘要、概念图和技术路线图 | [keros68/abstract-fig](https://github.com/keros68/abstract-fig) |
| [`study-area-map`](skills/study-area-map/) | 使用 R 绘制论文研究区区位图和地形底图 | [keros68/study-area-map.skill](https://github.com/keros68/study-area-map.skill) |
| [`ai-cross`](skills/ai-cross/) | 多模型分工、分层派发和跨厂商交叉验证 | [keros68/ai-cross](https://github.com/keros68/ai-cross) |

`journal-fit` 不再单独收录；其投稿前期刊定向审查能力已经并入 `sci-select`。

## 安装

安装时选择需要的 skill 子目录，不要把仓库根目录当成一个 skill。目标目录应直接包含对应的 `SKILL.md`。

以 Codex 和 `sci-select` 为例：

```powershell
git clone https://github.com/keros68/xiaoyu-skill.git "$env:USERPROFILE\xiaoyu-skill"
Copy-Item -Recurse "$env:USERPROFILE\xiaoyu-skill\skills\sci-select" "$env:USERPROFILE\.codex\skills\sci-select"
```

macOS 或 Linux：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/sci-select ~/.codex/skills/sci-select
```

如需安装其他 skill，将示例中的 `sci-select` 换成表格里的目录名。各 skill 的依赖、触发方式和使用边界见其目录内的 `README.md` 与 `SKILL.md`。

## 合并基线

本仓库首次合并自各原项目 2026-09-02 的 GitHub `main` 分支：

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
