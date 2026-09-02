"""⛔ 已失效（2026-07-10）——本脚本关于「thinking 对正确率的影响」的一切数字不得引用。

两处叠加的缺陷制造了"思考让模型答错"的假象，见 `FINDINGS-thinking-truncation.md`：
  1. max_tokens=512 太小，推理 token 把答案 token 挤没了（finish_reason=="length"）；
  2. content 为空时回退读 reasoning_content 尾 200 字判分 —— 拿没写完的思考草稿当答案。
预算给到 2048 后，thinking=on 在同一抽取任务上正确率 100%。

接替者：`run_depth.py` + `tasks_depth.py`（判分只看 content，截断单独记账）。
本文件保留仅为历史留痕；其跨模型 token 中位数等不涉及 thinking 对错的观测仍可参考。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

纯文本横评：5 模型 × 7 任务 × 3 轮，全走硅基流动裸 API（无 harness）。

测量纪律（沿用血的教训）：
  - verifier 先过正/负样本自检（tasks_text.py）
  - content 空时回退 reasoning_content 尾 200 字（推理模型可能只填 reasoning）
  - max_tokens=512（够推理模型答完）；默认思考开（out-of-box 行为）
  - 记 prompt/completion token（completion 含推理开销）+ 耗时
  - 单次调用失败重试 1 次；仍失败记 ERROR
"""
import json, urllib.request, urllib.error, pathlib, time, statistics, csv, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks_text import TASKS_TEXT

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"
MODELS = [
    ("Qwen3.6-35B",   "Qwen/Qwen3.6-35B-A3B"),
    ("GLM-5.2",        "zai-org/GLM-5.2"),
    ("DeepSeek-V4-Pro","deepseek-ai/DeepSeek-V4-Pro"),
    ("Kimi-K2.6",      "Pro/moonshotai/Kimi-K2.6"),
    ("LongCat-2.0",    "meituan-longcat/LongCat-2.0"),
]

def call(model_id, prompt, max_tokens=512):
    body = json.dumps({"model": model_id, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(URL, data=body, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", "Bearer " + KEY)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        d = json.loads(resp.read())
    wall = time.time() - t0
    ch = (d.get("choices") or [{}])[0].get("message", {})
    content = (ch.get("content") or "").strip()
    reasoning = (ch.get("reasoning_content") or "").strip()
    out = content if content else reasoning[-200:]   # 回退推理尾部
    u = d.get("usage", {})
    return dict(out=out, used_reasoning=(not content and bool(reasoning)),
                prompt=u.get("prompt_tokens"), completion=u.get("completion_tokens"), wall=wall)

def main():
    trials = 3
    rows = []
    total = len(MODELS) * len(TASKS_TEXT) * trials
    n = 0
    for name, mid in MODELS:
        for t in TASKS_TEXT:
            for tr in range(1, trials + 1):
                n += 1
                res, err = None, ""
                for attempt in (1, 2):
                    try:
                        res = call(mid, t["prompt"]); break
                    except Exception as e:
                        err = f"{type(e).__name__}: {str(e)[:80]}"; time.sleep(2)
                if res is None:
                    correct, note, res = 0, err, dict(out="", used_reasoning=False, prompt=None, completion=None, wall=0)
                else:
                    ok, note = t["verifier"](res["out"])
                    correct = int(ok)
                rows.append(dict(task=t["id"], type=t["type"], model=name, trial=tr,
                                 correct=correct, prompt=res["prompt"], completion=res["completion"],
                                 wall=round(res["wall"], 1), reasoning=int(res["used_reasoning"]),
                                 note=note[:60]))
                print(f"[{n}/{total}] {t['id']:16} {name:15} t{tr} "
                      f"{'✅' if correct else '❌'} c={res['completion']} {res['wall']:.1f}s | {note[:35]}",
                      flush=True)

    with (pathlib.Path(__file__).parent / "results_text.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    def med(v):
        v = [x for x in v if x is not None]
        return int(statistics.median(v)) if v else 0

    print("\n" + "=" * 78)
    print(f"{'模型':16}{'正确率':>7}{'prompt中位':>11}{'completion中位':>14}{'秒中位':>7}")
    print("-" * 78)
    for name, _ in MODELS:
        sub = [r for r in rows if r["model"] == name]
        acc = sum(r["correct"] for r in sub) / len(sub)
        print(f"{name:16}{acc*100:6.0f}%{med(r['prompt'] for r in sub):11d}"
              f"{med(r['completion'] for r in sub):14d}{statistics.median(r['wall'] for r in sub):7.1f}")
    print("=" * 78)

    print("\n各任务正确率（%）:")
    print(f"{'任务':18}" + "".join(f"{name[:10]:>11}" for name, _ in MODELS))
    for t in TASKS_TEXT:
        line = f"{t['id']:18}"
        for name, _ in MODELS:
            sub = [r for r in rows if r["model"] == name and r["task"] == t["id"]]
            acc = sum(r["correct"] for r in sub) / len(sub) if sub else 0
            line += f"{acc*100:>10.0f}%"
        print(line)

if __name__ == "__main__":
    main()
