"""补跑：deep × thinking=on，max_tokens 加到 16384，消除截断。

为什么必须重跑：run_depth.py 主跑里 12/500 次截断**全部**落在 deep+on 这一格
（d-multihop 8 次撞满 4096）。按本项目纪律，finish_reason=="length" 的格子
其正确率不可用于比较 —— 截断被记为答错，会**低估** thinking 在深任务上的收益。

只重跑这一格：shallow 两臂与 deep+off 的截断率均为 0，无需重跑。
产物 results_deep_on16k.csv 与主跑 CSV 合并后重新汇总（见 analyze_depth.py）。
"""
import pathlib, csv, sys, statistics

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run_depth
from tasks_depth import TASKS
from concurrent.futures import ThreadPoolExecutor

run_depth.MAX_TOKENS = 16384          # 4× 主跑；d-multihop 撞满 4096，留足余量
TRIALS = run_depth.TRIALS
DEEP = [t for t in TASKS if t["depth"] == "deep"]


def main():
    jobs = [(mn, mid, t, True, tr)
            for mn, mid in run_depth.MODELS
            for t in DEEP
            for tr in range(1, TRIALS + 1)]
    print(f"补跑 deep × thinking=on × max_tokens={run_depth.MAX_TOKENS}：{len(jobs)} 次\n")

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=run_depth.WORKERS) as ex:
        for r in ex.map(run_depth.one, jobs):
            rows.append(r); done += 1
            if done % 20 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}]", flush=True)

    out = pathlib.Path(__file__).parent / "results_deep_on16k.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n→ {out}")

    truncs = [r for r in rows if r["finish"] == "length"]
    errs = [r for r in rows if r["finish"] == "ERROR"]
    print(f"\n截断: {len(truncs)}/{len(rows)}"
          + ("  ✅ 已消除，该格正确率现在可用" if not truncs else "  ⚠️ 仍有截断，需再加预算"))
    print(f"API 失败: {len(errs)}/{len(rows)}")
    if truncs:
        from collections import Counter
        for (m, t), c in Counter((r["model"], r["task"]) for r in truncs).items():
            print(f"    {m} / {t}: {c} 次")

    acc = sum(r["correct"] for r in rows) / len(rows)
    print(f"\ndeep × on × 16384 正确率: {acc*100:.0f}%  (主跑 4096 下为 80%)")
    print(f"completion 中位: {statistics.median(r['completion'] for r in rows):.0f}")
    print("\n逐任务:")
    for t in DEEP:
        sub = [r for r in rows if r["task"] == t["id"]]
        tr = sum(r["finish"] == "length" for r in sub)
        print(f"  {t['id']:18} {sum(r['correct'] for r in sub)/len(sub)*100:>3.0f}%  "
              f"token中位 {statistics.median(r['completion'] for r in sub):>6.0f}  截断 {tr}")


if __name__ == "__main__":
    main()
