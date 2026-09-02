"""③ 剂量-响应：深度从 k=1 连续扫到 k=15，画「关思考正确率 vs 深度」曲线。

假设：若"搜索深度"是真变量，off 臂正确率应随 k 单调滑落，on 臂保持平坦；
并能读出一个阈值 k*（关思考仍安全的最大深度）——直接写进路由表。

成本安排（省开支）：
  - 只用 3 个便宜模型：Qwen3.6-35B（A3B 小激活）、GLM-5.2、LongCat-2.0。
    剔除 Kimi（Pro/ 前缀贵 + off 臂漏推理进 content，数据不干净）、DeepSeek-V4-Pro（Pro 档贵）。
  - off 臂便宜（几个 token/次）：全曲线 k=1..15 × 3 模型 × n=3 = 135 次。
  - on 臂贵（数百 token/次）：只采 7 个点 k∈{1,3,5,7,9,12,15} × 3 × 3 = 63 次。
  - 每 trial 换不同的初始值 a1（防提供商缓存 + 防单实例巧合），GT 由参考实现按 (a1,k) 现算。

判分沿用纪律：只看 content；finish=="length" 单独记账；绝不读 reasoning_content。
"""
import json, urllib.request, pathlib, time, csv, sys, re
from concurrent.futures import ThreadPoolExecutor

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"

MODELS = [
    ("Qwen3.6-35B", "Qwen/Qwen3.6-35B-A3B"),
    ("GLM-5.2",     "zai-org/GLM-5.2"),
    ("LongCat-2.0", "meituan-longcat/LongCat-2.0"),
]
K_OFF = list(range(1, 16))
K_ON = [1, 3, 5, 7, 9, 12, 15]
TRIALS = 3
WORKERS = 6


def gt(a1, k):
    a = a1
    for _ in range(k):
        a = (a * 7 + 11) % 1000
    return a


def prompt(a1, k):
    return (f"数列定义：a(1)={a1}，且对任意 n≥1 有 a(n+1) = (a(n) × 7 + 11) mod 1000。\n"
            f"求 a({k+1}) 的值。只输出一个阿拉伯数字，不要过程，不要其他文字。")


def call(mid, text, thinking, max_tokens):
    body = {"model": mid, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": text}]}
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
    mname, mid, k, thinking, trial = args
    # 每 trial 不同初值；GT 是 0-999 的数，可能撞上题面常数（×7、+11、mod 1000、a1 本身）
    # → 在确定性候选序列里挑第一个不泄漏的实例
    for a1 in range(2 + trial, 2 + trial + 40, 3):
        expect = gt(a1, k)
        text = prompt(a1, k)
        if str(expect) not in text:
            break
    else:
        raise RuntimeError(f"k={k} trial={trial} 找不到不泄漏的实例")
    err = ""
    r = None
    for attempt in (1, 2, 3):
        try:
            r = call(mid, text, thinking, 16384 if thinking else 512)
            break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:50]}"
            time.sleep(2 * attempt)
    if r is None:
        return dict(model=mname, k=k, thinking=int(thinking), trial=trial, a1=a1,
                    correct=0, completion=0, wall=0.0, finish="ERROR", note=err)
    if not r["content"]:
        correct, note = 0, f"content空(finish={r['finish']})"
    else:
        m = re.findall(r"-?\d+", r["content"])
        got = int(m[-1]) if m else None
        correct = int(got == expect)
        note = f"得到 {got} 期望 {expect}"
    return dict(model=mname, k=k, thinking=int(thinking), trial=trial, a1=a1,
                correct=correct, completion=r["completion"], wall=round(r["wall"], 1),
                finish=r["finish"], note=note[:50])


def main():
    jobs = ([(mn, mid, k, False, tr) for mn, mid in MODELS for k in K_OFF for tr in range(1, TRIALS + 1)]
            + [(mn, mid, k, True, tr) for mn, mid in MODELS for k in K_ON for tr in range(1, TRIALS + 1)])
    print(f"共 {len(jobs)} 次（off {len(MODELS)*len(K_OFF)*TRIALS} + on {len(MODELS)*len(K_ON)*TRIALS}），并发 {WORKERS}\n")

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(one, jobs):
            rows.append(r); done += 1
            if done % 30 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}]", flush=True)

    out = pathlib.Path(__file__).parent / "results_dose.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n→ {out}\n")

    def acc(k, th, model=None):
        sub = [r for r in rows if r["k"] == k and r["thinking"] == th and r["finish"] != "ERROR"
               and (model is None or r["model"] == model)]
        return sum(r["correct"] for r in sub) / len(sub) if sub else float("nan")

    print("深度 k → 正确率（3 模型汇总，off 全曲线 / on 采样点）")
    print(f"{'k':>4}{'off':>8}{'on':>8}")
    for k in K_OFF:
        on_s = f"{acc(k, 1)*100:6.0f}%" if k in K_ON else "     -"
        print(f"{k:>4}{acc(k, 0)*100:>7.0f}%{on_s:>8}")

    print("\n逐模型 off 曲线：")
    print(f"{'k':>4}" + "".join(f"{mn[:11]:>13}" for mn, _ in MODELS))
    for k in K_OFF:
        print(f"{k:>4}" + "".join(f"{acc(k, 0, mn)*100:>12.0f}%" for mn, _ in MODELS))

    truncs = [r for r in rows if r["finish"] == "length"]
    errs = [r for r in rows if r["finish"] == "ERROR"]
    print(f"\n截断 {len(truncs)} / API失败 {len(errs)}")


if __name__ == "__main__":
    main()
