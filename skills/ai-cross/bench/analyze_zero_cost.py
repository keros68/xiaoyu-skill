"""零新增调用的两项分析，挖 results_depth.csv + results_deep_on16k.csv。

① 跨厂商错误独立性 —— ai-cross 核心前提的首次量化
   关键指标不是"谁错得多"，而是：**两个模型错的时候，错得一样吗？**
   交叉验证只在"错得不一样"时才有用（分歧暴露错误）；
   若两家给出同一个错误答案（共识错误），交叉验证会把错的当成对的。
   对比：同厂商两次采样的"共识错误率" vs 跨厂商的"共识错误率"。

② 自一致性探针 —— 用"关思考跑 3 次是否一致"机械判断任务深浅
   浅任务：模型在复制输入，次次一致；深任务：模型在瞎猜，答案发散。
   若灵敏度/特异度够高，路由就不用"让 agent 自己判断深度"了。
"""
import csv, pathlib, re, itertools
from collections import defaultdict

HERE = pathlib.Path(__file__).parent


def load(name):
    with (HERE / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


rows = load("results_depth.csv")
rows_on16k = load("results_deep_on16k.csv")
# 与 analyze_depth.py 相同的合并规则：deep×on 整格替换为 16k 补跑
merged = [r for r in rows if not (r["depth"] == "deep" and r["thinking"] == "1")] + rows_on16k
merged = [r for r in merged if r["finish"] != "ERROR"]


def parse_answer(note, task):
    """从 note 字段抽出模型给的答案值（用于比较两次作答是否相同）。"""
    if task == "json-extract" or note.startswith("name="):
        return note.strip()
    m = re.match(r"得到\s+(.+?)(?:\s+期望|$)", note)
    return m.group(1).strip() if m else note.strip()


# ════════════════════════════════════════════════════════
# ① 共识错误率：同厂商 vs 跨厂商
# ════════════════════════════════════════════════════════
print("=" * 88)
print("① 跨厂商错误独立性（ai-cross 核心前提量化）")
print("=" * 88)

# 收集每个 (arm, task, model) 的错误答案值列表
wrongs = defaultdict(list)   # (thinking, task) -> {model: [错误答案值]}
for r in merged:
    if r["correct"] == "0" and r["failmode"] == "wrong":
        wrongs[(r["thinking"], r["task"])].append((r["model"], parse_answer(r["note"], r["task"])))

def consensus_rates(arm_filter):
    same_pairs = cross_pairs = 0
    same_hit = cross_hit = 0
    for (th, task), lst in wrongs.items():
        if th != arm_filter:
            continue
        for (m1, a1), (m2, a2) in itertools.combinations(lst, 2):
            if m1 == m2:
                same_pairs += 1
                same_hit += (a1 == a2)
            else:
                cross_pairs += 1
                cross_hit += (a1 == a2)
    return same_pairs, same_hit, cross_pairs, cross_hit

for arm, label in (("0", "关思考"), ("1", "开思考")):
    sp, sh, cp, ch = consensus_rates(arm)
    print(f"\n  [{label}臂] 同一任务上两个「错误答案」相同的概率：")
    if sp:
        print(f"    同厂商（同模型两次采样）: {sh}/{sp} = {sh/sp*100:.0f}%")
    else:
        print(f"    同厂商: 无足够错误样本")
    if cp:
        print(f"    跨厂商（不同模型）      : {ch}/{cp} = {ch/cp*100:.0f}%")
    else:
        print(f"    跨厂商: 无足够错误样本")

# 任务难度画像相关：模型间的逐任务错误率相关系数（错误是否集中在同一批任务上）
print("\n  逐任务错误率画像的模型间相关（off 臂，Pearson）:")
models = sorted({r["model"] for r in merged})
tasks = sorted({r["task"] for r in merged})
err = {m: [] for m in models}
for m in models:
    for t in tasks:
        sub = [r for r in merged if r["model"] == m and r["task"] == t and r["thinking"] == "0"]
        err[m].append(sum(r["correct"] == "0" for r in sub) / max(len(sub), 1))

def pearson(a, b):
    n = len(a); ma, mb = sum(a)/n, sum(b)/n
    cov = sum((x-ma)*(y-mb) for x, y in zip(a, b))
    va = sum((x-ma)**2 for x in a) ** 0.5
    vb = sum((y-mb)**2 for y in b) ** 0.5
    return cov/(va*vb) if va*vb else float("nan")

cors = [pearson(err[m1], err[m2]) for m1, m2 in itertools.combinations(models, 2)]
print(f"    {len(cors)} 对模型的相关系数：min {min(cors):.2f} / 中位 {sorted(cors)[len(cors)//2]:.2f} / max {max(cors):.2f}")
print("    （高相关 = 大家在同一批任务上栽 —— 难度驱动，属预期；关键量是上面的共识错误率）")

# ════════════════════════════════════════════════════════
# ② 自一致性探针
# ════════════════════════════════════════════════════════
print("\n" + "=" * 88)
print("② 自一致性探针：关思考跑 3 次，答案不一致 ⇒ 判为深任务")
print("=" * 88)

# 每 (model, task) 取 off 臂前 3 个 trial 的答案值
probe = {}
for m in models:
    for t in tasks:
        sub = sorted([r for r in merged if r["model"] == m and r["task"] == t and r["thinking"] == "0"],
                     key=lambda r: int(r["trial"]))[:3]
        if len(sub) < 3:
            continue
        answers = [parse_answer(r["note"], t) for r in sub]
        depth = sub[0]["depth"]
        probe[(m, t)] = (len(set(answers)) > 1, depth)   # 不一致?, 真实深度

# 混淆矩阵（探针预测 deep vs 实际 deep）
tp = sum(1 for v in probe.values() if v[0] and v[1] == "deep")
fn = sum(1 for v in probe.values() if not v[0] and v[1] == "deep")
fp = sum(1 for v in probe.values() if v[0] and v[1] == "shallow")
tn = sum(1 for v in probe.values() if not v[0] and v[1] == "shallow")
print(f"\n  以 (模型×任务) 为单位，共 {len(probe)} 格：")
print(f"    深任务被探中（不一致）  : {tp}/{tp+fn}  灵敏度 {tp/(tp+fn)*100:.0f}%")
print(f"    浅任务误报（不一致）    : {fp}/{fp+tn}  特异度 {tn/(fp+tn)*100:.0f}%")

print("\n  漏网的深任务格（3 次答案一致但其实是深任务）：")
for (m, t), (inc, d) in sorted(probe.items()):
    if d == "deep" and not inc:
        sub = [r for r in merged if r["model"] == m and r["task"] == t and r["thinking"] == "0"]
        acc = sum(r["correct"] == "1" for r in sub) / len(sub)
        print(f"    {m:18} {t:16} off臂正确率 {acc*100:.0f}%  ← {'一致且对（无害漏网）' if acc >= 0.8 else '一致且错（危险：稳定的假数字）'}")

print("\n  误报的浅任务格：")
for (m, t), (inc, d) in sorted(probe.items()):
    if d == "shallow" and inc:
        print(f"    {m:18} {t:16}")
