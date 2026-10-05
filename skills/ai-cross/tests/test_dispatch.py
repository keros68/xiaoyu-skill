# dispatch.py 单元测试。纯标准库,各通道的输出用真机抓到的形状伪造,不跑任何 CLI、不发网络请求。
# 跑法: python -m unittest discover -s tests  (在 skill 目录下)
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references"))
import dispatch
import inventory
from test_inventory import Base

SECRET_ENV = "env-SECRET-NEVER-WRITTEN"


def jl(*events):
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n"


def pi_out(text="发现两处问题", served=None, stop="stop", thinking_only=False, model="glm-5.3"):
    content = [{"type": "thinking", "thinking": "草稿里的答案"}]
    if not thinking_only:
        content.append({"type": "text", "text": text})
    msg = {"role": "assistant", "content": content, "provider": "zai-coding-cn", "model": model,
           "usage": {"input": 508, "output": 9, "cacheRead": 3}, "stopReason": stop}
    if served:
        msg["responseModel"] = served
    if stop == "error":
        msg["errorMessage"] = "403 AccessDenied.Unpurchased"
    return jl({"type": "agent_start"}, {"type": "message_end", "message": {"role": "user", "content": []}},
              {"type": "message_end", "message": msg}, {"type": "agent_settled"})


CODEX_OUT = jl({"type": "thread.started", "thread_id": "t"},
               {"type": "item.completed", "item": {"type": "agent_message", "text": "空列表会除零"}},
               {"type": "item.completed", "item": {"type": "agent_message", "text": ""}},
               {"type": "turn.completed", "usage": {"input_tokens": 77438, "cached_input_tokens": 57600, "output_tokens": 35}})
CLAUDE_OUT = json.dumps({"is_error": False, "result": "没有发现问题", "usage": {
    "input_tokens": 10, "cache_creation_input_tokens": 2285, "cache_read_input_tokens": 4286, "output_tokens": 119}})


class DBase(Base):
    def setUp(self):
        super().setUp()
        self.save()
        self.project = self.home / "proj"
        self.project.mkdir()
        (self.project / "AGENTS.md").write_text("我方结论：这段代码没问题", encoding="utf-8")
        self.material = self.home / "avg.py"
        self.material.write_text("def average(nums):\n    return sum(nums) / len(nums)\n", encoding="utf-8")
        self.calls = []

    def fake(self, outputs):
        """按命令里出现的关键字返回伪造输出;记录每次调用的 (cmd, cwd, stdin)。"""
        def run_process(cmd, cwd, timeout, stdin_text=None):
            self.calls.append((cmd, cwd, stdin_text))
            for key, (code, out, err) in outputs.items():
                if any(key in str(part) for part in cmd):
                    return code, out, err, None
            return 0, "", "", None
        return mock.patch.object(dispatch, "run_process", run_process)

    def review(self, outputs=None, **over):
        args = dict(host="claude-code", file=[str(self.material)], text_file=None, kind="code", author=None,
                    n=None, entry=None, tier=None, thinking="high", project=str(self.project), timeout=5,
                    json=False, go=False)
        args.update(over)
        with self.fake(outputs or {}):
            return self.call(dispatch.cmd_review, **args)

    def traces(self):
        return sorted((self.project / ".dispatch").glob("*.md"))


class TestReview(DBase):
    def test_without_go_sends_nothing(self):
        code, out, _ = self.review()
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [])
        self.assertIn("路由决策行", out)
        self.assertIn("pi:zai-coding-cn / glm-5.3（Zhipu）", out)
        self.assertIn("尚未发送", out)
        self.assertFalse((self.project / ".dispatch").exists())

    def test_go_runs_blind_and_leaves_trace(self):
        code, out, _ = self.review({"--provider": (0, pi_out(), "")}, go=True)
        self.assertEqual(code, 0)
        cmd, cwd, stdin = self.calls[0]
        # 盲审目录在数据目录的 scratch 下,不在项目里;材料走 stdin
        self.assertTrue(Path(cwd).is_relative_to(self.home / "data" / "scratch"))
        self.assertFalse(Path(cwd).exists())                       # 用完即删
        self.assertIn("def average", stdin)
        self.assertNotIn("我方结论", stdin)                        # 项目里的结论不进 prompt
        for flag in ("--no-tools", "--no-context-files", "--no-extensions"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--thinking") + 1], "high")
        self.assertIn("发现两处问题", out)
        self.assertIn("本次派发小结", out)
        trace = self.traces()[0].read_text(encoding="utf-8")
        for needle in ('schema: "aicross-dispatch/1"', 'visibility: "盲"', 'isolation: "完整"', 'status: "ok"',
                       "tokens_in: 508", "## 任务全文", "def average", "## 原始输出", "发现两处问题"):
            self.assertIn(needle, trace)
        self.assertNotIn("草稿里的答案", trace)                    # 思考草稿不当答案
        self.assertEqual((self.project / ".dispatch" / ".gitignore").read_text(encoding="utf-8"), "*\n")
        smoke = {e["id"]: e["smoke"]["status"] for e in self.manifest()["entries"]}
        self.assertEqual(smoke["pi-zai-coding-cn.zhipu"], "ok")    # 成功的派发顺带刷新冒烟

    def test_two_vendors_and_partial_failure(self):
        outputs = {"--provider": (0, pi_out(), ""), "exec": (0, CODEX_OUT.replace("空列表会除零", ""), "boom")}
        code, out, _ = self.review(outputs, go=True, n=2)
        self.assertEqual(code, 0)                                  # 一路成功即 0
        self.assertIn("状态 error", out)
        self.assertIn("只算第二意见", out)
        self.assertEqual(len(self.traces()), 2)                    # 失败的一路也留痕

    def test_all_failed_exits_1(self):
        code, out, _ = self.review({"--provider": (1, "", "network down")}, go=True)
        self.assertEqual(code, 1)
        self.assertIn("没有可用的结果", out)

    def test_named_entries_same_vendor_flagged(self):
        code, out, _ = self.review(entry=["codex.openai"])
        self.assertIn("codex / gpt-6.1-sol（OpenAI）", out)
        self.assertIn("用户点名", out)

    def test_no_material_and_no_reviewer(self):
        self.assertEqual(self.review(file=None)[0], 2)
        self.assertEqual(self.review(file=[str(self.home / "nope.py")])[0], 2)
        self.save({"entries": [{"channel": "claude", "tiers": {"low": "haiku"}}]}, replace=True)
        self.assertEqual(self.review()[0], 1)                      # 只有宿主同厂商,没人可派

    def test_trace_never_contains_environment_values(self):
        with mock.patch.dict(os.environ, {"GLM_CODING_KEY": SECRET_ENV}):
            self.review({"--provider": (0, pi_out(), "")}, go=True)
        for path in (self.project / ".dispatch").iterdir():
            self.assertNotIn(SECRET_ENV, path.read_text(encoding="utf-8"))


class TestChannels(DBase):
    def pick(self, entry, tier="high"):
        return inventory.describe(inventory.find_entry(self.manifest(), entry), tier)

    def run_one(self, entry, output, thinking="high", prompt="材料"):
        with self.fake({"": output}):
            return dispatch.call(self.pick(entry), prompt, str(self.home), 5, thinking, str(self.home / "p.txt"))

    def test_codex_takes_last_non_empty_message(self):
        r = self.run_one("codex.openai", (0, CODEX_OUT, ""), thinking="mid")
        self.assertEqual((r["status"], r["answer"], r["tokens_in"], r["cache_read"]), ("ok", "空列表会除零", 77438, 57600))
        cmd = self.calls[0][0]
        self.assertIn('model_reasoning_effort="medium"', cmd)
        self.assertEqual(cmd[cmd.index("-s") + 1], "read-only")
        self.assertEqual(cmd[-1], "-")                             # prompt 走 stdin
        two = jl({"type": "item.completed", "item": {"type": "agent_message", "text": "1. 排序方向反了"}},
                 {"type": "item.completed", "item": {"type": "agent_message", "text": "审查已完成。"}})
        r = self.run_one("codex.openai", (0, two, ""))
        self.assertEqual(r["answer"], "1. 排序方向反了\n\n审查已完成。")   # 正文在前一条时不能只留收尾那句

    def test_claude_blind_flags_and_error_masquerade(self):
        r = self.run_one("claude.anthropic", (0, CLAUDE_OUT, ""))
        self.assertEqual((r["status"], r["answer"], r["tokens_in"]), ("ok", "没有发现问题", 6581))
        cmd = self.calls[0][0]
        self.assertIn("--restricted", cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        bad = json.dumps({"is_error": True, "api_error_status": 529, "result": "API Error: overloaded"})
        r = self.run_one("claude.anthropic", (0, bad, ""))
        self.assertEqual((r["status"], r["answer"]), ("error", ""))  # exit 0 也不把错误当回答

    def test_pi_rejects_thinking_only_and_reports_errors(self):
        self.assertEqual(self.run_one("pi-zai-coding-cn.zhipu", (0, pi_out(thinking_only=True), ""))["status"], "error")
        r = self.run_one("pi-zai-coding-cn.zhipu", (0, pi_out(stop="error"), ""))
        self.assertIn("Unpurchased", r["error"])

    def test_pi_identity_mismatch_voids_the_answer(self):
        r = self.run_one("pi-zai-coding-cn.zhipu", (0, pi_out(served="glm-4.7"), ""))
        self.assertEqual(r["status"], "identity_mismatch")
        self.assertEqual(self.run_one("pi-zai-coding-cn.zhipu", (0, pi_out(served="GLM-5.3"), ""))["status"], "ok")
        self.assertEqual(dispatch.norm_model("GLM-5.3-Flash[1M]"), "glm-5.3-flash")

    def test_cc_switch_goes_through_bridge(self):
        r = self.run_one("cc-switch-deepseek.deepseek", (0, "看起来没问题", "[usage] input=120 fresh=20 cache_create=0 cache_read=100 output=7\n"))
        self.assertEqual((r["status"], r["tokens_in"], r["cache_read"], r["tokens_out"]), ("ok", 120, 100, 7))
        cmd = self.calls[0][0]
        self.assertTrue(cmd[1].endswith("cc_switch.py"))
        self.assertEqual(cmd[cmd.index("--provider") + 1], "DeepSeek")
        self.assertIn("--task-file", cmd)                          # 材料不进命令行
        r = self.run_one("cc-switch-deepseek.deepseek", (8, "", "[API 错误] status=529"))
        self.assertEqual(r["status"], "error")

    def test_agy_empty_response_is_failure(self):
        agy = inventory.describe({"id": "agy.google", "channel": "agy", "kind": "cli", "vendor": "Google",
                                  "billing": "subscription", "tiers": {"high": "gemini-3.8-flash-high"}}, "high")
        ok = jl({"event": "init"}, {"event": "result", "result": {"status": "SUCCESS", "response": "有除零风险\n",
                                                               "usage": {"input_tokens": 11681, "output_tokens": 5}}})
        empty = jl({"event": "result", "result": {"status": "SUCCESS", "response": "", "usage": {}}})
        with self.fake({"": (0, ok, "")}):
            r = dispatch.call(agy, "材料", str(self.home), 120, "high", "p")
        self.assertEqual((r["status"], r["tokens_in"]), ("ok", 11681))
        self.assertEqual(json.loads(self.calls[0][2])["message"]["content"], "材料")   # stdin 是一行 NDJSON
        with self.fake({"": (0, empty, "")}):
            self.assertEqual(dispatch.call(agy, "材料", str(self.home), 120, "high", "p")["status"], "error")

    def test_kimi_over_argv_limit_is_skipped_without_calling(self):
        kimi = inventory.describe({"id": "kimi.moonshot", "channel": "kimi", "kind": "cli", "vendor": "Moonshot",
                                   "billing": "subscription", "tiers": {"high": "kimi-code/k3"}}, "high")
        with self.fake({}):
            r = dispatch.call(kimi, "字" * 11000, str(self.home), 5, "high", "p")
        self.assertEqual((r["status"], self.calls), ("skipped", []))
        out = jl({"role": "meta", "type": "system.version"}, {"role": "assistant", "content": "收到"})
        with self.fake({"": (0, out, "")}):
            r = dispatch.call(kimi, "短材料", str(self.home), 5, "high", "p")
        self.assertEqual((r["status"], r["answer"]), ("ok", "收到"))
        self.assertEqual(self.calls[0][0][2], "短材料")

    def test_manual_entry_is_skipped(self):
        manual = {"id": "manual-x.mistral", "channel": "manual:x", "kind": "manual", "vendor": "Mistral",
                  "billing": "per-call", "tier": "low", "model": "mistral-small"}
        self.assertEqual(dispatch.call(manual, "材料", str(self.home), 5, "high", "p")["status"], "skipped")

    def test_child_env_marks_peer(self):
        seen = {}

        def fake_run(cmd, **kw):
            seen.update(kw)
            return mock.Mock(returncode=0, stdout="x", stderr="")
        with mock.patch.object(dispatch.subprocess, "run", fake_run):
            dispatch.run_process(["x"], str(self.home), 5, "in")
        self.assertEqual(seen["env"]["AI_CROSS_PEER"], "1")
        self.assertEqual(seen["input"], "in")


class TestRedactAndGuards(DBase):
    def test_literals_redacted_code_untouched(self):
        text = ('password = "hunter22"\napi_key: \'sk-abcdefgh12345678\'\nexport GLM_API_KEY=abcdef123456\n'
                "Authorization: Bearer abcdefghijkl\nAKIAABCDEFGHIJKLMNOP\npostgres://bob:s3cret@db/x\n"
                "-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----\n"
                "token = get_token()\npassword = os.environ[\"PW\"]\n")
        out, hits = dispatch.redact(text)
        for leaked in ("hunter22", "sk-abcdefgh12345678", "abcdef123456", "abcdefghijkl", "AKIAABCDEFGHIJKLMNOP",
                       "s3cret", "MIIE"):
            self.assertNotIn(leaked, out)
        self.assertIn("token = get_token()", out)                  # 代码本身不动
        self.assertIn('password = os.environ["PW"]', out)
        self.assertEqual(sum(hits.values()), 7)

    def test_redaction_reported_before_sending(self):
        self.material.write_text('DB = "postgres://bob:s3cret@db/x"\n', encoding="utf-8")
        code, out, _ = self.review()
        self.assertIn("脱敏", out)
        code, out, _ = self.review({"--provider": (0, pi_out(), "")}, go=True)
        self.assertNotIn("s3cret", self.calls[0][2])
        self.assertIn("redacted: 1", self.traces()[0].read_text(encoding="utf-8"))

    def test_peer_session_refuses_to_dispatch(self):
        argv = ["dispatch.py", "review", "--host", "codex", "--file", str(self.material), "--go"]
        with mock.patch.dict(os.environ, {"AI_CROSS_PEER": "1"}), mock.patch.object(sys, "argv", argv), self.fake({}):
            code, _, err = self.call(lambda _: dispatch.main())
        self.assertEqual(code, 2)
        self.assertEqual(self.calls, [])
        self.assertIn("不再往下派发", err)


class TestRun(DBase):
    def run_task(self, outputs=None, **over):
        task = self.home / "task.txt"
        task.write_text("写一个函数 slugify(title)，带 5 个单元测试。\n", encoding="utf-8")
        args = dict(host="claude-code", task_file=str(task), file=None, entry=None, tier=None, thinking="low",
                    project=str(self.project), timeout=5, json=False, go=False)
        args.update(over)
        with self.fake(outputs or {}):
            return self.call(dispatch.cmd_run, **args)

    def test_needs_an_executor(self):
        code, _, err = self.run_task(go=True)
        self.assertEqual((code, self.calls), (1, []))
        self.assertIn("set --executor", err)

    def test_plan_then_go_sends_task_verbatim(self):
        self.setm(executor="pi-zai-coding-cn.zhipu:low")
        code, out, _ = self.run_task()
        self.assertEqual((code, self.calls), (0, []))              # 不带 --go 不发送
        self.assertIn("[ai-cross] 执行 → pi:zai-coding-cn / glm-5.3-flash（Zhipu）", out)
        code, out, _ = self.run_task({"--provider": (0, pi_out("def slugify(title): ...", model="glm-5.3-flash"), "")},
                                     go=True, file=[str(self.material)])
        self.assertEqual(code, 0)
        cmd, cwd, stdin = self.calls[0]
        self.assertTrue(stdin.startswith("写一个函数 slugify(title)"))    # 任务原文，不套审查模板
        self.assertNotIn("请独立审查", stdin)
        self.assertIn("===== 文件：avg.py =====", stdin)            # 参考材料附在任务后面
        self.assertNotIn("--no-context-files", cmd)                 # 执行者不做盲审隔离
        self.assertIn("--no-tools", cmd)                            # 但同样没有工具，落盘归宿主
        self.assertEqual(cmd[cmd.index("--thinking") + 1], "low")
        self.assertIn("def slugify", out)
        self.assertIn("--author Zhipu", out)                        # 提示后续交叉验证要回避的厂商
        trace = self.traces()[0].read_text(encoding="utf-8")
        for needle in ('role: "执行"', 'visibility: "共享"', 'isolation: "部分"', "写一个函数 slugify"):
            self.assertIn(needle, trace)

    def test_named_executor_and_claude_not_restricted(self):
        code, out, _ = self.run_task({"claude": (0, CLAUDE_OUT, "")}, entry="claude.anthropic", go=True)
        self.assertEqual(code, 0)
        self.assertNotIn("--restricted", self.calls[0][0])
        self.assertIn("同厂商", out)                                # 宿主就是 Claude 时提醒可用内部通道

    def test_review_plan_points_to_run_for_work(self):
        _, out, _ = self.review()
        self.assertIn("dispatch.py run", out)


class TestSmoke(DBase):
    def test_smoke_records_pass_and_fail(self):
        outputs = {"glm-5.3-flash": (0, pi_out("收到", model="glm-5.3-flash"), ""),
                   "glm-5.3": (0, pi_out("收到"), ""), "exec": (1, "", "401 Unauthorized")}
        with self.fake(outputs):
            code, out, _ = self.call(dispatch.cmd_smoke, entry=["pi-zai-coding-cn.zhipu", "codex.openai"],
                                     all=False, timeout=5)
        self.assertEqual(code, 1)
        smoke = {e["id"]: e["smoke"] for e in self.manifest()["entries"]}
        self.assertEqual(smoke["pi-zai-coding-cn.zhipu"]["status"], "ok")
        self.assertEqual(smoke["codex.openai"]["status"], "fail")
        self.assertIn("401", smoke["codex.openai"]["reason"])
        tested = sorted(c[0][c[0].index("--model") + 1] for c in self.calls if "--provider" in c[0])
        self.assertEqual(tested, ["glm-5.3", "glm-5.3-flash"])     # 每个档位的模型都测
        _, res = self.pick("workbuddy", n=3)                       # 冒烟失败的 codex 之后不再被选中
        self.assertNotIn("codex.openai", [p["id"] for p in res["picked"]])

    def test_smoke_fails_entry_when_one_tier_is_dead(self):
        outputs = {"glm-5.3-flash": (0, pi_out("收到", model="glm-5.3-flash"), ""),
                   "glm-5.3": (0, pi_out(stop="error"), "")}
        with self.fake(outputs):
            code, out, _ = self.call(dispatch.cmd_smoke, entry=["pi-zai-coding-cn.zhipu"], all=False, timeout=5)
        self.assertEqual(code, 1)
        smoke = next(e["smoke"] for e in self.manifest()["entries"] if e["id"] == "pi-zai-coding-cn.zhipu")
        self.assertEqual(smoke["status"], "fail")
        self.assertIn("glm-5.3：", smoke["reason"])                # 原因里点名是哪一档哪个模型
        self.assertIn("重新 save", out)


if __name__ == "__main__":
    unittest.main()
