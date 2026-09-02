"""⑤ 植入缺陷的方法学审查：第三档（开放式审查开思考）的第一份可验证证据。

难点：开放式审查没有程序可验证的答案 → 绕法是把 ground truth 埋进去。
两篇伪造"方法"节，各 6 小节（①-⑥），3 节埋硬伤、3 节干净。
模型只输出「有缺陷的节号 + 一句话」→ 按节号机械判分：
  召回 = 报出的缺陷节 ∩ GT；误报 = 报出的干净节。

两个方向的结果都有价值：
  开思考召回显著↑ → 第三档第一次有数据支撑；
  只是输出更长、召回不变 → "更自洽的 rationalization"担忧被证实。

附带一刀（ai-cross 的审查场景验证）：三个模型的并集召回 vs 单模型召回——
换厂商拿第二意见在审查任务上到底补多少漏。

埋的全是硬伤（不可争辩），风格/可改进类不算：
  A②数据泄漏(先全集标准化再划分) A④多重比较未校正 A⑤均值320超出自报范围0.5-86
  B②目标泄漏(输入含可直接算出目标的特征) B④特征重要性→因果跳跃 B⑥检出限5报0.32

n=3、2 臂、3 便宜模型、2 文档 = 36 次调用。存完整 raw。
"""
import json, urllib.request, pathlib, time, csv, re, sys
from concurrent.futures import ThreadPoolExecutor

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"
MODELS = [
    ("Qwen3.6-35B", "Qwen/Qwen3.6-35B-A3B"),
    ("GLM-5.2",     "zai-org/GLM-5.2"),
    ("LongCat-2.0", "meituan-longcat/LongCat-2.0"),
]
TRIALS = 3

DOC_A = """① 研究区位于华北平原东部冲积扇，面积约 1200 km²，属暖温带半湿润季风气候，年均降水 560 mm；土地利用以冬小麦-夏玉米轮作为主，兼有村镇建设用地与蔬菜大棚。
② 共采集地下水样 240 组。建模前，先对全部 240 组样本的 11 项指标做 Z-score 标准化，并基于全体样本与硝酸盐浓度的相关性筛选出 7 个特征，然后按 7:3 随机划分训练集与测试集，训练随机森林回归模型。
③ 水样经 0.45 μm 滤膜现场过滤后装入聚乙烯瓶，4℃ 避光保存，24 小时内采用离子色谱法完成硝酸盐测定。
④ 四个季节的硝酸盐浓度差异比较：对春-夏、春-秋、春-冬、夏-秋、夏-冬、秋-冬共 6 组组合分别进行独立样本 t 检验，均以 P<0.05 判定差异显著。
⑤ 全部样本硝酸盐浓度范围为 0.5–86 mg/L，平均值为 320 mg/L，中位数 12.4 mg/L，变异系数 1.8。
⑥ 质量控制：每批插入 10% 平行样，相对偏差均小于 5%；加标回收率介于 92%–105%；每 20 个样品插入一个空白，空白均低于检出限。"""
GT_A = {"②", "④", "⑤"}

DOC_B = """① 土壤数据来自省级环境监测网 2023 年例行监测，共 156 个表层（0–20 cm）样点，剔除 3 个坐标缺失样点后保留 153 个；测定指标包括 Cd、Pb、As、Cr、Hg 浓度及 pH、有机质。
② 以内梅罗综合污染指数为预测目标训练 XGBoost 模型，输入特征包括五种重金属的实测浓度、各金属的单项污染指数、pH 与有机质含量。
③ 模型采用 500 轮迭代，学习率等超参数经网格搜索确定，模型性能以 10 折交叉验证的 R² 与 RMSE 评估。
④ 特征重要性分析显示 pH 的重要性得分最高（0.31），说明土壤酸化是研究区重金属富集的主要驱动因素。
⑤ 空间制图采用普通克里金插值，半变异函数用球状模型拟合（决定系数 0.87，块金效应 21%），插值精度经留一交叉验证检验。
⑥ 现场筛查采用便携式 XRF，仪器对 Cd 的检出限为 5 mg/kg；据此报告研究区 Cd 平均含量为 0.32 mg/kg。"""
GT_B = {"②", "④", "⑥"}

DOCS = [("A", DOC_A, GT_A), ("B", DOC_B, GT_B)]
ALL_SECS = {"①", "②", "③", "④", "⑤", "⑥"}

PROMPT_TMPL = """以下是一篇论文"方法与结果"部分的六个小节（编号①-⑥）。请找出其中存在明显方法学硬伤的小节。

要求：
- 只报硬伤（逻辑或统计上站不住、数据自相矛盾、流程根本性错误）；文字风格、"可以做得更好"类建议不算。
- 只输出一个 JSON 数组，每项格式 {{"节": "②", "缺陷": "一句话说明"}}。没有硬伤的节不要列。不要输出其他任何文字。

{doc}"""


def call(mid, text, thinking):
    body = {"model": mid, "max_tokens": 16384,
            "messages": [{"role": "user", "content": text}]}
    if not thinking:
        body["enable_thinking"] = False
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", "Bearer " + KEY)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.loads(resp.read())
    c0 = d["choices"][0]
    return dict(finish=c0.get("finish_reason"),
                content=(c0["message"].get("content") or "").strip(),
                completion=d.get("usage", {}).get("completion_tokens") or 0,
                wall=time.time() - t0)


def cited_sections(content):
    """从输出抽被点名的节号。优先解析 JSON；失败则退化为全文找 ①-⑥。"""
    m = re.search(r"\[.*\]", content, re.S)
    if m:
        try:
            items = json.loads(m.group(0))
            secs = set()
            for it in items:
                s = str(it.get("节", "")) if isinstance(it, dict) else str(it)
                secs.update(ch for ch in s if ch in ALL_SECS)
            if secs or items == []:
                return secs, True
        except Exception:
            pass
    return {ch for ch in content if ch in ALL_SECS}, False


def one(args):
    mname, mid, docid, doc, gtset, thinking, trial = args
    r, err = None, ""
    for attempt in (1, 2, 3):
        try:
            r = call(mid, PROMPT_TMPL.format(doc=doc), thinking); break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:40]}"; time.sleep(2 * attempt)
    base = dict(doc=docid, model=mname, thinking=int(thinking), trial=trial)
    if r is None or not r["content"]:
        return dict(**base, hits=0, misses=len(gtset), fps=0, json_ok=0,
                    completion=(r or {}).get("completion", 0),
                    finish=(r or {}).get("finish", "ERROR"),
                    cited="", raw=err if r is None else "(content空)")
    secs, json_ok = cited_sections(r["content"])
    hits = len(secs & gtset)
    fps = len(secs - gtset)
    return dict(**base, hits=hits, misses=len(gtset) - hits, fps=fps, json_ok=int(json_ok),
                completion=r["completion"], finish=r["finish"],
                cited="".join(sorted(secs)), raw=r["content"][:400])


def main():
    jobs = [(mn, mid, did, doc, gt, th, tr)
            for mn, mid in MODELS for did, doc, gt in DOCS
            for th in (False, True) for tr in range(1, TRIALS + 1)]
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(one, jobs):
            rows.append(r); done += 1
            if done % 12 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}]", flush=True)

    out = pathlib.Path(__file__).parent / "results_defects.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n→ {out}\n")

    def agg(th):
        sub = [r for r in rows if r["thinking"] == th and r["finish"] != "ERROR"]
        n = len(sub)
        tot_gt = sum(r["hits"] + r["misses"] for r in sub)
        rec = sum(r["hits"] for r in sub) / tot_gt
        fps = sum(r["fps"] for r in sub) / n
        comp = sorted(r["completion"] for r in sub)[n // 2]
        return rec, fps, comp, n

    print("审查：3 个植入硬伤 / 文档，3 节干净")
    print(f"{'臂':>6}{'召回率':>9}{'误报/次':>9}{'completion中位':>15}{'n':>5}")
    for th, label in ((0, "off"), (1, "on")):
        rec, fps, comp, n = agg(th)
        print(f"{label:>6}{rec*100:>8.0f}%{fps:>9.2f}{comp:>15}{n:>5}")

    # 并集召回：3 模型第二意见的价值（按 doc×trial 聚合并集）
    print("\n单模型 vs 三模型并集（on 臂）：")
    for th in (0, 1):
        per_model = {}
        for mn, _ in MODELS:
            sub = [r for r in rows if r["model"] == mn and r["thinking"] == th]
            tot = sum(r["hits"] + r["misses"] for r in sub)
            per_model[mn] = sum(r["hits"] for r in sub) / tot
        # 并集：同 doc 同 trial，三模型报的节合并后对 GT 的召回
        union_hits = union_tot = 0
        for did, _, gt in DOCS:
            for tr in range(1, TRIALS + 1):
                secs = set()
                for r in rows:
                    if r["doc"] == did and r["trial"] == tr and r["thinking"] == th:
                        secs.update(ch for ch in r["cited"] if ch in ALL_SECS)
                union_hits += len(secs & gt); union_tot += len(gt)
        lab = "off" if th == 0 else "on "
        singles = " / ".join(f"{mn.split('-')[0]} {v*100:.0f}%" for mn, v in per_model.items())
        print(f"  [{lab}] 单模型: {singles}   → 三家并集: {union_hits/union_tot*100:.0f}%")

    print("\n各缺陷节被抓率（on 臂）：")
    for did, _, gt in DOCS:
        for sec in sorted(gt):
            sub = [r for r in rows if r["doc"] == did and r["thinking"] == 1]
            got = sum(sec in r["cited"] for r in sub)
            print(f"  {did}{sec}: {got}/{len(sub)}")
    print("\n误报明细（被点名的干净节，on 臂）：")
    from collections import Counter
    fp_ctr = Counter()
    for r in rows:
        if r["thinking"] == 1:
            did = r["doc"]; gt = dict((d, g) for d, _, g in DOCS)[did]
            for ch in r["cited"]:
                if ch in ALL_SECS - gt:
                    fp_ctr[f"{did}{ch}"] += 1
    for k, v in fp_ctr.most_common():
        print(f"  {k}: {v} 次")


if __name__ == "__main__":
    main()
