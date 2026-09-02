"""①(判定性) 跨节深缺陷审查：第三档的生死测试。

⑤ 证明单节内硬伤（浅缺陷）不吃思考。本测试埋的缺陷**在任何单节内都成立**，
只有把两节信息链起来才能发现 —— 按深度轴预测，这才是思考的有效区：
  开思考召回显著↑ → 轴统一到审查任务，第三档"高 thinking"保住（换措辞）；
  仍无增益        → 路由表"审查→高 thinking"整行降级。

缺陷设计（每个都需要跨节配对，锚节自身干净）：
  C③×C①  训练+测试 = 130+31 = 161 ≠ ①的 153 组
  C④×C①  t 检验 df=120，但 ①说丰水 78+枯水 75 → df 应为 151
  C⑥×C②  ⑥按"以 N 计"算超标率，②明说结果以 NO3⁻ 计（差 4.43 倍基准）
  D③×D①  特征用"6 种重金属"，①明说测了 8 种
  D④×D①  十折交叉验证"每折约 30 个"，①共 153 样点 → 每折应约 15
  D⑥×D⑤  插值图 3–15 mg/kg，⑤实测范围 0.05–0.83 → 预测超实测 ~20 倍

判分：命中 = 点名缺陷节（③④⑥）。点名锚节（①②⑤）计中性（它们是矛盾的另一方，
不算错也不算对）；误报池 = 完全无关的干净节（C⑤/D②）。
3 便宜模型 × 2 臂 × n=3 × 2 文档 = 36 次。存完整 raw。
"""
import json, urllib.request, pathlib, time, csv, re
from concurrent.futures import ThreadPoolExecutor

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"
MODELS = [
    ("Qwen3.6-35B", "Qwen/Qwen3.6-35B-A3B"),
    ("GLM-5.2",     "zai-org/GLM-5.2"),
    ("LongCat-2.0", "meituan-longcat/LongCat-2.0"),
]
TRIALS = 3

DOC_C = """① 2024 年 5 月（丰水期）与 11 月（枯水期）分两次采样，共取得地下水样 153 组，其中丰水期 78 组、枯水期 75 组，采样井均为农用灌溉井。
② 硝酸盐采用离子色谱法测定，测定结果均以硝酸根离子（NO3⁻）计，单位 mg/L；检出限 0.08 mg/L。
③ 随机森林建模时，将全部样本按约 8:2 划分为训练集与测试集，其中训练集 130 组、测试集 31 组，划分前对特征做了归一化处理（归一化参数仅由训练集拟合）。
④ 丰水期与枯水期硝酸盐浓度差异采用独立样本 t 检验，结果 t=3.42，自由度 df=120，P<0.01，差异显著。
⑤ 质量控制：每批插入 10% 平行样（相对偏差<5%）与试剂空白（均低于检出限），并以标准样品 GSB07-3164 进行准确度核查，测定值均落在保证值范围内。
⑥ 以饮用水中硝酸盐限值 10 mg/L（以 N 计）为标准判定超标情况，直接将各样品测定值与 10 mg/L 比较，得到研究区超标率为 61%。"""
GT_C = {"③", "④", "⑥"}
ANCHOR_C = {"①", "②"}
CLEAN_C = {"⑤"}

DOC_D = """① 本研究测定了 8 种重金属元素（Cd、Pb、As、Cr、Hg、Cu、Zn、Ni）。样点共 153 个，其中农田 96 个、林地 57 个。
② 采样按 500 m × 500 m 网格布设，采集 0–20 cm 表层土，四分法缩分至 1 kg，风干过 100 目筛后保存。
③ 随机森林模型的输入特征为 6 种重金属的实测浓度加 pH 与有机质，共 8 个特征；目标变量为综合生态风险指数。
④ 模型评估采用十折交叉验证，全部样点参与，每折约 30 个样点，以各折 R² 的均值报告模型性能。
⑤ 样品经 HNO3-HCl-HF 微波消解后用 ICP-MS 测定；Cd 的实测浓度范围为 0.05–0.83 mg/kg，加标回收率 91%–106%。
⑥ 基于普通克里金插值绘制 Cd 空间分布图，图中全区 Cd 预测含量介于 3–15 mg/kg，高值区集中在东南部工业园周边。"""
GT_D = {"③", "④", "⑥"}
ANCHOR_D = {"①", "⑤"}
CLEAN_D = {"②"}

DOCS = [("C", DOC_C, GT_C, ANCHOR_C, CLEAN_C), ("D", DOC_D, GT_D, ANCHOR_D, CLEAN_D)]
ALL_SECS = {"①", "②", "③", "④", "⑤", "⑥"}

PROMPT_TMPL = """以下是一篇论文"方法与结果"部分的六个小节（编号①-⑥）。请找出其中存在明显方法学硬伤的小节。

要求：
- 只报硬伤（逻辑或统计上站不住、数据自相矛盾、流程根本性错误）；文字风格、"可以做得更好"类建议不算。
- 注意通读全文：有些问题需要对照不同小节才能发现。
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
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.loads(resp.read())
    c0 = d["choices"][0]
    return dict(finish=c0.get("finish_reason"),
                content=(c0["message"].get("content") or "").strip(),
                completion=d.get("usage", {}).get("completion_tokens") or 0)


def cited_sections(content):
    m = re.search(r"\[.*\]", content, re.S)
    if m:
        try:
            items = json.loads(m.group(0))
            secs = set()
            for it in items:
                s = str(it.get("节", "")) if isinstance(it, dict) else str(it)
                secs.update(ch for ch in s if ch in ALL_SECS)
            return secs, True
        except Exception:
            pass
    return {ch for ch in content if ch in ALL_SECS}, False


def one(args):
    mname, mid, docid, doc, gt, anchor, clean, thinking, trial = args
    r, err = None, ""
    for attempt in (1, 2, 3):
        try:
            r = call(mid, PROMPT_TMPL.format(doc=doc), thinking); break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:40]}"; time.sleep(2 * attempt)
    base = dict(doc=docid, model=mname, thinking=int(thinking), trial=trial)
    if r is None or not r["content"]:
        return dict(**base, hits=0, fps=0, neutral=0, json_ok=0, completion=0,
                    finish="ERROR" if r is None else r["finish"], cited="", raw=err)
    secs, json_ok = cited_sections(r["content"])
    return dict(**base,
                hits=len(secs & gt), fps=len(secs & clean), neutral=len(secs & anchor),
                json_ok=int(json_ok), completion=r["completion"], finish=r["finish"],
                cited="".join(sorted(secs)), raw=r["content"][:400])


def main():
    jobs = [(mn, mid, did, doc, gt, an, cl, th, tr)
            for mn, mid in MODELS for did, doc, gt, an, cl in DOCS
            for th in (False, True) for tr in range(1, TRIALS + 1)]
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(one, jobs):
            rows.append(r); done += 1
            if done % 12 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}]", flush=True)

    out = pathlib.Path(__file__).parent / "results_defects_deep.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n→ {out}\n")

    print("跨节深缺陷（每个缺陷都需把两节链起来才能发现）")
    print(f"{'臂':>6}{'召回率':>9}{'误报/次':>9}{'completion中位':>15}{'n':>5}")
    for th, label in ((0, "off"), (1, "on")):
        sub = [r for r in rows if r["thinking"] == th and r["finish"] != "ERROR"]
        tot = 3 * len(sub)
        rec = sum(r["hits"] for r in sub) / tot
        fps = sum(r["fps"] for r in sub) / len(sub)
        comp = sorted(r["completion"] for r in sub)[len(sub) // 2]
        print(f"{label:>6}{rec*100:>8.0f}%{fps:>9.2f}{comp:>15}{len(sub):>5}")

    print("\n各缺陷节被抓率：")
    print(f"{'缺陷':>8}{'off':>8}{'on':>8}")
    for did, _, gt, _, _ in DOCS:
        for sec in sorted(gt):
            line = f"{did}{sec:>4}"
            for th in (0, 1):
                sub = [r for r in rows if r["doc"] == did and r["thinking"] == th and r["finish"] != "ERROR"]
                line += f"{sum(sec in r['cited'] for r in sub):>7}/{len(sub)}"
            print(line)

    print("\n单模型召回 vs 三家并集：")
    for th in (0, 1):
        per = {}
        for mn, _ in MODELS:
            sub = [r for r in rows if r["model"] == mn and r["thinking"] == th and r["finish"] != "ERROR"]
            per[mn] = sum(r["hits"] for r in sub) / (3 * len(sub)) if sub else 0
        uh = ut = 0
        for did, _, gt, _, _ in DOCS:
            for tr in range(1, TRIALS + 1):
                secs = set()
                for r in rows:
                    if r["doc"] == did and r["trial"] == tr and r["thinking"] == th:
                        secs.update(ch for ch in r["cited"] if ch in ALL_SECS)
                uh += len(secs & gt); ut += len(gt)
        lab = "off" if th == 0 else "on "
        singles = " / ".join(f"{mn.split('-')[0]} {v*100:.0f}%" for mn, v in per.items())
        print(f"  [{lab}] {singles}   → 并集 {uh/ut*100:.0f}%")


if __name__ == "__main__":
    main()
