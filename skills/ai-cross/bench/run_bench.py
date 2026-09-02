"""档位对照基准 runner（v2：可靠仪器版）

测量教训（v1 踩过的坑，务必保留）：
  1. codex 打印的 "tokens used" 是【计费(未命中缓存)】部分，随 prompt 缓存状态在 188~19,538 之间乱跳，
     用它做跨档比较会得出完全错误的结论。改用 `codex exec --json` 的 turn.completed.usage。
  2. codex 的 stderr 含横幅(OpenAI Codex vX / workdir: ...)，混进代码 verifier 会 exec() 出 SyntaxError
     造成假阴性。改用 `-o FILE` 只取最终消息。
  3. 相同 prompt 会命中缓存，trial 之间不独立。每 trial 注入唯一 nonce。

指标定义：
  input       上下文总量（系统提示+工具定义+任务），稳定，反映“固定开销”
  fresh       未命中缓存的 input（计费主体），随缓存状态波动
  output      生成 token（含推理 token）
  tool_calls  工具调用轮数（thrash 指标）
"""
import argparse, json, re, subprocess, shutil, sys, time, csv, statistics, pathlib, uuid
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks import TASKS

BENCH = pathlib.Path(__file__).parent
WORK = BENCH.parent / "test-run2"
CC_SWITCH = pathlib.Path.home() / ".claude" / "skills" / "model-dispatch" / "references" / "cc_switch.py"

ARMS = {
    "codex-low":  dict(kind="codex", model="gpt-5.4-mini", effort="low"),
    "codex-mid":  dict(kind="codex", model="gpt-5.4",      effort="medium"),
    "codex-high": dict(kind="codex", model="gpt-5.5",      effort="xhigh"),
    "glm-low":    dict(kind="ccsw", provider="Zhipu GLM", tier="haiku"),
    "glm-mid":    dict(kind="ccsw", provider="Zhipu GLM", tier="sonnet"),
    "glm-high":   dict(kind="ccsw", provider="Zhipu GLM", tier="opus"),
    "step-low":   dict(kind="ccsw", provider="StepFun", tier="haiku"),
    "step-mid":   dict(kind="ccsw", provider="StepFun", tier="sonnet"),
    "step-high":  dict(kind="ccsw", provider="StepFun", tier="opus"),
}
VENDOR = {"codex": "OpenAI", "glm": "智谱", "step": "StepFun"}


def run_codex(cfg, prompt, timeout, tag):
    ev = BENCH / f"_ev_{tag}.jsonl"
    lm = BENCH / f"_lm_{tag}.txt"
    cmd = [shutil.which("codex"), "exec", "--json",
           "-m", cfg["model"], "-c", f'model_reasoning_effort="{cfg["effort"]}"',
           "-s", "read-only", "--skip-git-repo-check", "-o", str(lm), prompt]
    t0 = time.time()
    with ev.open("w", encoding="utf-8") as f:
        r = subprocess.run(cmd, cwd=WORK, stdout=f, stderr=subprocess.PIPE,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
    wall = time.time() - t0

    usage, tool_calls = {}, 0
    for line in ev.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "turn.completed":
            usage = e.get("usage", {}) or {}
        if e.get("type") == "item.completed":
            it = (e.get("item") or {}).get("item_type") or (e.get("item") or {}).get("type")
            if it in ("command_execution", "local_shell_call"):
                tool_calls += 1

    out = lm.read_text(encoding="utf-8", errors="replace") if lm.exists() else ""
    inp = usage.get("input_tokens")
    cached = usage.get("cached_input_tokens", 0)
    outp = (usage.get("output_tokens") or 0)
    for p in (ev, lm):
        p.unlink(missing_ok=True)
    return dict(ok=r.returncode == 0, out=out, input=inp,
                fresh=(inp - cached) if inp is not None else None,
                output=outp, wall=wall, tool_calls=tool_calls,
                err=(r.stderr or "")[-200:] if r.returncode else "")


def run_ccsw(cfg, prompt, timeout, tag):
    tf = BENCH / f"_task_{tag}.txt"
    tf.write_text(prompt, encoding="utf-8")
    cmd = [sys.executable, str(CC_SWITCH), "exec", "--provider", cfg["provider"],
           "--tier", cfg["tier"], "--usage", "--task-file", str(tf), "--timeout", str(timeout)]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=WORK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout + 30)
    wall = time.time() - t0
    tf.unlink(missing_ok=True)
    m = re.search(r'input=(\d+) fresh=(\d+) cache_create=(\d+) cache_read=(\d+) output=(\d+)',
                  r.stderr or "")
    if m:
        inp, fresh, _cc, _cr, outp = (int(m.group(i)) for i in range(1, 6))
    else:
        inp = fresh = outp = None
    # turns>1 表示模型做了工具调用后又续跑；turns==1 表示单轮直答。
    # 注意：这是【代理指标】，不是真实工具调用轮数——claude -p 的 JSON 未直接给出。
    mt = re.search(r'turns=(\d+)', r.stderr or "")
    turns = int(mt.group(1)) if mt else None
    return dict(ok=r.returncode == 0, out=r.stdout or "", input=inp, fresh=fresh,
                output=outp, wall=wall, tool_calls=(turns - 1) if turns else None,
                err=(r.stderr or "")[-200:] if r.returncode else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="codex-low,codex-high,glm-low,glm-mid,step-low,step-mid")
    ap.add_argument("--tasks", default="")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        print("ARMS :", ", ".join(ARMS))
        print("TASKS:", ", ".join(f"{t['id']}({t['type']}/{t['difficulty']})" for t in TASKS))
        return

    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    want = {x.strip() for x in a.tasks.split(",") if x.strip()}
    tasks = [t for t in TASKS if not want or t["id"] in want]

    rows, n, total = [], 0, len(arms) * len(tasks) * a.trials
    for t in tasks:
        for arm in arms:
            cfg = ARMS[arm]
            for trial in range(1, a.trials + 1):
                n += 1
                tag = uuid.uuid4().hex[:6]
                # nonce 破缓存：让每个 trial 成为独立样本
                prompt = f"{t['prompt']}\n\n[req-id:{tag}]"
                print(f"[{n}/{total}] {t['id']} × {arm} × t{trial} ...", flush=True)
                try:
                    res = (run_codex if cfg["kind"] == "codex" else run_ccsw)(
                        cfg, prompt, a.timeout, tag)
                except subprocess.TimeoutExpired:
                    res = dict(ok=False, out="", input=None, fresh=None, output=None,
                               wall=a.timeout, tool_calls=0, err="TIMEOUT")
                correct, note = (False, res["err"]) if not res["ok"] else t["verifier"](res["out"])
                rows.append(dict(task=t["id"], type=t["type"], difficulty=t["difficulty"],
                                 vendor=VENDOR[arm.split("-")[0]], arm=arm, trial=trial,
                                 correct=int(correct), input=res["input"], fresh=res["fresh"],
                                 output=res["output"], wall=round(res["wall"], 1),
                                 tool_calls=res["tool_calls"], note=note[:110]))
                print(f"      {'✅' if correct else '❌'} in={res['input']} fresh={res['fresh']} "
                      f"out={res['output']} {res['wall']:.0f}s tools={res['tool_calls']} | {note[:60]}",
                      flush=True)

    csv_path = BENCH / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    def med(vals):
        v = [x for x in vals if x is not None]
        return int(statistics.median(v)) if v else 0

    print("\n" + "=" * 92)
    print(f"{'task':14}{'arm':12}{'厂商':8}{'正确率':>7}{'input中位':>10}{'out中位':>9}{'秒':>6}{'工具轮':>7}")
    print("-" * 92)
    lines = []
    for t in tasks:
        for arm in arms:
            sub = [r for r in rows if r["task"] == t["id"] and r["arm"] == arm]
            if not sub: continue
            acc = sum(r["correct"] for r in sub) / len(sub)
            line = (f"{t['id']:14}{arm:12}{VENDOR[arm.split('-')[0]]:8}{acc*100:6.0f}%"
                    f"{med(r['input'] for r in sub):10d}{med(r['output'] for r in sub):9d}"
                    f"{statistics.median(r['wall'] for r in sub):6.0f}"
                    f"{statistics.median(r['tool_calls'] for r in sub):7.0f}")
            print(line); lines.append(line)
    print("=" * 92)
    print("注：input=上下文总量(稳定，反映固定开销)；跨厂商 token 可比，成本不可比(单价不同)。")
    (BENCH / "summary.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
