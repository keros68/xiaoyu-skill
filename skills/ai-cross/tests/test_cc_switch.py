# cc_switch.py 单元测试。纯标准库,mock 掉 claude CLI 与真实 cc-switch 库,不发任何网络请求。
# 跑法: python -m unittest discover -s tests  (在 dist/ai-cross 目录下)
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references"))
import cc_switch

TOKEN = "sk-SECRET-NEVER-PRINT"


def make_db(path, providers):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE providers (id TEXT, app_type TEXT, name TEXT, category TEXT, settings_config TEXT)")
    con.execute("CREATE TABLE provider_endpoints (provider_id TEXT, url TEXT)")
    for p in providers:
        con.execute("INSERT INTO providers VALUES (?,?,?,?,?)",
                    (p["id"], p["app_type"], p["name"], p.get("category", ""), json.dumps(p["cfg"])))
    con.commit()
    con.close()


GLM = {
    "id": "p1", "app_type": "claude", "name": "Zhipu GLM",
    "cfg": {"env": {
        "ANTHROPIC_BASE_URL": "https://example.invalid/api/anthropic",
        "ANTHROPIC_AUTH_TOKEN": TOKEN,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-5-turbo",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.2",
    }},
}
NO_KEY = {"id": "p2", "app_type": "claude", "name": "NoKey", "cfg": {"env": {"ANTHROPIC_BASE_URL": "https://x.invalid"}}}
CODEX = {"id": "p3", "app_type": "codex", "name": "Codex Official", "cfg": {"env": {}}}


class Base(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        make_db(self.db, [GLM, NO_KEY, CODEX])
        self._old_db = cc_switch.DB
        cc_switch.DB = self.db

    def tearDown(self):
        cc_switch.DB = self._old_db
        os.unlink(self.db)

    def run_exec(self, run_mock=None, **over):
        """跑 cmd_exec,返回 (exit_code, stdout, stderr, subprocess.run 的调用参数)。"""
        args = Namespace(provider="Zhipu GLM", tier="haiku", model=None, task="任务",
                         task_file=None, tools="Read,Grep,Glob", usage=False, timeout=5)
        for k, v in over.items():
            setattr(args, k, v)
        ok = json.dumps({"is_error": False, "result": "答案", "usage": {}, "num_turns": 1, "duration_ms": 1})
        if run_mock is None:
            run_mock = mock.Mock(return_value=mock.Mock(stdout=ok, stderr="", returncode=0))
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(cc_switch.shutil, "which", return_value="claude"), \
             mock.patch.object(cc_switch.subprocess, "run", run_mock), \
             redirect_stdout(out), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                cc_switch.cmd_exec(args)
        call = run_mock.call_args if run_mock.called else None
        return cm.exception.code or 0, out.getvalue(), err.getvalue(), call


class TestList(Base):
    def test_list_never_leaks_token(self):
        out = io.StringIO()
        with redirect_stdout(out):
            cc_switch.cmd_list(Namespace(human=False))
        text = out.getvalue()
        self.assertNotIn(TOKEN, text)
        provs = {p["name"]: p for p in json.loads(text)}
        self.assertTrue(provs["Zhipu GLM"]["has_token"])
        self.assertFalse(provs["NoKey"]["has_token"])
        self.assertEqual(provs["Zhipu GLM"]["tier_models"]["sonnet"], "glm-5.2")

    def test_missing_db_exits_2(self):
        cc_switch.DB = self.db + ".nope"
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            cc_switch.cmd_list(Namespace(human=False))
        self.assertEqual(cm.exception.code, 2)


class TestExec(Base):
    def test_env_injection_and_cmd_shape(self):
        code, out, err, call = self.run_exec()
        self.assertEqual(code, 0)
        self.assertEqual(out, "答案")  # stdout 只含模型回答
        env = call.kwargs["env"]
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "https://example.invalid/api/anthropic")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], TOKEN)
        self.assertEqual(env["AI_CROSS_PEER"], "1")          # 防套娃标记
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        cmd = call.args[0]
        self.assertIn("--output-format", cmd)                 # 唯一能查 is_error 的形式
        self.assertIn("json", cmd)
        self.assertIn("--tools", cmd)
        self.assertEqual(cmd[cmd.index("--model") + 1], "glm-5-turbo")  # haiku 档映射
        self.assertEqual(call.kwargs["input"], "任务")        # task 走 stdin 不进 argv
        self.assertNotIn(TOKEN, " ".join(cmd))                # key 不进命令行

    def test_api_error_masquerade_exits_8(self):
        bad = json.dumps({"is_error": True, "api_error_status": 529, "result": "API Error: overloaded"})
        rm = mock.Mock(return_value=mock.Mock(stdout=bad, stderr="", returncode=0))
        code, out, err, _ = self.run_exec(run_mock=rm)
        self.assertEqual(code, 8)
        self.assertEqual(out, "")                             # 错误绝不伪装成答案进 stdout
        self.assertIn("API 错误", err)
        self.assertNotIn(TOKEN, out + err)

    def test_error_paths(self):
        for over, expect in ((dict(provider="不存在"), 2),
                             (dict(provider="Codex Official"), 3),
                             (dict(provider="NoKey"), 4),
                             (dict(tier="opus"), 5),          # GLM 未配 opus 档
                             (dict(task="  "), 7)):
            code, out, err, _ = self.run_exec(**over)
            self.assertEqual(code, expect, f"{over} 应 exit {expect},实得 {code}")
            self.assertNotIn(TOKEN, out + err)

    def test_explicit_model_overrides_tier(self):
        code, _, _, call = self.run_exec(model="glm-5.2[1m]")
        self.assertEqual(code, 0)
        cmd = call.args[0]
        self.assertEqual(cmd[cmd.index("--model") + 1], "glm-5.2[1m]")


if __name__ == "__main__":
    unittest.main()
