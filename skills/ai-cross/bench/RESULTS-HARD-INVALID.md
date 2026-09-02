# 高难度基准（2026-07-08）—— codex 臂结果作废,原因记录

> **【最终更正】根因不是环境污染,是 runner 的传参 bug。**
>
> 多行 prompt 经 **argv** 传给 `codex exec` 时,在**第一个换行处被截断**(Windows)。
> codex 只收到规格的第一行,于是**完全正确地**回答"你这条消息里算法正文没有贴出来"。
>
> 决定性证据(dump 出 codex 的实际回复):
> > "你这条消息里的算法正文似乎没有贴出来,可能需要从仓库上下文补齐。"
> > "你这条消息里算法说明没有贴出来,**冒号后是空的**。"
>
> 这解释了为什么**单行 prompt 的简单基准全 100%,多行规格的高难度基准全 0%**。
>
> **修复**:改走 stdin(`codex exec ... -`,`subprocess.run(cmd, input=prompt)`)。修复后立即验证:
> `h-checksum × codex-high` ✅、`h-recur × codex-low` ✅(A=887 B=270)、`h-interval × codex-low` ✅ —— 三个此前 5/5 失败的格子全绿。
>
> 下文关于 superpowers / AGENTS.md 的因果分析**是错的**(它们确实被加载,但不是失败原因)。
> 移除 superpowers 与 AGENTS.md 后重测,两个格子**依然失败**——那才逼出真正的根因。
>
> **教训:判定模型失败前,先 dump 出它实际收到的输入。** 我先怀疑了仪器(对),
> 又怀疑了环境(错),唯独最后才去看"它到底收到了什么"——那本该是第一步。

## 结论先行（原始记录，已被上方更正推翻）

**这一轮基准的 codex 三臂(codex-low / codex-advisor / codex-high)全部 0%,但这不是模型能力,是环境污染。数据作废,不得引用。**

GLM/StepFun 臂的数字同样受同类污染影响,只是没被打穿。

## 表面数据(仅存档,不可引用)

```
task         arm                正确率     in中位   冷fresh   热fresh    out     秒    工具
h-interval   codex-low           0%    90026    19878    43520   1985   108     6
h-interval   codex-advisor       0%   137353    63086    55734   2233   166     9
h-interval   codex-high          0%   260024        0    40888   9064   280    14   ← 2/3 超时
h-interval   glm-low           100%    29573    21701     3205    910    44     0
h-interval   step-low          100%    62521    30444    17648   1999    30     1
h-checksum   codex-*             0%      ...                                          ← 全"未找到代码起点"
h-checksum   step-low          100%    30325    20345      116    326     8     0
h-recur      codex-*             0%      ...                                          ← 全"未找到 JSON"
h-recur      glm-low            33%   118453    28789     3371   2872    73     3
h-recur      step-low           67%   161127    67708     4981   7185    70     4
h-ambig      codex-*             0%      ...
h-ambig      glm-low           100%    29423    28719     3182    495    30     0
h-ambig      step-low          100%    31946    30494    13744    786    15     0
```

## 根因:外派继承了目标 CLI 的人格

`codex exec` **不是裸模型**。本机实测它启动时加载:

- **44 个 skill**,含整套 superpowers:`test-driven-development`、`verification-before-completion`、`systematic-debugging`、`using-superpowers`(强制"回应前必先调用 skill")
- 一份全局 `~/.codex/AGENTS.md`

### 因果链(逐条对上)

| 观察到的失败 | 直接来源 |
|---|---|
| h-recur:不给答案,改列"如果你要,我可以继续帮你:1.计算前若干项 2.推导通项公式 3.求某个指定的 f(n)" | `AGENTS.md`:"If multiple interpretations would lead to meaningfully different changes, **ask or present the options**" |
| 明确写了"不要执行任何命令",仍跑 6–16 轮工具调用 | superpowers 的 TDD / verification-before-completion |
| h-checksum:最终消息是验证总结,代码从未出现在任何 agent_message 里 | 同上——它把代码写进 shell 命令去验证了 |

### 决定性反证

同一道递推题,**换成"编码任务"框架**问 codex-low(最便宜档):

```
{"A":887,"B":270}    ← 与 ground truth 完全一致,一次答对
```

**模型完全会算。** 失败的是任务措辞与它被灌输的人格之间的冲突。

## 这一轮我修掉的仪器 bug(修完仍然 0%,才发现根因在环境)

1. **提取器把中文解释当代码 `exec()`** → `SyntaxError: invalid character '，'`。改为**渐进式编译**:从末尾往回缩,找能编译且定义了目标函数的最长前缀。
2. **只取 `-o` 的最终消息** → codex 做完工具调用后最终消息是总结。改为从 JSONL 事件流取 `agent_message`,并回退扫描 `command_execution` 的命令内容。
3. **任务措辞诱导对话模式** → 中立化("方式不限,但最终回复最后一行必须只有那行 JSON")。
4. verifier 自检补了三种真实假阴性场景:代码后跟中文解释、前后都有散文+围栏、纯散文无代码。

**修完前三条,codex 仍 0%。** 这才逼出根因:不是解析,是环境。

## 教训(比结果值钱)

1. **跨 CLI 的"模型对比",实际是"被配置过的 agent 对比"。** 要做严格模型对比,必须控制环境(干净 `CODEX_HOME`、停用 skills),否则结论无效。
2. **20k–30k 的固定上下文足迹,大头是用户自己装的 skills。** 装得越多,每次外派越贵。
3. **派发时绝不能依赖"只输出 X"的格式约束**——目标 agent 的全局指令会压过你的任务指令。要么给分隔符取最后一次出现,要么宽松解析。**判定失败前先排除解析问题。**
4. 讽刺的是,污染源之一正是**我们自己的 `model-dispatch` skill**(它也装在 `~/.codex/skills/`),以及用户精心写的工程规范 AGENTS.md——**它们都在正确地做自己该做的事**,只是不该出现在被测对象体内。

## 重跑前提

- [ ] 干净 `CODEX_HOME`(仅带 `auth.json`),且跳过首次运行引导(直接复制 CODEX_HOME 会触发 onboarding 挂起,需要额外解决)
- [ ] 或改用 `-p/--profile` 叠加一份精简 profile
- [ ] `claude -p` 侧同样需要控制(`CLAUDE_CONFIG_DIR` 指向干净目录)
- [ ] codex-high 的 timeout 需 ≥ 420s(本轮 280s 触发 2 次超时)
