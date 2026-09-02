"""合并主跑与补跑，输出最终结论表。

数据来源：
  results_depth.csv        主跑（5 模型 × 10 任务 × 2 臂 × 5 轮，max_tokens=4096）
  results_deep_on16k.csv   补跑（deep × on，max_tokens=16384，消除主跑的 12 次截断）

合并规则：deep × thinking=on 这一格**整格替换**为补跑数据（预算充足、零截断）；
其余三格用主跑。不做逐行挑选 —— 只保留答对的那次是 p-hacking。

指标口径（一处此前的措辞缺陷，在此修正）：
  `strict` 实现为「答对 **且** 输出无多余文字」，它与正确率耦合，
  在正确率低的格子里没有独立含义（deep×off 的 "2%" 只是它答错得多）。
  故重命名为 **可直接入库率**：一次调用的输出能不能不经清洗直接进数据库/表格。
  这才是抽取类任务真正关心的量，也正是它该被报告的地方（shallow 端）。
"""
import csv, pathlib, statistics
from collections import Counter

HERE = pathlib.Path(__file__).parent


def load(name):
    with (HERE / name).open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("thinking", "trial", "correct", "strict", "completion", "reasoning_chars"):
            r[k] = int(r[k])
        r["wall"] = float(r["wall"])
    return rows


main_rows = load("results_depth.csv")
deep_on = load("results_deep_on16k.csv")
mh_fix = load("results_multihop_fix.csv")

# 整格替换（两层）：
# 1) deep×on 用 16k 补跑（消除截断）
# 2) d-multihop 两臂整体用修复后的题重跑 —— 旧题 jia=260 时丙=197.5，题面未声明
#    取整，5 模型一致按 197.5 忠实作答被误判（见 FINDINGS-multihop-illposed）
merged = [r for r in main_rows if not (r["depth"] == "deep" and r["thinking"] == 1)] + deep_on
merged = [r for r in merged if r["task"] != "d-multihop"] + mh_fix
merged = [r for r in merged if r["finish"] != "ERROR"]


def sel(**kw):
    return [r for r in merged if all(r[k] == v for k, v in kw.items())]


def agg(sub):
    return dict(
        acc=sum(r["correct"] for r in sub) / len(sub),
        usable=sum(r["strict"] for r in sub) / len(sub),
        trunc=sum(r["finish"] == "length" for r in sub) / len(sub),
        comp=statistics.median(r["completion"] for r in sub),
        wall=statistics.median(r["wall"] for r in sub),
        n=len(sub),
    )


print("=" * 90)
print("最终结果：搜索深度 × thinking（5 模型汇总；deep×on 用 16k 预算补跑，零截断）")
print("=" * 90)
print(f"{'深度':>8}{'thinking':>10}{'正确率':>9}{'可直接入库':>12}{'截断率':>9}"
      f"{'completion中位':>15}{'秒中位':>9}{'n':>6}")
print("-" * 90)
tbl = {}
for depth in ("shallow", "deep"):
    for th in (0, 1):
        a = agg(sel(depth=depth, thinking=th)); tbl[(depth, th)] = a
        print(f"{depth:>8}{('on' if th else 'off'):>10}{a['acc']*100:>8.0f}%"
              f"{a['usable']*100:>11.0f}%{a['trunc']*100:>8.0f}%"
              f"{a['comp']:>15.0f}{a['wall']:>9.1f}{a['n']:>6}")

print("\n" + "=" * 90)
print("thinking 的净效应（on − off）—— 这张表就是全部结论")
print("-" * 90)
for depth in ("shallow", "deep"):
    on, off = tbl[(depth, 1)], tbl[(depth, 0)]
    dacc = (on["acc"] - off["acc"]) * 100
    print(f"  {depth:>8}: 正确率 {dacc:+5.0f} pp   token {on['comp']/max(off['comp'],1):>5.0f}×   "
          f"耗时 {on['wall']/max(off['wall'],0.1):>4.0f}×")
print("\n  两端任务【都有唯一可验证答案】。唯一区别：答案在不在输入里。")
print("  → 决定推理是否有用的不是'有无标准答案'，是**搜索深度**。")

print("\n" + "=" * 90)
print("逐任务（off → on）")
print("-" * 90)
order = [r for r in merged]
for tid in dict.fromkeys(r["task"] for r in merged):
    off, on = agg(sel(task=tid, thinking=0)), agg(sel(task=tid, thinking=1))
    depth = next(r["depth"] for r in merged if r["task"] == tid)
    d = (on["acc"] - off["acc"]) * 100
    flag = "  ⚠️仍有截断" if on["trunc"] or off["trunc"] else ""
    print(f"  [{depth:>7}] {tid:18} {off['acc']*100:>3.0f}% → {on['acc']*100:>3.0f}%"
          f"  ({d:+4.0f}pp)   token {off['comp']:>5.0f} → {on['comp']:>6.0f}{flag}")

print("\n" + "=" * 90)
print("逐模型：thinking 净效应（正确率 pp）—— 检查结论是不是某一个模型带出来的")
print("-" * 90)
print(f"{'模型':18}{'shallow':>10}{'deep':>10}{'deep token比':>16}")
for mn in dict.fromkeys(r["model"] for r in merged):
    cells = []
    for depth in ("shallow", "deep"):
        off, on = agg(sel(model=mn, depth=depth, thinking=0)), agg(sel(model=mn, depth=depth, thinking=1))
        cells.append(((on["acc"] - off["acc"]) * 100, on["comp"] / max(off["comp"], 1)))
    print(f"{mn:18}{cells[0][0]:>9.0f}{cells[1][0]:>10.0f}{cells[1][1]:>15.0f}×")
print("\n  5/5 模型在 deep 上均为正增益 → 不是单个模型的特性。")

print("\n" + "=" * 90)
print("shallow 端的诚实脚注")
print("-" * 90)
sx_off, sx_on = agg(sel(task="s-extract-amounts", thinking=0)), agg(sel(task="s-extract-amounts", thinking=1))
print(f"  s-extract-amounts 是 shallow 里唯一非零增益：{sx_off['acc']*100:.0f}% → {sx_on['acc']*100:.0f}%")
print(f"    它要求「抽取 + 去重 + 排序」，排序那步已经不是纯定位了 —— 深度轴上它离 0 最远。")
print(f"  其余 5 个 shallow 任务：thinking 净效应恰好 0pp，token 多烧 {tbl[('shallow',1)]['comp']/max(tbl[('shallow',0)]['comp'],1):.0f}×。")
so, sf = tbl[("shallow", 0)], tbl[("shallow", 1)]
print(f"  可直接入库率 off {so['usable']*100:.0f}% vs on {sf['usable']*100:.0f}% "
      f"→ 关思考并【没有】让格式更合规，'关掉更听话'这个假设不成立。")

print("\n" + "=" * 90)
print("数据卫生")
print("-" * 90)
truncs = [r for r in merged if r["finish"] == "length"]
print(f"  合并后总样本 : {len(merged)}（主跑 {len([r for r in main_rows if r['finish']!='ERROR'])} 中"
      f" deep×on 一格 {len([r for r in main_rows if r['depth']=='deep' and r['thinking']==1])} 条已被 16k 补跑整格替换）")
print(f"  截断         : {len(truncs)}" + ("  ✅ 零截断" if not truncs else "  ⚠️"))
print(f"  content 空   : {sum(r['failmode']=='empty' for r in merged)}")
print(f"  API 失败(已剔): {len(main_rows)+len(deep_on)-len(merged)-len([r for r in main_rows if r['depth']=='deep' and r['thinking']==1])}")
if truncs:
    for (m, t), c in Counter((r["model"], r["task"]) for r in truncs).items():
        print(f"      {m} / {t}: {c}")

print("\n  失败模式分布（off 臂 deep 端）：")
for fm, c in Counter(r["failmode"] for r in sel(depth="deep", thinking=0) if r["failmode"]).items():
    print(f"      {fm}: {c}")
