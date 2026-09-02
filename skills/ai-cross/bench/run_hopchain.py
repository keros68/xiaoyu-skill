"""④ 多跳定位：答案【字面就在输入里】，但需要沿链跳 h 步才能定位。

这是拆混淆变量的关键实验：
  现有深度轴里，"答案在输入里"和"浅"是绑死的。本实验把它们解耦——
  城市名就印在输入文本中（纯定位任务），但定位路径需要 h 次相互依赖的跳转。
  若 off 臂正确率随 h 滑落，则真变量是**深度**，"答案在不在输入里"只是深度的代理；
  若 off 臂全程平坦，则"答案在输入里"本身就是保护因素，轴的表述保持现状。

设计：
  - 12 人，每人「住在」一个不同城市；部分人有「导师」关系构成链。
  - 问「X 的导师的导师…住在哪个城市」（h 跳）。中间每个人城市互不相同 →
    早停 k<h 步必然得到错误城市（可区分"跳了几步"）。
  - 事实顺序用种子打乱；每 trial 换种子生成新实例（防缓存/巧合）。
  - 自检断言：链唯一、无环、中间城市互异、目标城市在文本中恰出现一次。

成本：3 便宜模型 × h∈{1..5} × 2 臂 × n=3 = 90 次。off 臂几 token，on 臂几百。
"""
import json, urllib.request, pathlib, time, csv, random, sys, re
from concurrent.futures import ThreadPoolExecutor

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"
MODELS = [
    ("Qwen3.6-35B", "Qwen/Qwen3.6-35B-A3B"),
    ("GLM-5.2",     "zai-org/GLM-5.2"),
    ("LongCat-2.0", "meituan-longcat/LongCat-2.0"),
]
HOPS = [1, 2, 3, 4, 5]
TRIALS = 3

PEOPLE = ["张伟", "李娜", "王强", "赵敏", "刘洋", "陈静", "杨光", "周杰", "吴丹", "郑爽", "孙浩", "冯雪"]
CITIES = ["杭州", "成都", "西安", "长沙", "青岛", "昆明", "厦门", "沈阳", "兰州", "南宁", "贵阳", "哈尔滨"]


def gen_instance(h, seed):
    """返回 (facts_text, question, gt_city)。链上 h 跳：p0 -导师-> p1 ... -> p_h 住在 gt。"""
    rng = random.Random(seed)
    people = rng.sample(PEOPLE, len(PEOPLE))
    cities = rng.sample(CITIES, len(CITIES))
    chain = people[:h + 1]                      # p0..p_h
    city_of = {p: c for p, c in zip(people, cities)}   # 每人城市互不相同

    facts = [f"{p}住在{city_of[p]}。" for p in people]
    facts += [f"{chain[i]}的导师是{chain[i + 1]}。" for i in range(h)]
    # 干扰导师边：链外的人之间加 3 条（不指向链上任何人，保证链唯一）
    others = people[h + 1:]
    for i in range(3):
        a, b = others[2 * i], others[2 * i + 1]
        facts.append(f"{a}的导师是{b}。")
    rng.shuffle(facts)

    q = chain[0] + "的导师" * h + "住在哪个城市？"
    gt = city_of[chain[h]]

    text = "已知信息：\n" + "\n".join(facts) + f"\n\n问题：{q}\n只输出城市名两个到三个字，不要其他文字。"

    # ── 自检断言 ──
    assert text.count(gt) == 1, f"目标城市在文本中出现 {text.count(gt)} 次"
    inter = {city_of[p] for p in chain[:-1]}
    assert gt not in inter, "早停城市与目标城市撞了"
    assert len(inter) == h, "中间城市有重复"
    return text, gt


def call(mid, text, thinking):
    body = {"model": mid, "max_tokens": 8192 if thinking else 64,
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


def one(args):
    mname, mid, h, thinking, trial = args
    text, gt = gen_instance(h, seed=1000 * h + trial)
    r, err = None, ""
    for attempt in (1, 2, 3):
        try:
            r = call(mid, text, thinking); break
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:40]}"; time.sleep(2 * attempt)
    base = dict(model=mname, h=h, thinking=int(thinking), trial=trial)
    if r is None:
        return dict(**base, correct=0, completion=0, finish="ERROR", note=err, raw="")
    if not r["content"]:
        return dict(**base, correct=0, completion=r["completion"], finish=r["finish"],
                    note="content空", raw="")
    found = [c for c in CITIES if c in r["content"]]
    got = found[-1] if found else r["content"][:8]
    return dict(**base, correct=int(got == gt), completion=r["completion"],
                finish=r["finish"], note=f"得到 {got} 期望 {gt}", raw=r["content"][:200])


def main():
    # 生成器自检：全部 (h, trial) 实例断言过
    for h in HOPS:
        for tr in range(1, TRIALS + 1):
            gen_instance(h, seed=1000 * h + tr)
    print("生成器自检通过（链唯一/城市互异/目标唯一出现）\n")

    jobs = [(mn, mid, h, th, tr) for mn, mid in MODELS for h in HOPS
            for th in (False, True) for tr in range(1, TRIALS + 1)]
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(one, jobs):
            rows.append(r); done += 1
            if done % 20 == 0 or done == len(jobs):
                print(f"  [{done}/{len(jobs)}]", flush=True)

    out = pathlib.Path(__file__).parent / "results_hopchain.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n→ {out}\n")

    def acc(h, th):
        sub = [r for r in rows if r["h"] == h and r["thinking"] == th and r["finish"] != "ERROR"]
        return sum(r["correct"] for r in sub) / len(sub) if sub else float("nan")

    print("答案在输入里，但要跳 h 步定位（3 模型汇总）")
    print(f"{'h':>4}{'off':>8}{'on':>8}")
    for h in HOPS:
        print(f"{h:>4}{acc(h, 0)*100:>7.0f}%{acc(h, 1)*100:>7.0f}%")
    errs = [r for r in rows if r["finish"] == "ERROR"]
    truncs = [r for r in rows if r["finish"] == "length"]
    print(f"\nAPI失败 {len(errs)} / 截断 {len(truncs)}")


if __name__ == "__main__":
    main()
