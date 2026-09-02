"""深度轴基准：thinking on/off × {shallow, deep} × 5 模型 × n=5。

回答一个问题：推理预算该按"有无唯一答案"调，还是按"搜索深度"调？
两类任务**都有唯一可验证答案**，唯一区别是答案在不在输入里。

━━ 相对 run_text.py 的三条方法学修正（都是被自己坑出来的）━━

1. **判分绝不回退读 reasoning_content。**
   run_text.py 在 content 为空时读思考尾 200 字来判分。当 max_tokens 掐断思考时，
   这等于拿一段没写完的草稿当答案 → 制造出"思考让模型答错"的假象。
   现在：content 空即失败，并按 finish_reason 归因（truncated / empty）。

2. **max_tokens 给足 4096，且截断单独记账。**
   推理 token 与答案 token 共享同一预算。任何 finish_reason=="length" 都会被单列，
   截断率不为 0 的格子，其正确率不得用于比较。

3. **格式合规率与正确率分开报。**
   "答案对"和"只输出了答案"是两件事；抽取类任务真正在意的是后者。

其余纪律沿用：自造任务、程序化 GT、verifier 先过正负样本自检、n=5 取正确率均值。
"""
import json, urllib.request, urllib.error, pathlib, time, statistics, csv, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks_depth import TASKS

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"

MODELS = [
    ("Qwen3.6-35B",    "Qwen/Qwen3.6-35B-A3B"),
    ("GLM-5.2",        "zai-org/GLM-5.2"),
    ("DeepSeek-V4-Pro","deepseek-ai/DeepSeek-V4-Pro"),
    ("Kimi-K2.6",      "Pro/moonshotai/Kimi-K2.6"),
    ("LongCat-2.0",    "meituan-longcat/LongCat-2.0"),
]

TRIALS = 5
MAX_TOKENS = 4096       # 探针证实 2048 已足够；留 2× 余量
WORKERS = 6


def call(model_id, prompt, thinking):
    body = {"model": model_id, "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}]}
    if not thinking:
        body["enable_thinking"] = False     # 探针证实 5 个模型均真实生效
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", "Bearer " + KEY)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.loads(resp.read())
    wall = time.time() - t0
    c0 = (d.get("choices") or [{}])[0]
    ch = c0.get("message", {})
    u = d.get("usage", {})
    return dict(echo=d.get("model"), finish=c0.get("finish_reason"),
                content=(ch.get("content") or "").strip(),
                reasoning=(ch.get("reasoning_content") or "").strip(),
                completion=u.get("completion_tokens") or 0, wall=wall)


def one(args):
    mname, mid, task, thinking, trial = args
    err = ""
    r = None
    for attempt in (1, 2, 3):
        try:
            r = call(mid, task["prompt"], thinking); break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:60]}"
            time.sleep(2 * attempt)
    if r is None:
        return dict(task=task["id"], depth=task["depth"], type=task["type"], model=mname,
                    thinking=int(thinking), trial=trial, correct=0, strict=0,
                    completion=0, reasoning_chars=0, wall=0.0,
                    finish="ERROR", failmode="api_error", note=err[:60])

    truncated = (r["finish"] == "length")
    if not r["content"]:
        # 关键：绝不拿思考残留判分
        correct, strict = 0, 0
        failmode = "truncated_empty" if truncated else "empty"
        note = f"content 空 (finish={r['finish']}, reasoning {len(r['reasoning'])}字)"
    else:
        c, s, note = task["verifier"](r["content"])
        correct, strict = int(c), int(s)
        failmode = "" if correct else ("truncated" if truncated else "wrong")

    return dict(task=task["id"], depth=task["depth"], type=task["type"], model=mname,
                thinking=int(thinking), trial=trial, correct=correct, strict=strict,
                completion=r["completion"], reasoning_chars=len(r["reasoning"]),
                wall=round(r["wall"], 1), finish=r["finish"], failmode=failmode,
                note=note[:60])


def main():
    jobs = [(mn, mid, t, th, tr)
            for mn, mid in MODELS
            for t in TASKS
            for th in (False, True)
            for tr in range(1, TRIALS + 1)]
    print(f"共 {len(jobs)} 次调用（{len(MODELS)} 模型 × {len(TASKS)} 任务 × 2 臂 × {TRIALS} 轮），"
          f"并发 {WORKERS}，max_tokens={MAX_TOKENS}\n")

    rows = []
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(one, jobs):
            rows.append(r)
            done += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}]", flush=True)

    out = pathlib.Path(__file__).parent / "results_depth.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n原始数据 → {out}\n")

    def sel(**kw):
        return [r for r in rows if all(r[k] == v for k, v in kw.items())]

    def agg(sub):
        if not sub:
            return None
        return dict(
            acc=sum(r["correct"] for r in sub) / len(sub),
            strict=sum(r["strict"] for r in sub) / len(sub),
            trunc=sum(r["finish"] == "length" for r in sub) / len(sub),
            comp=statistics.median(r["completion"] for r in sub),
            wall=statistics.median(r["wall"] for r in sub),
            n=len(sub),
        )

    # ── 主表：深度 × thinking ──
    print("=" * 84)
    print("主结果：搜索深度 × thinking（跨 5 模型汇总）")
    print("=" * 84)
    print(f"{'深度':>8}{'thinking':>10}{'正确率':>9}{'格式合规':>10}{'截断率':>9}"
          f"{'completion中位':>15}{'秒中位':>9}{'n':>6}")
    print("-" * 84)
    main_tbl = {}
    for depth in ("shallow", "deep"):
        for th in (0, 1):
            a = agg(sel(depth=depth, thinking=th))
            main_tbl[(depth, th)] = a
            print(f"{depth:>8}{('on' if th else 'off'):>10}{a['acc']*100:>8.0f}%"
                  f"{a['strict']*100:>9.0f}%{a['trunc']*100:>8.0f}%"
                  f"{a['comp']:>15.0f}{a['wall']:>9.1f}{a['n']:>6}")

    print("\n" + "=" * 84)
    print("thinking 的净效应（on − off）")
    print("-" * 84)
    for depth in ("shallow", "deep"):
        on, off = main_tbl[(depth, 1)], main_tbl[(depth, 0)]
        dacc = (on["acc"] - off["acc"]) * 100
        ratio = on["comp"] / off["comp"] if off["comp"] else float("inf")
        verdict = ("推理有真实收益" if dacc >= 10 else
                   "推理零/负收益" if dacc <= 2 else "不确定")
        print(f"  {depth:>8}: 正确率 {dacc:+.0f} 个百分点   token {ratio:.0f}×   "
              f"耗时 {on['wall']/max(off['wall'],0.1):.0f}×   → {verdict}")

    # ── 逐任务 ──
    print("\n" + "=" * 84)
    print("逐任务正确率（off → on）")
    print("-" * 84)
    for t in TASKS:
        off, on = agg(sel(task=t["id"], thinking=0)), agg(sel(task=t["id"], thinking=1))
        d = (on["acc"] - off["acc"]) * 100
        flag = "  ⚠️截断" if on["trunc"] > 0 or off["trunc"] > 0 else ""
        print(f"  [{t['depth']:>7}] {t['id']:18} {off['acc']*100:>3.0f}% → {on['acc']*100:>3.0f}%"
              f"  ({d:+.0f}pp)  token {off['comp']:>5.0f} → {on['comp']:>5.0f}{flag}")

    # ── 逐模型 × 深度 ──
    print("\n" + "=" * 84)
    print("逐模型：thinking 净效应（正确率 pp）")
    print("-" * 84)
    print(f"{'模型':16}{'shallow':>12}{'deep':>12}{'shallow token比':>17}{'deep token比':>15}")
    for mn, _ in MODELS:
        cells = []
        for depth in ("shallow", "deep"):
            off, on = agg(sel(model=mn, depth=depth, thinking=0)), agg(sel(model=mn, depth=depth, thinking=1))
            cells.append(((on["acc"] - off["acc"]) * 100, on["comp"] / max(off["comp"], 1)))
        print(f"{mn:16}{cells[0][0]:>11.0f}{cells[1][0]:>12.0f}"
              f"{cells[0][1]:>16.0f}×{cells[1][1]:>14.0f}×")

    # ── 数据卫生 ──
    print("\n" + "=" * 84)
    print("数据卫生")
    print("-" * 84)
    errs = [r for r in rows if r["finish"] == "ERROR"]
    truncs = [r for r in rows if r["finish"] == "length"]
    empties = [r for r in rows if r["failmode"] == "empty"]
    print(f"  API 失败      : {len(errs)}/{len(rows)}")
    print(f"  截断(length)  : {len(truncs)}/{len(rows)}"
          + ("  ← 该格正确率不可用于比较" if truncs else "  ✅ 无截断，预算充足"))
    print(f"  content 空    : {len(empties)}/{len(rows)}")
    if truncs:
        from collections import Counter
        for (m, t, th), c in Counter((r["model"], r["task"], r["thinking"]) for r in truncs).items():
            print(f"      {m} / {t} / thinking={'on' if th else 'off'}: {c} 次")


if __name__ == "__main__":
    main()
