# 接入与盘点向导（探测先行，申报兜底）

面向不会安装配置的新人。逐步执行，每步失败就停下报错，不要跳步。

**"不盲扫本机" ≠ 什么都不看**：它指的是不读密钥文件、不凭猜测翻目录。第 1 步的四类只读探测是随附工具、安全边界明确（白名单见 `security.md`），**必须先跑**——新人答不上"我有哪些订阅"，探测就是替他回答这个问题的。盘点阶段只需读本文件；`channels.md` 的命令模板到逐项验证时才按通道查阅，不要预先全读。

## 第 0 步 — 识别宿主

判断当前跑在哪个 agent 里。**宿主自己不算外部通道。**

- 宿主是 **Claude Code**：内部 subagent 三档可用；claude CLI 仍可作 coding plan 载体（分支 B）。
- 宿主是 **Codex / WorkBuddy / Qoder / 其他**：**无内部通道**，全部走外部命令。盘点阶段第一个实际动作是**第 1 步的只读探测**（不是提问），不要尝试内部派发。

**壳 ≠ 模型**：zcode(ZCode)、Qoder 桌面、Hermes、OpenClaw、WorkBuddy 这类是 harness/壳，不是可派发的模型。派发目标永远是**模型**，经三种方式之一触达：①官方 CLI（claude/codex/gemini/qoder）②Anthropic/OpenAI 兼容端点（GLM/Kimi/DeepSeek）③按量 API。用户报"我有 zcode/z.ai"时，其底层模型是 GLM，走分支 B 直连智谱端点，**不需要装它的桌面，也不需要经过任何路由壳**。只有桌面 GUI、无 CLI 也无 API 的工具无法被任何方式派发（路由壳也救不了——它自己也得靠 API 触达模型）。

## 第 1 步 — 只读探测（先做，不等用户回答）

新人往往答不上"我有哪些订阅"，所以**探测先行、申报兜底**：先把下面四类只读探测跑完，拿到事实再提问。**绝不允许空着检测结果直接反问用户"你有哪些订阅"**——那是把盘点的工作推回给最回答不了它的人。

**这些动作是"探测"，不是"盲扫"，默认直接执行**：在同一条消息里告知用户"正在只读检测本机模型入口"即满足知情原则（白名单见 `security.md`），无需停下等许可。它们不登录、不发模型请求、不读密钥明文、零费用。

1. **CLI 存在检测**（只跑 `--version`，不存在就跳过，报错不算失败）：
   `claude --version`、`codex --version`、`kimi --version`、`pi --version`、`qoder --version`、`aichat --version`、`codebuddy --version`、`hermes --version`。kimi 在 Windows 装完可能不进 PATH，补试全路径 `~/.kimi-code/bin/kimi.exe`。
2. **cc-switch 只读桥**（`~/.cc-switch/cc-switch.db` 存在才跑）：
   ```
   python <本skill目录>/references/cc_switch.py list
   ```
   Windows 上若 `python` 不存在，改用 `py -3 <...>/cc_switch.py list`。**无 python / 读不到 / schema 对不上 → 跳过这项，不阻塞。**细节与铁律见下方专节。
3. **用量痕迹**（发现"装了但用户没说"的入口）：
   ```
   python <本skill目录>/references/usage_probe.py --days 30
   ```
4. **当前模型偏好**（只读配置里的模型字段，不读 key 字段）：
   `~/.claude/settings.json` 的 `model`、`~/.codex/config.toml` 的 `model` / `model_reasoning_effort`、`~/.kimi-code/config.toml` 的 `[models]` 段；codex 官方模型清单缓存 `~/.codex/models_cache.json`。**字段缺失时只记录版本与可用性，不推断。**

### cc-switch 只读桥：细节与铁律

很多多模型用户用 [cc-switch](https://github.com/farion1231/cc-switch) 管配置。它把用户**手动添加**的各 CLI 供应商存在 `~/.cc-switch/cc-switch.db`（SQLite）。注意：这是用户申报过的清单，不是探测结果——信任级别同申报，好处是免重输。

- **固化做法**：运行随附只读桥
  ```
  python <本skill目录>/references/cc_switch.py list
  ```
  Windows 上若 `python` 不存在，改用 `py -3 <...>/cc_switch.py list`。
  输出每个 provider 的 `app_type / name / category / endpoint / tier_models(档位→模型) / has_token`，**token 从不输出**。据此建 manifest 与厂商×档位矩阵。**无 python / 读不到 / schema 对不上 → 回退手动申报，不阻塞。**

- **派发时**用同一脚本的 exec 模式：
  ```
  python cc_switch.py exec --provider "Zhipu GLM" --tier sonnet --task "..."
  python cc_switch.py exec --provider "Zhipu GLM" --tier sonnet --task-file task.txt
  ```
  任务含引号/花括号/换行时**务必用 `--task-file`**（shell 会拆碎 `{}` 和转义引号，实测踩过）。token 只在脚本子进程内读取注入，**绝不进主 agent 上下文**。仅支持 `app_type=claude`（Anthropic 端点）；codex/gemini 官方订阅走各自 CLI。

- **实测边界（cc-switch v3.8+，2026-07-08）**：有保存 key 的 provider，token 明文存于 `settings_config.env.ANTHROPIC_AUTH_TOKEN`（cn_official 订阅模板 GLM/StepFun 与 custom 类讯飞均如此，cc-switch 不加密第三方 key）。空/陈旧条目无 token → 端点+模型仍可自动填，key 让用户补。
- **额外红利**：env 里的 `ANTHROPIC_DEFAULT_HAIKU/SONNET/OPUS_MODEL` 就是**用户配的当前档位→模型映射**，直接当该 provider 的 tier→model 表用，模型 ID 取实时值、免猜、免维护漂移。
- **铁律**：只读，绝不修改其 db；**绝不采用它的"切换"机制**（它靠把当前供应商写进 `~/.claude/settings.json` 来切换、一次只激活一个，正是要避开的全局污染）。我们的价值恰是把它存的多个供应商用**按进程环境变量并发跑起来**。提取到的 key 只在派发时按进程注入，manifest 只记"来源=cc-switch / 是否可自动提取"。
- 把读到的列表拿给用户勾选要纳入的，再写 manifest。

### usage_probe：用量痕迹的用法与信任边界

申报（用户说的）、配置（cc-switch/config.toml，用户配过的）之外的第三类：**使用痕迹**（实际发生过的调用）。运行随附只读桥：

```
python <本skill目录>/references/usage_probe.py --days 30
```

输出聚合 JSON：每个 (来源 CLI, 模型) 的调用次数与首末时间、已知 CLI 数据目录的存在性与最近活动。**只出元数据，对话内容一律不读不输出。**用法：

- **发现**：`installs` 里存在且近期活跃、但用户没申报过的 CLI → 提示用户确认是否纳入（**不自动纳入**，申报制不破）。
- **预填**：`usage` 里近期高频的模型 ID 就是"用户实际在用的"，直接当申报候选拿去勾选。
- **信任边界**：模型字段多为**请求值**，不代表服务端真身——第三方端点仍必须过 `verify_model.py`；日志只证明"用过"，不证明"现在可用"。

## 第 2 步 — 一次性确认（只问一次）

把探测结果摆成一张表，用当前宿主的交互提问机制**一次问完两件事**：

| 宿主 | 提问机制 |
|---|---|
| Claude Code | `AskUserQuestion`（支持多选） |
| Codex | `request_user_input`；不可用时退化为逐条文本提问 |
| 其他 | 逐条文本提问 |

**推荐提问模板**（按实际检测结果改写）：

> 我在你机器上只读检测到这些模型入口（没有读取或显示任何密钥）：
> - ✅ 已装：codex CLI vX.Y（当前模型 gpt-x）；cc-switch 有 N 个供应商（M 个已存 key）：Zhipu GLM、StepFun…
> - ❓ 已装但状态待确认（未登录 / 长期未用）：…
> - ❌ 未装：claude / kimi / aichat…
>
> ① 以上哪些要纳入盘点？（默认全选；用量痕迹新发现的入口单独列出、不自动纳入）
> ② 还有没有探测不到的入口？（网页版订阅、按量 API key——DeepSeek / OpenRouter / GLM Coding Plan 等）

**确认之后才有动作**：冒烟是真实的（订阅内）调用；代为安装 CLI、写配置、读含 key 的字段，都必须等用户点头。

### 兜底：探测全失败才退回纯申报

全新机器（无 python、无任何 CLI、无 cc-switch）时用下表逐条问：

> 请勾选你已有的模型入口（可多选）：
> ① Claude（Claude Code / Pro / Max 订阅）
> ② Codex（ChatGPT 订阅）
> ③ Gemini（⚠️ 独立 CLI 已下线，2026-07 核实；若未来恢复见 `channels.md`）
> ④ Qoder（CLI 与 IDE 共享 Credits，算一个源）
> ⑤ CodeBuddy / WorkBuddy（同账号通用，算一个源）
> ⑥ 智谱 GLM Coding Plan（订阅制 → 分支 B）
> ⑦ Kimi 会员 / Kimi Code（订阅制：装了 kimi CLI（OAuth）→ 分支 A；有控制台 API key → 分支 B）
> ⑧ 按量 API（DeepSeek / OpenRouter / 其他 → 分支 C）
> ⑨ 其他 agent 或模型（请说明名字）

## 第 3 步 — 逐项验证（只验证勾选项）

### 分支 A：官方 agent CLI

每项三小步：存在检测 → 登录 → 冒烟。

| CLI | 存在检测 | 冒烟（最便宜档） | 模型枚举 |
|---|---|---|---|
| claude | `claude --version` | `claude -p --model haiku "只回复OK"` | 不支持，用静态档位表 haiku<sonnet<opus |
| codex | `codex --version` | `codex exec -m gpt-5.6-luna -c model_reasoning_effort="low" -s read-only --skip-git-repo-check "reply OK"` | **本地枚举**：读 `~/.codex/models_cache.json`（CLI 缓存的官方清单，含描述/efforts/priority），别手抄 |
| kimi | `kimi --version`（Windows 装完不进 PATH，全路径 `~/.kimi-code/bin/kimi.exe`） | `kimi -p "只回复OK" -m kimi-code/kimi-for-coding-highspeed` | **本地枚举**：读 `~/.kimi-code/config.toml` 的 `[models]` 段（含上下文/effort），别手抄 |
| gemini | ⚠️ 独立 CLI 已下线（2026-07 核实，见 `channels.md`），跳过验证 | 若未来恢复：先 `gemini --version` 冒烟确认存在再用 | 不支持，静态表 |
| qoder | `qoder --version` | `qoder -p "只回复OK"`（参数以本地 `qoder --help` 为准） | 静态，`--model` 选档 |
| codebuddy | `codebuddy --version` | 命令形态以本地 `codebuddy --help` 为准 | 静态表 |
| hermes | `hermes --version` | `hermes chat -q "只回复OK" -Q` | 以其配置为准，额度归属问用户 |

- **档位与当前偏好**：官方 CLI 不支持枚举，也不需要——档位少且顺序由厂商定义，用静态表。用户在 TUI `/model` 里选的型号**会落盘**：读 `~/.claude/settings.json` 的 `model`、`~/.codex/config.toml` 的 `model` / `model_reasoning_effort`，作为"用户当前偏好"记入 manifest（读文件即可，无需进 TUI）。**字段缺失时只记录版本与可用性，不推断偏好模型。**
- **CLI 不存在**：按下方附录给出安装命令，征得同意后代为安装；装不了则记"不可用 + 原因"。
- **版本**：记录版本号，**不自动升级**（可能有破坏性变更）；仅冒烟失败且疑似过旧时才建议升级。
- **认证错误**：agent 无法代替用户完成 OAuth 登录——提示用户在自己终端运行登录命令（`claude` 首次启动 / `codex login` / `gemini` 首次启动），完成后回来重测。
- **参数报错**（`unrecognized arguments` 等）：跑 `<cli> --help` 看当前参数，去掉非必要项用最小命令重试，并提示更新 `channels.md`。

### 分支 B：coding plan（GLM / Kimi 等订阅）

载体是 claude CLI + 按进程环境变量。**不要用 aichat 接 coding plan**——多数条款限定其只能用于 coding agent，且网关常拒非 agent 流量。

1. 确认本机有 claude CLI，没有则先装（**免费；装了不等于要买 Claude 订阅**，第三方端点用 env 覆写认证）。
2. 引导用户到对应控制台创建 API key（智谱：开放平台 → 个人编程套餐 → 套餐概览建 key；Kimi：Kimi Code 控制台）。此 key 与 zcode/ZCode 桌面用的是同一个、同一份订阅额度池，直连端点即可，无需装桌面。
3. key 存为用户级环境变量，不落明文：Windows `setx GLM_CODING_KEY <key>`（Kimi 同理），类 Unix 写入 shell profile。**若 key 已在 cc-switch 里，直接用 `cc_switch.py exec`，跳过本步。**
4. 用 `channels.md` 的 coding plan 模板冒烟。
5. 记入 manifest，额度归属为对应 coding plan，算独立源。

### 分支 C：按量 API（aichat，最后的兜底）

1. **检测**：`aichat --version`，已装跳到第 3 小步。
2. **代为安装**：Windows `winget install sigoden.aichat`（失败试 `scoop install aichat`）；macOS `brew install aichat`；Linux 从 https://github.com/sigoden/aichat/releases 下载二进制入 PATH。全部失败才让用户手动装并停在这步。
3. **收集三项**：先选预设，预设内只需粘贴 API key：

| 预设 | api_base | 默认模型 ID |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 智谱按量 API（非 Coding Plan） | `https://open.bigmodel.cn/api/paas/v4` | 以官网当前型号为准 |
| OpenRouter | `https://openrouter.ai/api/v1` | 用户指定 |
| 自定义 | 用户填 URL | 用户填模型 ID |

4. **写配置**：Windows `%APPDATA%\aichat\config.yaml`；macOS `~/Library/Application Support/aichat/config.yaml`；Linux `~/.config/aichat/config.yaml`。**已存在则先读再追加 client，绝不整体覆盖**：

```yaml
model: <name>:<model_id>
clients:
  - type: openai-compatible
    name: <name>
    api_base: <api_base>
    api_key: <api_key>
```

5. **冒烟**：`aichat -m <name>:<model_id> "只回复两个字：正常"`。已配置的全部模型可用 `aichat --list-models` 枚举。

## 第 4 步 — 写 manifest

写入本 skill 目录下 `manifest.md`，带盘点日期。**复制同目录现成 `manifest.md` 的表头填写**；若不存在，用此最小模板：

```markdown
# 能力清单 manifest
盘点日期:YYYY-MM-DD ｜ 宿主:<宿主名>

| 通道 | 模型/档位 | 强项 | 相对成本 | 额度归属 | 冒烟结果 |
|---|---|---|---|---|---|
| codex CLI | gpt-5.4-mini(low) | 快速琐事 | 低 | Codex 订阅 | ✅ YYYY-MM-DD |
| cc_switch→Zhipu GLM | glm-5-turbo / glm-5.2 / glm-5.2[1m] | 实现/分析 | 低/中/高 | GLM Coding Plan | ✅ YYYY-MM-DD |
| gemini | — | — | — | — | ❌ CLI 未安装 |

## 厂商 × 档位矩阵(路由查这张表)
| 厂商 | 低档 | 中档 | 高档 | 来源 |
|---|---|---|---|---|
| OpenAI(codex) | gpt-5.4-mini | gpt-5.4 | gpt-5.5 | 读:~/.codex/models_cache.json |
| 智谱(cc_switch) | glm-5-turbo | glm-5.2 | glm-5.2[1m] | 读:cc_switch.py list |
| <无事实源的厂商> | … | … | … | 文档(YYYY-MM-DD) / 申报(YYYY-MM-DD) |

## 源与强度解锁
独立厂商数:N → 分层省钱 ✅ ｜ 交叉验证(≥2 厂商) ✅/❌ ｜ 全力 ✅/❌
```

- 验证失败的勾选项也记入（标"不可用 + 原因"），避免下次重复试错。
- 末尾写明独立**厂商**数及解锁的强度。源仅用于计费提示与独立性判断，不作强度门槛。
- **「来源」列必填，三选一**：`读:<命令或路径>`（有本地事实源，派发前实读）/ `文档(日期)`（抄自厂商文档）/ `申报(日期)`（用户口述）。**标了 `读:` 的行不得静默用表里的值**——读失败时可以拿它顶上，但必须当场告知用户"未实读、用的是 N 天前的记录值"（规则见 `channels.md`「不得静默降级用旧值」）。这一列存在的意义是：**让"这个 ID 是哪来的"在路由时可见**，而不是等静默降级发生后再去追。
- **聚合型订阅**（一份额度里含多家权重，如千问 Token Plan 含 GLM/DeepSeek/Kimi/MiniMax）：厂商列按**权重厂商**分行填，额度归属列填**聚合平台名**。这类源的权重独立性成立（可交叉验证）、计费独立性不成立（熔断一起没），两者不能合并成一列——合了会误判为"有 N 个独立源"。

### ⛔ 不要给通道打「自算可靠性」评级（实测：这个抽象是错的）

曾计划用一道递推题给每个通道打 `自算 k/n` 分。**实测证明该评级不稳定、会误导**：

| 同一道 51 步递推题 | GLM | StepFun |
|---|---|---|
| 硬基准（n=3） | 3/3 | 1/3 |
| 独立探针（n=3） | **1/3** | **2/3** |
| 合计 | 4/6 | 3/6 |

**完全反转，都接近抛硬币。** 对照 `tools` 字段：答对的那几次模型**写了代码去跑**，答错的那几次它**心算**了。

**「自算准不准」不是厂商属性，是「它这次选没选择写代码」的随机结果。** 而探针里那句「你可以心算、手算或写代码，方式不限」正是邀请失败的元凶。

**→ 正确做法（见 SKILL.md 铁律）**：不评级，而是在**每次派发精确计算任务时**，prompt 明确命令「写代码并执行，给出运行结果」；模型不能执行代码时，**编排者独立核验**。

manifest 只记**可复现的具体缺陷**（如"肉眼计数 33%"、"统计推导方法标注错误"），不记自算评分。

**判定"它不会算"之前，先排除传参问题**：多行 prompt 经 argv 传给 `codex exec` 会在首个换行截断（见 `channels.md`）。**先确认它收到了完整题目。**

## 第 5 步 — 报告（含期望校准）

告知用户：清单写在哪、有几个厂商、解锁了什么强度、路由表中哪些任务会走哪些通道、哪些通道未冒烟需首次派发前先测。

**必须包含「组合解锁表」——按用户实际组合如实校准期望，不吹不瞒**：

| 你的组合 | 能做什么 | 做不了什么 | 最便宜的下一步 |
|---|---|---|---|
| 仅 Claude Code（单厂商） | 内部三档分层（scout/worker/heavy，几乎免费）、留痕、闭环 | **跨厂商交叉验证**（本 skill 核心价值）——同厂商复查只算"复核" | 接入任一第二厂商即解锁：GLM/Kimi coding plan（订阅制，走分支 B）或 DeepSeek 等按量 API（充几元即可，走分支 C），以各家官网当前价为准 |
| 仅 Codex（单厂商） | 外部分层（codex 三档）、留痕、闭环 | 同上；且无内部 subagent，分层全走外部 | 同上 |
| Claude Code + Codex | **完整能力**：交叉验证、双保险、分层、熔断主备 | — | 可选：再加一家中文厂商做三方面板 |
| 任一宿主 + ≥1 个 coding plan/按量 key | 交叉验证（宿主厂商 × 第三方厂商）、额度分摊 | — | — |

单厂商用户要**明确告知**："当前组合只有分层收益，交叉验证要等第二家厂商接入"——这不是 skill 故障，是能力门槛（SKILL.md「派发单元与门槛」）。

## 第 6 步 — 首次派发演示（可选，建议做）

盘点报告后问用户一句："要不要跑一次演示派发，直观看看交叉验证长什么样？（约一次冷调用 × 2 的成本，全程只读、不碰你的项目文件）"。同意后执行：

1. **选通道**：从 manifest 挑两个**不同厂商**、已冒烟、最便宜档的通道。只有一家厂商时退化为分层演示（低档执行 + 编排者核验），并**明说这不是交叉验证**。
2. **派发**：用 SKILL.md 的冻结盲验模板 + 下面这段内置演示代码（**不读用户项目文件**——演示的安全边界就是它自己），并行发给两路，prompt 为中性审查请求：「请独立审查这段代码，列出你发现的问题、依据与不确定处。不要猜测提供者想听什么。」
3. **留痕**：两路原始输出存 `.dispatch/`（顺带演示留痕机制，`.gitignore` 一并建好）。
4. **核对与汇总**：对照下方「已知缺陷答案」（⚠️ 答案绝不进派发 prompt），给用户三样东西：**共识**（两家都抓到的）、**分歧**（只有一家抓到的/意见相反的）、**账单**（每路 token 与耗时）。两家高度一致也是合法结果，如实展示即可。

演示代码（含植入缺陷，自包含）：

```python
def summarize_scores(scores, top_n=3):
    """返回全体平均分与前 top_n 名。scores: {姓名: [各次得分]}"""
    avgs = {}
    for name, vals in scores.items():
        avgs[name] = sum(vals) / len(vals)
    top = sorted(avgs, key=avgs.get)[:top_n]
    total_avg = sum(avgs.values()) / len(scores)
    return {"total": round(total_avg), "top": top}
```

已知缺陷答案（仅编排者核对用）：① `vals` 为空列表时 `ZeroDivisionError`；② `sorted` 默认升序，`[:top_n]` 取到的是**倒数** top_n，应 `reverse=True`；③ `scores` 为空 dict 时除零；④ `total_avg` 是"各人平均的平均"，人数不等权时 ≠ 全体总平均（判断型缺陷，规格歧义）；⑤ `round` 取整丢精度（弱缺陷，规格未明）。①②③是硬伤，④⑤是判断题——通常正好能引出两家的分歧，这就是演示想让用户看到的东西。

---

## 附录：常见 CLI 安装命令

| CLI | Windows | macOS | Linux |
|---|---|---|---|
| claude | `npm i -g @anthropic-ai/claude-code` | 同左 | 同左 |
| codex | `npm i -g @openai/codex` | 同左 | 同左 |
| gemini | ⚠️ 独立 CLI 已下线（2026-07 核实，见 `channels.md`），不建议安装；若未来恢复再执行 `npm i -g @google/gemini-cli` | — | — |
| aichat | `winget install sigoden.aichat`（或 `scoop install aichat`） | `brew install aichat` | [releases](https://github.com/sigoden/aichat/releases) 下载二进制入 PATH |

以上为通用形态，**以各家官方文档当前值为准**；安装前先跑 `<cli> --version` 确认是否已装。装完让用户自行完成 OAuth 登录（agent 代替不了）。
