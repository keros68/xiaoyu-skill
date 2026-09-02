"""关键探针：Qwen 抽取任务"思考开着就错"，到底是过度推理，还是 max_tokens 截断？

原实验 run_text.py 用 max_tokens=512。探针发现 Qwen baseline 的 completion 恰好 =512（撞顶）。
若拉大预算后思考开着也能答对 → 原结论"思考帮倒忙"是测量假象，必须撤稿。

对每个 (max_tokens) 跑 n 次，记录：
  - finish_reason（length = 被截断，stop = 自然结束）
  - content 是否为空（空 = verifier 被迫读思考残留）
  - 正确率
"""
import json, urllib.request, pathlib, time, sys, re

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks_text import v_amounts, SPEC_AMOUNTS

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "Qwen/Qwen3.6-35B-A3B"

N = 5
BUDGETS = [512, 1024, 2048, 4096]


def call(max_tokens, thinking):
    body = {"model": MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": SPEC_AMOUNTS}]}
    if not thinking:
        body["enable_thinking"] = False
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
    return dict(finish=c0.get("finish_reason"),
                content=(ch.get("content") or "").strip(),
                reasoning=(ch.get("reasoning_content") or "").strip(),
                completion=u.get("completion_tokens"), wall=wall)


def judge(r):
    """复刻 run_text.py 的判分逻辑：content 空时回退思考尾部。"""
    out = r["content"] if r["content"] else r["reasoning"][-200:]
    ok, note = v_amounts(out)
    return ok, note


def main():
    print(f"任务: extract-amounts (期望 12,45,89,256,1200)   模型: {MODEL}   n={N}\n")
    print(f"{'thinking':>9}{'max_tok':>9}{'正确率':>8}{'截断率':>8}{'content空':>10}"
          f"{'completion中位':>14}{'秒中位':>8}")
    print("-" * 70)

    summary = {}
    for thinking in (False, True):
        for mt in ([512] if not thinking else BUDGETS):
            rs = []
            for i in range(N):
                for attempt in (1, 2):
                    try:
                        rs.append(call(mt, thinking)); break
                    except Exception as e:
                        if attempt == 2:
                            print(f"  ERROR {type(e).__name__}: {e}")
                        time.sleep(2)
                time.sleep(0.3)
            if not rs:
                continue
            oks = [judge(r)[0] for r in rs]
            trunc = [r["finish"] == "length" for r in rs]
            empty = [not r["content"] for r in rs]
            comps = sorted(r["completion"] for r in rs)
            walls = sorted(r["wall"] for r in rs)
            med = lambda v: v[len(v) // 2]
            key = ("on" if thinking else "off", mt)
            summary[key] = dict(acc=sum(oks) / len(oks), trunc=sum(trunc) / len(trunc),
                                empty=sum(empty) / len(empty), comp=med(comps), wall=med(walls))
            print(f"{('on' if thinking else 'off'):>9}{mt:>9}{sum(oks)/len(oks)*100:>7.0f}%"
                  f"{sum(trunc)/len(trunc)*100:>7.0f}%{sum(empty)/len(empty)*100:>9.0f}%"
                  f"{med(comps):>14}{med(walls):>8.1f}")

    print("\n" + "=" * 70)
    off = summary.get(("off", 512))
    print("判定：")
    for mt in BUDGETS:
        on = summary.get(("on", mt))
        if not on:
            continue
        if on["trunc"] == 0 and on["acc"] >= 0.8:
            print(f"  ⚠️  thinking=on 在 max_tokens={mt} 下不再截断且正确率 {on['acc']*100:.0f}%"
                  f" → 原'思考帮倒忙'结论是 **max_tokens 截断假象**，必须撤")
            break
    else:
        print("  ✅ 即便预算拉满，thinking=on 仍显著更差 → 原结论成立（过度推理真实存在）")
    if off:
        print(f"\n  参考：thinking=off 正确率 {off['acc']*100:.0f}%，completion 中位 {off['comp']}")

    with (pathlib.Path(__file__).parent / "probe_truncation.json").open("w", encoding="utf-8") as f:
        json.dump({f"{k[0]}-{k[1]}": v for k, v in summary.items()}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
