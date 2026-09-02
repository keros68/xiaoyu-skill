"""纯文本任务集（自造内容，规避训练集污染；程序化 ground truth）。

为什么纯文本：这是中低档模型的主场，也是 FrugalGPT/RouteLLM 的场景，且裸 API 单轮、
方差比 coding 小。全部走硅基流动裸 API（OpenAI 兼容），跨模型同条件对比。

verifier 从 content 抽答案；content 空时回退 reasoning_content 尾部（推理模型可能只填 reasoning）。
运行 `python tasks_text.py` 执行自检。
"""
import re

def _clean(s):
    return (s or "").strip()

# ── 任务 1：抽取金额并升序（考精确抽取 + 排序）──
SPEC_AMOUNTS = ("从下面这段话里抽取所有【人民币金额的数字部分】（不含币种符号和单位），"
                "去重后按数值升序，用英文逗号连接成一行输出，不要任何其他文字。\n"
                "文本：李雷买了3件商品，分别是89元、1200元和45元；退货了一件89元的，"
                "又补买了一件256元的。运费是12元。")
# 金额：89,1200,45,256,12 → 去重升序
AMOUNTS_GT = "12,45,89,256,1200"
def v_amounts(out):
    m = re.findall(r'-?\d+', _clean(out))
    got = ",".join(str(x) for x in sorted({int(x) for x in m}))
    return (got == AMOUNTS_GT, f"得到 {got!r} 期望 {AMOUNTS_GT!r}")

# ── 任务 2：情感分类（考单标签约束遵循）──
SENTI = [
    ("这家店的服务态度好得让我想再来十次。", "正面"),
    ("等了两小时菜还没上，再也不来了。", "负面"),
    ("店在三楼，营业到晚上十点。", "中性"),
]
def make_senti_prompt(text):
    return (f"判断下面这句话的情感，只能回复三个词之一：正面、负面、中性。不要标点，不要解释。\n句子：{text}")
def v_senti(out, expect):
    got = _clean(out)
    # 取最后出现的标签（推理模型可能前面有思考残留）
    labels = re.findall(r'正面|负面|中性', got)
    g = labels[-1] if labels else got[:6]
    return (g == expect, f"得到 {g!r} 期望 {expect!r}")

# ── 任务 3：日期归一化（考格式约束）──
SPEC_DATE = ("把下面的日期改写成 YYYY-MM-DD 格式，只输出改写后的日期一行，不要其他文字。\n"
             "日期：2026年3月7日")
DATE_GT = "2026-03-07"
def v_date(out):
    m = re.search(r'\d{4}-\d{2}-\d{2}', _clean(out))
    g = m.group(0) if m else _clean(out)[:20]
    return (g == DATE_GT, f"得到 {g!r} 期望 {DATE_GT!r}")

# ── 任务 4：数句号（考"模型亲自数"——纯文本版的弱项探针）──
_SENT = "今天天气很好。我们去公园散步。路上买了冰淇淋。回家后看了电影。"
SPEC_COUNT = (f"数一下下面这段文字里有多少个句号（。），只回复一个阿拉伯数字，不要其他文字。\n文字：{_SENT}")
COUNT_GT = _SENT.count("。")  # 4
def v_count(out):
    m = re.search(r'\d+', _clean(out))
    g = int(m.group(0)) if m else -1
    return (g == COUNT_GT, f"得到 {g} 期望 {COUNT_GT}")

# ── 任务 5：结构化抽取 JSON（考结构化输出）──
SPEC_JSON = ('从下文抽取信息，只输出一行 JSON，键为 name/age/city，不要 markdown 围栏、不要解释。\n'
             '文本：王芳，今年29岁，目前在成都定居。')
def v_json(out):
    import json as _j
    m = re.search(r'\{.*\}', _clean(out), re.S)
    if not m:
        return (False, "无 JSON")
    try:
        d = _j.loads(m.group(0))
    except Exception as e:
        return (False, f"JSON 解析失败 {e}")
    ok = (str(d.get("name")).strip() == "王芳" and int(d.get("age", -1)) == 29
          and str(d.get("city")).strip() == "成都")
    return (ok, f"name={d.get('name')} age={d.get('age')} city={d.get('city')}")

TASKS_TEXT = [
    dict(id="extract-amounts", type="抽取", prompt=SPEC_AMOUNTS, verifier=v_amounts),
    dict(id="sentiment-pos", type="分类", prompt=make_senti_prompt(SENTI[0][0]),
         verifier=lambda o: v_senti(o, SENTI[0][1])),
    dict(id="sentiment-neg", type="分类", prompt=make_senti_prompt(SENTI[1][0]),
         verifier=lambda o: v_senti(o, SENTI[1][1])),
    dict(id="sentiment-neu", type="分类", prompt=make_senti_prompt(SENTI[2][0]),
         verifier=lambda o: v_senti(o, SENTI[2][1])),
    dict(id="date-normalize", type="格式", prompt=SPEC_DATE, verifier=v_date),
    dict(id="count-periods", type="亲自数", prompt=SPEC_COUNT, verifier=v_count),
    dict(id="json-extract", type="结构化", prompt=SPEC_JSON, verifier=v_json),
]

if __name__ == "__main__":
    fails = 0
    print("=== verifier 正/负样本自检 ===")
    checks = [
        ("amounts 正", v_amounts("12,45,89,256,1200"), True),
        ("amounts 正(带思考残留)", v_amounts("嗯，让我想想…金额是 12,45,89,256,1200"), True),
        ("amounts 负(漏一个)", v_amounts("12,45,89,1200"), False),
        ("amounts 正(顺序不同集合同)", v_amounts("89,1200,45,256,12"), True),  # 有意顺序无关：只测抽取
        ("senti 正", v_senti("正面", "正面"), True),
        ("senti 正(带思考)", v_senti("这句话很积极，所以：正面", "正面"), True),
        ("senti 负(答错)", v_senti("负面", "正面"), False),
        ("date 正", v_date("2026-03-07"), True),
        ("date 正(带前缀)", v_date("改写后：2026-03-07"), True),
        ("date 负(没补零)", v_date("2026-3-7"), False),
        ("count 正", v_count("4"), True),
        ("count 负(数错)", v_count("3"), False),
        ("json 正", v_json('{"name":"王芳","age":29,"city":"成都"}'), True),
        ("json 正(带围栏)", v_json('```json\n{"name":"王芳","age":29,"city":"成都"}\n```'), True),
        ("json 负(city错)", v_json('{"name":"王芳","age":29,"city":"重庆"}'), False),
    ]
    for name, (got, note), expect in checks:
        ok = (got == expect); fails += (not ok)
        print(f"  {'✅' if ok else '❌ BUG'} {name:24} 判定={str(got):5} 期望={expect} | {note[:40]}")
    print("\n" + ("✅ 尺子可信" if not fails else f"❌ {fails} 项有问题，禁止用于横评"))
