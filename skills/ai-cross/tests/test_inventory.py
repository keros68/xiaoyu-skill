# inventory.py 单元测试。纯标准库,假的主目录与假的探测结果,不跑任何 CLI、不发网络请求。
# 跑法: python -m unittest discover -s tests  (在 skill 目录下)
import io
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout, redirect_stderr
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references"))
import cc_switch
import inventory
from test_cc_switch import CODEX, GLM, NO_KEY, TOKEN, make_db

SECRET = "oauth-SECRET-NEVER-PRINT"


def channel(cid, models, kind="cli", isolation="partial", **extra):
    ch = {"id": cid, "kind": kind, "installed": True, "isolation": isolation, "source": "读:测试",
          "models": [inventory.model(m) for m in models]}
    ch.update(extra)
    return ch


FAKE = {"channels": [
    channel("claude", ["haiku", "sonnet", "opus"], isolation="full"),
    channel("codex", ["gpt-6-luna", "gpt-6.1-sol"], path="C:/bin/codex.cmd"),
    channel("agy", ["gemini-3.8-flash-low", "gemini-3.8-flash-high", "claude-opus-5-5-high"]),
    channel("pi:zai-coding-cn", ["glm-5.3-flash", "glm-5.3"], kind="pi", isolation="full"),
    channel("pi:opencode-go", ["hy3", "grok-4.7"], kind="pi", isolation="full"),
    channel("cc-switch:DeepSeek", ["deepseek-v4-flash"], kind="cc-switch"),
]}

PLAN = {"entries": [
    {"channel": "claude", "billing": "subscription", "tiers": {"low": "haiku", "high": "opus"}},
    {"channel": "cc-switch:DeepSeek", "billing": "per-call", "tiers": {"low": "deepseek-v4-flash"}},
    {"channel": "codex", "billing": "subscription", "tiers": {"low": "gpt-6-luna", "high": "gpt-6.1-sol"}},
    {"channel": "pi:zai-coding-cn", "billing": "subscription", "tiers": {"low": "glm-5.3-flash", "high": "glm-5.3"}},
]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        patches = [
            mock.patch.object(inventory, "HOME", self.home),
            mock.patch.dict(os.environ, {"AICROSS_HOME": str(self.home / "data")}),
            mock.patch.object(inventory, "detect", return_value=FAKE),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("ANTHROPIC_BASE_URL", None)
        self.addCleanup(self.tmp.cleanup)

    def call(self, func, **kw):
        """跑一个子命令,返回 (退出码, stdout, stderr)。"""
        out, err, code = io.StringIO(), io.StringIO(), 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                func(Namespace(**kw))
            except SystemExit as e:
                code = e.code or 0
        return code, out.getvalue(), err.getvalue()

    def save(self, plan=PLAN, replace=False):
        path = self.home / "plan.json"
        path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        return self.call(inventory.cmd_save, plan=str(path), replace=replace)

    def pick(self, host="claude-code", role="reviewer", author=None, n=None, tier=None):
        code, out, err = self.call(inventory.cmd_pick, role=role, host=host, author=author, n=n, tier=tier)
        return code, json.loads(out)

    def setm(self, **kw):
        args = dict(smoke=None, billing=None, reviewers=None, executor=None, note=None, remove=None)
        args.update(kw)
        return self.call(inventory.cmd_set, **args)

    def manifest(self):
        return json.loads(inventory.manifest_path().read_text(encoding="utf-8"))


class TestProbes(Base):
    def test_vendor_rules(self):
        self.assertEqual(inventory.vendor_of("kimi-code/k3"), "Moonshot")
        self.assertEqual(inventory.vendor_of("GLM-5.3-Flash[1M]"), "Zhipu")
        self.assertEqual(inventory.vendor_of("gpt-oss-120b-medium"), "OpenAI")
        self.assertIsNone(inventory.vendor_of("hy3"))               # 没把握的不猜
        self.assertEqual(inventory.canon_vendor("智谱"), "Zhipu")
        self.assertEqual(inventory.canon_vendor("openai"), "OpenAI")

    def test_kimi_reads_models_only(self):
        cfg = self.home / ".kimi-code"
        cfg.mkdir()
        (cfg / "config.toml").write_text(
            'default_model = "kimi-code/k3"\n'
            '[providers."managed:kimi-code".oauth]\n'
            f'access_token = "{SECRET}"\n'
            '[models."kimi-code/k3"]\nmodel = "k3"\ndisplay_name = "K3"\n'
            '[models."kimi-code/kimi-for-coding"]\nmodel = "kimi-for-coding"\n'
            '[thinking]\nenabled = true\n', encoding="utf-8")
        ch = inventory.probe_kimi("kimi")
        self.assertEqual([m["id"] for m in ch["models"]], ["kimi-code/k3", "kimi-code/kimi-for-coding"])
        self.assertEqual(ch["preferred_model"], "kimi-code/k3")
        self.assertNotIn(SECRET, json.dumps(ch))

    def test_codex_skips_hidden_models(self):
        d = self.home / ".codex"
        d.mkdir()
        (d / "models_cache.json").write_text(json.dumps({"identity": SECRET, "models": [
            {"slug": "gpt-6.1-sol", "visibility": "list", "description": "workhorse"},
            {"slug": "codex-auto-review", "visibility": "hide"}]}), encoding="utf-8")
        (d / "config.toml").write_text('model = "gpt-6.1-sol"\n[projects.x]\nmodel = "other"\n', encoding="utf-8")
        ch = inventory.probe_codex("codex")
        self.assertEqual([m["id"] for m in ch["models"]], ["gpt-6.1-sol"])
        self.assertEqual(ch["preferred_model"], "gpt-6.1-sol")
        self.assertNotIn(SECRET, json.dumps(ch))

    def test_claude_flags_global_override_without_value(self):
        d = self.home / ".claude"
        d.mkdir()
        (d / "settings.json").write_text(json.dumps(
            {"model": "opus", "env": {"ANTHROPIC_BASE_URL": "https://x.invalid", "ANTHROPIC_AUTH_TOKEN": TOKEN}}),
            encoding="utf-8")
        ch = inventory.probe_claude("claude")
        self.assertIn("warning", ch)
        self.assertNotIn(TOKEN, json.dumps(ch))
        self.assertNotIn("x.invalid", json.dumps(ch))

    def test_pi_table_ignores_noise(self):
        table = ("Warning: extension failed to load\n"
                 "provider       model          context  max-out  thinking  images\n"
                 "zai-coding-cn  glm-5.3        1M       131.1K   yes       no\n"
                 "opencode-go    grok-4.7       500K     500K     yes       yes\n\n")
        with mock.patch.object(inventory, "run_cli", return_value=(0, table)):
            provs = inventory.probe_pi("pi")
        self.assertEqual(sorted(provs), ["opencode-go", "zai-coding-cn"])
        self.assertEqual(provs["zai-coding-cn"][0]["vendor"], "Zhipu")

    def test_agy_list(self):
        out = "gemini-3.8-flash-high\tGemini 3.8 Flash (High)\nFetching available models...\n"
        with mock.patch.object(inventory, "run_cli", return_value=(0, out)):
            ch = inventory.probe_agy("agy")
        self.assertEqual([m["id"] for m in ch["models"]], ["gemini-3.8-flash-high"])

    def test_cc_switch_only_dispatchable_and_no_token(self):
        db = str(self.home / "cc.db")
        make_db(db, [GLM, NO_KEY, CODEX])
        with mock.patch.object(cc_switch, "DB", db):
            chans = inventory.probe_cc_switch()
        self.assertEqual([c["id"] for c in chans], ["cc-switch:Zhipu GLM"])
        self.assertEqual([(m["id"], m["tier"]) for m in chans[0]["models"]],
                         [("glm-5-turbo", "low"), ("glm-5.2", "mid")])
        self.assertNotIn(TOKEN, json.dumps(chans))


class TestSave(Base):
    def test_save_writes_under_data_root(self):
        code, out, _ = self.save()
        self.assertEqual(code, 0)
        self.assertEqual(inventory.manifest_path(), self.home / "data" / "skill" / "manifest.json")
        ids = [e["id"] for e in self.manifest()["entries"]]
        self.assertEqual(ids, ["claude.anthropic", "cc-switch-deepseek.deepseek", "codex.openai",
                               "pi-zai-coding-cn.zhipu"])

    def test_unknown_model_rejected_and_nothing_written(self):
        code, _, err = self.save({"entries": [{"channel": "codex", "tiers": {"high": "gpt-7-ultra"}}]})
        self.assertEqual(code, 2)
        self.assertIn("gpt-7-ultra", err)
        self.assertFalse(inventory.manifest_path().exists())

    def test_one_entry_one_vendor(self):
        mixed = {"entries": [{"channel": "agy", "tiers": {"low": "gemini-3.8-flash-low",
                                                          "high": "claude-opus-5-5-high"}}]}
        self.assertEqual(self.save(mixed)[0], 2)
        unknown = {"entries": [{"channel": "pi:opencode-go", "tiers": {"low": "hy3"}}]}
        self.assertEqual(self.save(unknown)[0], 2)               # 认不出厂商必须申报
        unknown["entries"][0]["vendor"] = "腾讯"
        self.assertEqual(self.save(unknown)[0], 0)
        self.assertEqual(self.manifest()["entries"][0]["vendor"], "腾讯")

    def test_unknown_channel_and_manual_declaration(self):
        self.assertEqual(self.save({"entries": [{"channel": "gemini", "tiers": {"low": "x"}}]})[0], 2)
        manual = {"entries": [{"channel": "manual:openrouter", "vendor": "mistral", "billing": "per-call",
                               "tiers": {"low": "mistral-small"}}]}
        self.assertEqual(self.save(manual)[0], 0)
        entry = self.manifest()["entries"][0]
        self.assertEqual((entry["id"], entry["vendor"]), ("manual-openrouter.mistral", "Mistral"))
        self.assertTrue(entry["source"].startswith("申报("))

    def test_resave_keeps_smoke_only_when_models_unchanged(self):
        self.save()
        self.setm(smoke=["codex.openai=ok", "claude.anthropic=ok"])
        changed = json.loads(json.dumps(PLAN))
        changed["entries"][2]["tiers"] = {"high": "gpt-6.1-sol"}
        self.save(changed)
        smoke = {e["id"]: e["smoke"]["status"] for e in self.manifest()["entries"]}
        self.assertEqual(smoke["claude.anthropic"], "ok")
        self.assertEqual(smoke["codex.openai"], "untested")


class TestPick(Base):
    def setUp(self):
        super().setUp()
        self.save()

    def test_excludes_host_vendor(self):
        code, res = self.pick("claude-code")
        self.assertEqual(code, 0)
        # 订阅内且隔离完整的排最前；宿主同厂商的 claude 被排除
        self.assertEqual([p["id"] for p in res["picked"]], ["pi-zai-coding-cn.zhipu"])
        self.assertEqual(res["picked"][0]["model"], "glm-5.3")      # 审查默认取高档

    def test_per_call_goes_last_and_vendors_distinct(self):
        _, res = self.pick("claude-code", n=3)
        self.assertEqual([p["id"] for p in res["picked"]],
                         ["pi-zai-coding-cn.zhipu", "codex.openai", "cc-switch-deepseek.deepseek"])
        self.assertTrue(any("按次计费" in n for n in res["notes"]))

    def test_opaque_host_gets_two_external_vendors(self):
        _, res = self.pick("workbuddy")
        self.assertIsNone(res["author_vendor"])
        self.assertEqual(len({p["vendor"] for p in res["picked"]}), 2)

    def test_overridden_claude_host_is_not_anthropic(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://x.invalid"}):
            _, res = self.pick("claude-code")
        self.assertIsNone(res["author_vendor"])
        self.assertIn("claude.anthropic", [p["id"] for p in res["picked"]])

    def test_author_alias_and_host_can_join(self):
        _, res = self.pick("claude-code", author="智谱")
        self.assertEqual(res["author_vendor"], "Zhipu")
        self.assertEqual(res["picked"][0]["id"], "claude.anthropic")
        self.assertTrue(any("宿主自己" in n for n in res["notes"]))

    def test_author_none_excludes_nobody(self):
        _, res = self.pick("claude-code", author="none", tier="low")
        self.assertEqual([p["id"] for p in res["picked"]], ["claude.anthropic", "pi-zai-coding-cn.zhipu"])
        self.assertEqual(res["picked"][0]["model"], "haiku")

    def test_failed_smoke_skipped_and_tier_fallback(self):
        self.setm(smoke=["pi-zai-coding-cn.zhipu=fail:401"])
        _, res = self.pick("claude-code")
        self.assertEqual(res["picked"][0]["id"], "codex.openai")
        _, res = self.pick("codex", n=3, tier="mid")
        tiers = {p["id"]: p["tier"] for p in res["picked"]}
        self.assertEqual(tiers["claude.anthropic"], "low")          # 没配 mid,往下取
        self.assertEqual(tiers["cc-switch-deepseek.deepseek"], "low")

    def test_single_vendor_exits_1(self):
        self.save({"entries": [PLAN["entries"][0]]}, replace=True)
        code, res = self.pick("claude-code")
        self.assertEqual(code, 1)
        self.assertEqual(res["picked"], [])

    def test_stale_smoke_flagged(self):
        self.setm(smoke=["codex.openai=ok"])
        data = self.manifest()
        old = (date.today() - timedelta(days=45)).isoformat()
        next(e for e in data["entries"] if e["id"] == "codex.openai")["smoke"]["date"] = old
        inventory.write_manifest(data)
        _, res = self.pick("claude-code", n=2)
        self.assertIn("先冒烟", next(p for p in res["picked"] if p["id"] == "codex.openai")["smoke"])


class TestSet(Base):
    def setUp(self):
        super().setUp()
        self.save()

    def test_pinned_reviewer_and_executor(self):
        code, out, _ = self.setm(reviewers="codex.openai", executor="pi-zai-coding-cn.zhipu:low")
        self.assertEqual(code, 0)
        _, res = self.pick("claude-code")
        self.assertEqual(res["picked"][0]["id"], "codex.openai")
        _, res = self.pick("claude-code", role="executor")
        self.assertEqual((res["picked"][0]["id"], res["picked"][0]["model"]),
                         ("pi-zai-coding-cn.zhipu", "glm-5.3-flash"))

    def test_billing_change_reorders_unpinned(self):
        self.setm(billing=["pi-zai-coding-cn.zhipu=per-call"])
        _, res = self.pick("claude-code")
        self.assertEqual(res["picked"][0]["id"], "codex.openai")

    def test_remove_clears_roles(self):
        self.setm(reviewers="codex.openai", executor="codex.openai")
        self.setm(remove=["codex.openai"])
        roles = self.manifest()["roles"]
        self.assertEqual((roles["reviewer_first"], roles["executor"]), ([], None))

    def test_bad_input_changes_nothing(self):
        before = self.manifest()
        for kw in (dict(smoke=["nope=ok"]), dict(smoke=["codex.openai=maybe"]),
                   dict(executor="claude.anthropic:mid"), dict()):
            self.assertEqual(self.setm(**kw)[0], 2, kw)
        self.assertEqual(self.manifest(), before)

    def test_no_manifest_exits_3(self):
        inventory.manifest_path().unlink()
        self.assertEqual(self.call(inventory.cmd_show, human=False)[0], 3)


if __name__ == "__main__":
    unittest.main()
