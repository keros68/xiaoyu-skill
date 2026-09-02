# bench — 基准实验与审计脚本

配套公众号文章（测评方法论 / K3 三模型实测 / 订阅回本实测）的可复现材料。

## 结构

- `tasks*.py` — 任务定义与参考实现算出的 GT（内置自检断言，先跑它）
- `run*.py` — 执行基准（裸 API / CLI 两类通道）
- `analyze*.py` — 判分与汇总（绝不回退读思考草稿；撞 max_tokens 记截断作废）
- `probe_*.py` — 单点探针（thinking 截断、multihop 等）
- `rerun_*.py` — 修正轮重跑
- `results_*.csv` — 每次调用的判分明细（含完整原始回答摘录）
- `RESULTS-*.md` — 各轮实验结论与自我纠错记录
- `audit_subscription_value.py` — 订阅回本审计：聚合本机 claude/codex/kimi CLI 用量日志，按官方 API 牌价折算（只读、只输出聚合数字）

## 复现顺序

```bash
python tasks_depth.py      # GT 自检
python run_depth.py        # 跑基准（需各家 API/CLI 凭据，走环境变量）
python analyze_depth.py    # 判分
python audit_subscription_value.py   # 订阅审计（只依赖本机 CLI 日志）
```

密钥纪律：所有脚本不落盘、不回显任何凭据；audit 脚本绝不读取或输出对话内容。
