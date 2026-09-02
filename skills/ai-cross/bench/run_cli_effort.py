"""② 官方端点复测：thinking/effort 旋钮在**你日常用的工具**上是否复现深任务增益。

背景：+71pp 的深度轴数据全部来自硅基流动的开源模型。日常主力是 Claude/Codex 订阅。
旧结论"官方推理强度零增益"来自 coding 任务（可写代码，深度被工具吸收）。
本测试用同一批**纯文本深任务**问官方 CLI：

  臂A claude -p --model haiku：MAX_THINKING_TOKENS=0（关）vs 默认（开）
  臂B codex exec -m gpt-5.4-mini：model_reasoning_effort low vs high

关键差异（如实记录，不掩盖）：CLI 是 harness，模型**可以尝试用工具**（写代码算）。
这正是真实使用形态——我们同时记录 num_turns/事件数，区分"自己想对的"和"借工具算对的"。

判分沿用 tasks_depth 的 verifier（只看最终文本，抽末尾数值）。
prompt 走 stdin（SPEC 教训 #7：argv 多行截断）。检查 is_error（教训：exit 0 ≠ 成功）。
4 深任务 × 2 CLI × 2 档 × n=3 = 48 次，走订阅额度，不花现金。
"""
import json, subprocess, pathlib, time, csv, shutil, sys, os

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks_depth import TASKS

DEEP = [t for t in TASKS if t["depth"] == "deep"]
TRIALS = 3
CLAUDE = shutil.which("claude")
CODEX = shutil.which("codex")


def run_claude(task_text, thinking_on):
    env = dict(os.environ)
    if not thinking_on:
        env["MAX_THINKING_TOKENS"] = "0"
    else:
        env.pop("MAX_THINKING_TOKENS", None)
    t0 = time.time()
    p = subprocess.run([CLAUDE, "-p", "--model", "haiku", "--output-format", "json"],
                       input=task_text.encode(), capture_output=True, env=env, timeout=600)
    wall = time.time() - t0
    try:
        d = json.loads(p.stdout)
    except Exception:
        return dict(ok=False, text=p.stdout.decode(errors="replace")[:200], turns=0,
                    out_tok=0, wall=wall, err=f"json解析失败 rc={p.returncode}")
    if d.get("is_error"):
        return dict(ok=False, text="", turns=0, out_tok=0, wall=wall,
                    err=f"is_error: {str(d.get('result'))[:80]}")
    return dict(ok=True, text=d.get("result") or "", turns=d.get("num_turns", 0),
                out_tok=d.get("usage", {}).get("output_tokens", 0), wall=wall, err="")


def run_codex(task_text, effort):
    t0 = time.time()
    # --skip-git-repo-check：bench/ 不在 git 仓库内，缺它 codex 直接 rc=1
    #（第一版 24 次全败即此因——又一例"先看它到底收到了什么/为什么退出"）
    p = subprocess.run([CODEX, "exec", "-m", "gpt-5.4-mini", "--skip-git-repo-check",
                        "-c", f"model_reasoning_effort={effort}", "--json"],
                       input=task_text.encode(), capture_output=True, timeout=600)
    wall = time.time() - t0
    last_msg, out_tok, n_events = "", 0, 0
    for line in p.stdout.decode(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        n_events += 1
        t = ev.get("type") or ev.get("msg", {}).get("type", "")
        if t == "item.completed":
            item = ev.get("item", {})
            if item.get("item_type") == "assistant_message" or item.get("type") == "agent_message":
                last_msg = item.get("text", "") or last_msg
        if "agent_message" in str(t):
            last_msg = (ev.get("msg", {}) or {}).get("message", "") or last_msg
        if t == "turn.completed":
            out_tok = (ev.get("usage") or {}).get("output_tokens", out_tok)
    if not last_msg:
        return dict(ok=False, text=p.stdout.decode(errors="replace")[-200:], turns=n_events,
                    out_tok=out_tok, wall=wall, err=f"无assistant消息 rc={p.returncode}")
    return dict(ok=True, text=last_msg, turns=n_events, out_tok=out_tok, wall=wall, err="")


def main():
    assert CLAUDE and CODEX, f"CLI缺失 claude={CLAUDE} codex={CODEX}"
    only = sys.argv[1] if len(sys.argv) > 1 else None   # 传 codex/claude 只跑一臂
    rows = []
    jobs = []
    for t in DEEP:
        for arm, knob in (("claude-haiku", False), ("claude-haiku", True),
                          ("codex-mini", "low"), ("codex-mini", "high")):
            if only and only not in arm:
                continue
            for tr in range(1, TRIALS + 1):
                jobs.append((t, arm, knob, tr))
    print(f"共 {len(jobs)} 次 CLI 调用（串行，避免本机争抢）\n")
    for i, (t, arm, knob, tr) in enumerate(jobs, 1):
        if arm == "claude-haiku":
            r = run_claude(t["prompt"], thinking_on=knob)
            knob_label = "on" if knob else "off"
        else:
            r = run_codex(t["prompt"], effort=knob)
            knob_label = knob
        if r["ok"]:
            c, s, note = t["verifier"](r["text"])
        else:
            c, note = 0, r["err"]
        rows.append(dict(task=t["id"], cli=arm, knob=knob_label, trial=tr,
                         correct=int(bool(c)) if r["ok"] else 0, turns=r["turns"],
                         out_tok=r["out_tok"], wall=round(r["wall"], 1),
                         ok=int(r["ok"]), note=note[:60], raw=r["text"][:300]))
        print(f"  [{i}/{len(jobs)}] {t['id']:16} {arm:13} {knob_label:4} t{tr} "
              f"{'✅' if rows[-1]['correct'] else '❌'} turns={r['turns']} tok={r['out_tok']} {r['wall']:.0f}s",
              flush=True)

    out = pathlib.Path(__file__).parent / (f"results_cli_effort_{only}.csv" if only else "results_cli_effort.csv")
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n→ {out}\n")

    print(f"{'CLI':>14}{'档':>6}{'正确率':>8}{'turns中位':>10}{'out_tok中位':>12}{'秒中位':>8}")
    for arm in ("claude-haiku", "codex-mini"):
        for knob in (("off", "on") if arm == "claude-haiku" else ("low", "high")):
            sub = [r for r in rows if r["cli"] == arm and r["knob"] == knob and r["ok"]]
            if not sub:
                print(f"{arm:>14}{knob:>6}   (全部失败)")
                continue
            acc = sum(r["correct"] for r in sub) / len(sub)
            med = lambda k: sorted(r[k] for r in sub)[len(sub) // 2]
            print(f"{arm:>14}{knob:>6}{acc*100:>7.0f}%{med('turns'):>10}{med('out_tok'):>12}{med('wall'):>8.0f}")

    print("\n逐任务：")
    for t in DEEP:
        line = f"  {t['id']:16}"
        for arm, knob in (("claude-haiku", "off"), ("claude-haiku", "on"),
                          ("codex-mini", "low"), ("codex-mini", "high")):
            sub = [r for r in rows if r["task"] == t["id"] and r["cli"] == arm and r["knob"] == knob and r["ok"]]
            acc = sum(r["correct"] for r in sub) / len(sub) if sub else float("nan")
            line += f" {arm.split('-')[0]}-{knob}:{acc*100:3.0f}%"
        print(line)
    fails = [r for r in rows if not r["ok"]]
    print(f"\nCLI 调用失败: {len(fails)}")
    for r in fails[:5]:
        print(f"  {r['task']} {r['cli']} {r['knob']}: {r['note']}")


if __name__ == "__main__":
    main()
