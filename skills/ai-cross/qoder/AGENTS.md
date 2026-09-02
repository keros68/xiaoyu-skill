# ai-cross（Qoder 适配头）

你是 Qoder，不是 Claude Code。运行 ai-cross 多模型派发 skill 时，注意四点 Qoder 特有的调整：

1. **没有内部 subagent**。Claude Code 的 scout/worker/heavy/advisor 在这里不可用——所有派发一律走外部命令（`codex exec` / `claude -p` / `python ai-cross/references/cc_switch.py` / 裸 API `curl`）。路由表照用，只是低/中/高档由外部通道承担，`scout/worker/heavy` 只是档位语义的占位名。

2. **references/ 不会自动加载**。需要命令模板、盘点流程、安全规则、校验器时，用文件工具读取 `./ai-cross/references/` 下对应文件：`channels.md`（命令模板）、`setup.md`（盘点）、`security.md`（密钥铁律）、`cc_switch.py`（cc-switch 只读桥）、`verify_model.py`（模型真身校验）、`dispatch-design.md`。skill 本体在 `./ai-cross/SKILL.md`。

3. **交叉验证必须显式换厂商**。Qoder 底层是自动路由的多厂商混合（Claude/GPT/Gemini 等），路由不透明、可能撞同一厂商。所以交叉审查时，必须**显式派给一个明确不同厂商**的模型（例如派给 `codex`=OpenAI、或 GLM/DeepSeek 裸 API），**不能依赖 Qoder 自动路由**，也不能"再问一次自己"。

4. **派发命令的执行**：`python ai-cross/references/` 下的三个只读脚本（`cc_switch.py` / `verify_model.py` / `usage_probe.py`）Qoder 会自动跑；`claude -p` / `codex exec` / `curl`（联网/未知命令）可能触发 Qoder 的风险审批或 sandbox——首次会让你在 IDE 里点批准，放行即可（或切 Experts Mode 减少打断）。

现在请读取并遵循 `./ai-cross/SKILL.md`，按其中的路由三步走与执行闭环规则工作。
