"""重跑 d-multihop 格子（修复病态题后）：5 模型 × 2 臂 × n=5 = 50 次。

为什么重跑：旧题 jia=260 时丙=197.5（题面未声明"一半"取整），5 个模型一致
按 197.5 忠实计算，被旧判分器（不识别小数）记成诡异的 (4,5)。错在题和尺子。
新题 jia=272 全程中间值为整数（tasks_depth.py 已加断言），判分器已识别小数。

新纪律（本次事故直接买来的）：**保存每次调用的完整原始 content** 到
results_multihop_fix.csv 的 raw 列——note 只有 60 字，出诡异值时无法尸检。
"""
import json, urllib.request, pathlib, time, csv, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks_depth import D_MULTIHOP, D_MULTIHOP_GT, v_multihop

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


def call(mid, thinking):
    body = {"model": mid, "max_tokens": 16384,
            "messages": [{"role": "user", "content": D_MULTIHOP}]}
    if not thinking:
        body["enable_thinking"] = False
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", "Bearer " + KEY)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.loads(resp.read())
    wall = time.time() - t0
    c0 = d["choices"][0]
    return dict(finish=c0.get("finish_reason"),
                content=(c0["message"].get("content") or "").strip(),
                completion=d.get("usage", {}).get("completion_tokens") or 0, wall=wall)


def one(args):
    mname, mid, thinking, trial = args
    r, err = None, ""
    for attempt in (1, 2, 3):
        try:
            r = call(mid, thinking); break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:50]}"; time.sleep(2 * attempt)
    base = dict(task="d-multihop", depth="deep", type="多跳算术", model=mname,
                thinking=int(thinking), trial=trial)
    if r is None:
        return dict(**base, correct=0, strict=0, completion=0, reasoning_chars=0,
                    wall=0.0, finish="ERROR", failmode="api_error", note=err, raw="")
    if not r["content"]:
        return dict(**base, correct=0, strict=0, completion=r["completion"], reasoning_chars=0,
                    wall=round(r["wall"], 1), finish=r["finish"],
                    failmode="truncated_empty" if r["finish"] == "length" else "empty",
                    note="content空", raw="")
    c, s, note = v_multihop(r["content"])
    return dict(**base, correct=int(c), strict=int(s), completion=r["completion"], reasoning_chars=0,
                wall=round(r["wall"], 1), finish=r["finish"],
                failmode="" if c else ("truncated" if r["finish"] == "length" else "wrong"),
                note=note[:60], raw=r["content"][:500])


def main():
    print(f"修复后的 d-multihop：GT={D_MULTIHOP_GT}，50 次调用\n")
    jobs = [(mn, mid, th, tr) for mn, mid in MODELS for th in (False, True) for tr in range(1, TRIALS + 1)]
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        for r in ex.map(one, jobs):
            rows.append(r); done += 1
            if done % 10 == 0:
                print(f"  [{done}/{len(jobs)}]", flush=True)

    out = pathlib.Path(__file__).parent / "results_multihop_fix.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"→ {out}\n")

    for th, label in ((0, "off"), (1, "on ")):
        sub = [r for r in rows if r["thinking"] == th and r["finish"] != "ERROR"]
        acc = sum(r["correct"] for r in sub) / len(sub)
        tr = sum(r["finish"] == "length" for r in sub)
        print(f"  {label}: 正确率 {acc*100:3.0f}%  截断 {tr}  n={len(sub)}")
    print("\n  开思考臂的错误明细（若仍有共识错误值 → 题可能还有问题）：")
    for r in rows:
        if r["thinking"] == 1 and r["correct"] == 0 and r["finish"] != "ERROR":
            print(f"    {r['model']:16} {r['note'][:44]}  raw尾: ...{r['raw'][-60:]!r}")


if __name__ == "__main__":
    main()
