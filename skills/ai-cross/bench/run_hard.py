"""高难度基准 runner（v3）

新增核心实验：**advisor 臂**——用便宜档执行，但先向高档模型咨询一次决策点。
直接检验 Anthropic advisor strategy（执行者+顾问，成本反降 11.9%）在【跨 CLI 进程】
架构下是否仍成立。我们的预测：不成立或大打折扣，因为每次咨询要付 20k–30k 固定上下文足迹
（原生 advisor 是 in-request 工具，不重发上下文）。

沿用的测量纪律（前几轮血的教训）：
  - 只用结构化用量：codex `--json` → turn.completed.usage；claude `-p --output-format json` → usage
  - 绝不用 codex 打印的 `tokens used`（是未命中缓存的计费部分，随缓存跳 43 倍）
  - 每 trial 唯一 nonce；**trial1=冷，trial2+=热，分开统计**
  - 代码输出用 `-o FILE` 取，避免 stderr 横幅混入 verifier
  - verifier 先过正/负样本自检（见 tasks_hard.py）
"""
import argparse, json, re, subprocess, shutil, sys, time, csv, statistics, pathlib, uuid
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks_hard import TASKS_HARD

BENCH = pathlib.Path(__file__).parent
WORK = BENCH.parent / "test-run2"
CC_SWITCH = pathlib.Path.home() / ".claude" / "skills" / "model-dispatch" / "references" / "cc_switch.py"

CODEX = {
    "low":  dict(model="gpt-5.4-mini", effort="low"),
    "mid":  dict(model="gpt-5.4",      effort="medium"),
    "high": dict(model="gpt-5.5",      effort="xhigh"),
}
ARMS = {
    "codex-low":     dict(kind="codex", **CODEX["low"]),
    "codex-high":    dict(kind="codex", **CODEX["high"]),
    "codex-advisor": dict(kind="advisor", exec_=CODEX["low"], adv=CODEX["high"]),
    "glm-low":       dict(kind="ccsw", provider="Zhipu GLM", tier="haiku"),
    "step-low":      dict(kind="ccsw", provider="StepFun", tier="haiku"),
    # Anthropic 官方三档：同厂商同 harness，只变档位 —— 检验"档位是否影响正确率"
    "claude-low":    dict(kind="claude", model="haiku"),
    "claude-mid":    dict(kind="claude", model="sonnet"),
    "claude-high":   dict(kind="claude", model="opus"),
}
VENDOR = {"codex": "OpenAI", "glm": "智谱", "step": "StepFun", "claude": "Anthropic"}

ADVISOR_Q = (
    "下面是一个编程任务的规格。**不要写实现代码。**\n"
    "只做一件事：指出实现时最容易出错的 2-3 个决策点或边界条件，"
    "并对每一点给出明确裁决（具体该怎么处理）。要求极简，总共 200 字以内。\n\n"
    "任务规格：\n")


def _codex_call(cfg, prompt, timeout, tag):
    ev, lm = BENCH / f"_ev_{tag}.jsonl", BENCH / f"_lm_{tag}.txt"
    # 关键：prompt 必须走 stdin（`-`），不能作为 argv 传。
    # Windows 下多行 argv 会在第一个换行处被截断——codex 只收到规格的第一行，
    # 然后（完全正确地）回答"你没把算法贴出来"。这个 bug 让整套高难度基准误判为 0%，
    # 而简单基准（单行 prompt）却全 100%，一度被错误归因为"环境污染"。
    cmd = [shutil.which("codex"), "exec", "--json", "-m", cfg["model"],
           "-c", f'model_reasoning_effort="{cfg["effort"]}"',
           "-s", "read-only", "--skip-git-repo-check", "-o", str(lm), "-"]
    t0 = time.time()
    with ev.open("w", encoding="utf-8") as f:
        r = subprocess.run(cmd, cwd=WORK, input=prompt, stdout=f, stderr=subprocess.PIPE,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout)
    wall = time.time() - t0
    usage, tools, msgs, cmds = {}, 0, [], []
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
            it = e.get("item") or {}
            kind = it.get("item_type") or it.get("type")
            if kind in ("command_execution", "local_shell_call"):
                tools += 1
                cmds.append(str(it.get("command", "")))
            elif kind == "agent_message" and it.get("text"):
                msgs.append(it["text"])
    # 正文取自事件流的 agent_message。不能只靠 `-o`（最终消息）：codex 做完工具调用后
    # 常把最终消息写成总结、代码留在别处，导致 verifier 判"未找到代码起点"（踩过）。
    lm_text = lm.read_text(encoding="utf-8", errors="replace") if lm.exists() else ""
    out = msgs[-1] if msgs else lm_text
    has_code = "```" in out or re.search(r'^\s*def ', out, re.M)
    if not has_code and msgs:
        out = "\n\n".join(msgs)                       # 回退 1：全部 agent 消息
    if not ("```" in out or re.search(r'^\s*def ', out, re.M)):
        out = out + "\n\n" + "\n\n".join(cmds)        # 回退 2：代码可能被写进 shell 命令里
    for p in (ev, lm):
        p.unlink(missing_ok=True)
    inp = usage.get("input_tokens")
    return dict(ok=r.returncode == 0, out=out, input=inp,
                fresh=(inp - usage.get("cached_input_tokens", 0)) if inp is not None else None,
                output=usage.get("output_tokens") or 0, wall=wall, tools=tools,
                err=(r.stderr or "")[-160:] if r.returncode else "")


def run_codex(cfg, prompt, timeout, tag):
    return _codex_call(cfg, prompt, timeout, tag)


def run_advisor(cfg, prompt, timeout, tag):
    """先咨询高档模型（只要决策裁决，不要实现），再让便宜档带着建议执行。"""
    a = _codex_call(cfg["adv"], ADVISOR_Q + prompt, timeout, tag + "a")
    if not a["ok"]:
        return dict(ok=False, out="", input=a["input"], fresh=a["fresh"], output=a["output"],
                    wall=a["wall"], tools=a["tools"], err="advisor 失败: " + a["err"], adv_out=0)
    guided = prompt + "\n\n[资深顾问对本任务决策点的裁决，请务必遵循]\n" + a["out"].strip()
    e = _codex_call(cfg["exec_"], guided, timeout, tag + "e")
    return dict(ok=e["ok"], out=e["out"],
                input=(a["input"] or 0) + (e["input"] or 0),
                fresh=(a["fresh"] or 0) + (e["fresh"] or 0),
                output=(a["output"] or 0) + (e["output"] or 0),
                wall=a["wall"] + e["wall"], tools=a["tools"] + e["tools"],
                err=e["err"], adv_out=a["output"] or 0)


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
    m = re.search(r'input=(\d+) fresh=(\d+) cache_create=(\d+) cache_read=(\d+) output=(\d+)', r.stderr or "")
    inp, fresh, outp = (int(m.group(1)), int(m.group(2)), int(m.group(5))) if m else (None, None, None)
    mt = re.search(r'turns=(\d+)', r.stderr or "")
    turns = int(mt.group(1)) if mt else None
    return dict(ok=r.returncode == 0, out=r.stdout or "", input=inp, fresh=fresh, output=outp,
                wall=wall, tools=(turns - 1) if turns else None,
                err=(r.stderr or "")[-160:] if r.returncode else "")


def run_claude(cfg, prompt, timeout, tag):
    """Anthropic 官方订阅，同一 harness 只变档位。prompt 走 stdin（argv 会截断多行）。"""
    cmd = [shutil.which("claude"), "-p", "--model", cfg["model"], "--output-format", "json"]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=WORK, input=prompt, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    wall = time.time() - t0
    try:
        data = json.loads(r.stdout)
    except (json.JSONDecodeError, TypeError):
        return dict(ok=False, out="", input=None, fresh=None, output=None,
                    wall=wall, tools=None, err=(r.stderr or r.stdout or "")[-160:])
    # claude -p 遇 API 错误仍可能 exit 0，把错误文本塞进 result（踩过）
    if data.get("is_error") or data.get("api_error_status"):
        return dict(ok=False, out="", input=None, fresh=None, output=None, wall=wall,
                    tools=None, err=f"API {data.get('api_error_status')}: {str(data.get('result'))[:120]}")
    u = data.get("usage", {}) or {}
    fresh = u.get("input_tokens", 0)
    inp = fresh + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
    turns = data.get("num_turns")
    return dict(ok=True, out=data.get("result", ""), input=inp, fresh=fresh,
                output=u.get("output_tokens", 0), wall=wall,
                tools=(turns - 1) if turns else None, err="")


RUNNER = {"codex": run_codex, "advisor": run_advisor, "ccsw": run_ccsw, "claude": run_claude}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="codex-low,codex-advisor,codex-high,glm-low,step-low")
    ap.add_argument("--tasks", default="")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()

    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    want = {x.strip() for x in a.tasks.split(",") if x.strip()}
    tasks = [t for t in TASKS_HARD if not want or t["id"] in want]

    rows, n, total = [], 0, len(arms) * len(tasks) * a.trials
    for t in tasks:
        for arm in arms:
            cfg = ARMS[arm]
            for trial in range(1, a.trials + 1):
                n += 1
                tag = uuid.uuid4().hex[:6]
                prompt = f"{t['prompt']}\n\n[req-id:{tag}]"
                print(f"[{n}/{total}] {t['id']} × {arm} × t{trial} ...", flush=True)
                try:
                    res = RUNNER[cfg["kind"]](cfg, prompt, a.timeout, tag)
                except subprocess.TimeoutExpired:
                    res = dict(ok=False, out="", input=None, fresh=None, output=None,
                               wall=a.timeout, tools=None, err="TIMEOUT")
                correct, note = (False, res["err"]) if not res["ok"] else t["verifier"](res["out"])
                rows.append(dict(task=t["id"], type=t["type"], arm=arm,
                                 vendor=VENDOR[arm.split("-")[0]], trial=trial,
                                 cold=int(trial == 1), correct=int(correct),
                                 input=res["input"], fresh=res["fresh"], output=res["output"],
                                 wall=round(res["wall"], 1), tools=res["tools"],
                                 adv_out=res.get("adv_out", 0), note=note[:110]))
                print(f"      {'✅' if correct else '❌'} in={res['input']} fresh={res['fresh']} "
                      f"out={res['output']} {res['wall']:.0f}s tools={res['tools']} | {note[:62]}", flush=True)

    with (BENCH / "results_hard.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    def med(v):
        v = [x for x in v if x is not None]
        return int(statistics.median(v)) if v else 0

    print("\n" + "=" * 100)
    print(f"{'task':13}{'arm':15}{'正确率':>7}{'in中位':>9}{'冷fresh':>9}{'热fresh':>9}{'out':>7}{'秒':>6}{'工具':>6}")
    print("-" * 100)
    lines = []
    for t in tasks:
        for arm in arms:
            sub = [r for r in rows if r["task"] == t["id"] and r["arm"] == arm]
            if not sub: continue
            acc = sum(r["correct"] for r in sub) / len(sub)
            cold = [r["fresh"] for r in sub if r["cold"]]
            warm = [r["fresh"] for r in sub if not r["cold"]]
            line = (f"{t['id']:13}{arm:15}{acc*100:6.0f}%{med(r['input'] for r in sub):9d}"
                    f"{med(cold):9d}{med(warm):9d}{med(r['output'] for r in sub):7d}"
                    f"{statistics.median(r['wall'] for r in sub):6.0f}"
                    f"{med(r['tools'] for r in sub):6d}")
            print(line); lines.append(line)
    print("=" * 100)
    print("advisor 臂的 in/out/秒 = 咨询 + 执行两次调用之和。冷=trial1，热=trial2+。")
    (BENCH / "summary_hard.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
