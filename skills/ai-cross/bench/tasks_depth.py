"""深度轴任务集：低搜索深度 vs 高搜索深度，用来检验 thinking 旋钮该按什么调。

轴的定义（不是"有无唯一答案"）：
  - shallow：答案**已显式存在于输入**，只需定位/复制/按固定规则转换。全部有唯一答案。
  - deep   ：答案**不在输入里**，必须经多步相互依赖的推导才能造出来。同样全部有唯一答案。

两端都可程序验证 —— 这是刻意的。若 deep 端 thinking=on 明显更好，就证明
"可验证 ⇒ 不需要推理"是错的，真正的变量是搜索深度。

全部自造内容 + 程序化 ground truth（GT 由本文件内的 Python 参考实现算出，不手写）。

判分返回 (correct, strict, note)：
  correct —— 从输出里抽到的答案是否等于 GT（宽容抽取，容忍思考残留/前缀）
  strict  —— 输出是否**只有**答案、无多余文字（格式合规率，独立于正确率）

运行 `python tasks_depth.py` 执行正/负样本自检。
"""
import re
import json as _j


def _clean(s):
    return (s or "").strip()


def _strip_fence(s):
    s = _clean(s)
    s = re.sub(r'^```[a-zA-Z]*\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    return s.strip()


# ══════════════════════════════════════════════════════════════
# SHALLOW：答案已在输入里
# ══════════════════════════════════════════════════════════════

# s1 抽取金额并升序
S_AMOUNTS = ("从下面这段话里抽取所有【人民币金额的数字部分】（不含币种符号和单位），"
             "去重后按数值升序，用英文逗号连接成一行输出，不要任何其他文字。\n"
             "文本：李雷买了3件商品，分别是89元、1200元和45元；退货了一件89元的，"
             "又补买了一件256元的。运费是12元。")
S_AMOUNTS_GT = "12,45,89,256,1200"


def v_amounts(out):
    o = _clean(out)
    m = re.findall(r'-?\d+', o)
    got = ",".join(str(x) for x in sorted({int(x) for x in m}))
    strict = (o == S_AMOUNTS_GT)
    return (got == S_AMOUNTS_GT, strict, f"得到 {got!r}")


# s2/s3/s4 情感分类
SENTI = [
    ("这家店的服务态度好得让我想再来十次。", "正面"),
    ("等了两小时菜还没上，再也不来了。", "负面"),
    ("店在三楼，营业到晚上十点。", "中性"),
]


def senti_prompt(text):
    return f"判断下面这句话的情感，只能回复三个词之一：正面、负面、中性。不要标点，不要解释。\n句子：{text}"


def make_v_senti(expect):
    def v(out):
        o = _clean(out)
        labels = re.findall(r'正面|负面|中性', o)
        g = labels[-1] if labels else o[:6]
        return (g == expect, o == expect, f"得到 {g!r} 期望 {expect!r}")
    return v


# s5 日期归一化
S_DATE = ("把下面的日期改写成 YYYY-MM-DD 格式，只输出改写后的日期一行，不要其他文字。\n"
          "日期：2026年3月7日")
S_DATE_GT = "2026-03-07"


def v_date(out):
    o = _clean(out)
    m = re.search(r'\d{4}-\d{2}-\d{2}', o)
    g = m.group(0) if m else o[:20]
    return (g == S_DATE_GT, o == S_DATE_GT, f"得到 {g!r}")


# s6 结构化抽取
S_JSON = ('从下文抽取信息，只输出一行 JSON，键为 name/age/city，不要 markdown 围栏、不要解释。\n'
          '文本：王芳，今年29岁，目前在成都定居。')


def v_json(out):
    o = _clean(out)
    m = re.search(r'\{.*\}', o, re.S)
    if not m:
        return (False, False, "无 JSON")
    try:
        d = _j.loads(m.group(0))
    except Exception as e:
        return (False, False, f"解析失败 {str(e)[:24]}")
    ok = (str(d.get("name")).strip() == "王芳" and int(d.get("age", -1)) == 29
          and str(d.get("city")).strip() == "成都")
    # prompt 明令"不要 markdown 围栏、不要解释" → 围栏/多行/前后缀一律不合规
    strict = ok and (o == m.group(0).strip()) and ("\n" not in o)
    return (ok, strict, f"name={d.get('name')} age={d.get('age')} city={d.get('city')}")


# ══════════════════════════════════════════════════════════════
# DEEP：答案不在输入里，必须多步推导
#   —— 每题的 GT 都由紧邻的参考实现算出，绝不手写
# ══════════════════════════════════════════════════════════════

# d1 递推：11 步相互依赖，前一步错则全错
def _gt_recur():
    a = 3
    for _ in range(11):
        a = (a * 7 + 11) % 1000
    return a


D_RECUR = ("数列定义：a(1)=3，且对任意 n≥1 有 a(n+1) = (a(n) × 7 + 11) mod 1000。\n"
           "求 a(12) 的值。只输出一个阿拉伯数字，不要过程，不要其他文字。")
D_RECUR_GT = _gt_recur()


def v_recur(out):
    o = _clean(out)
    m = re.findall(r'-?\d+', o)
    g = int(m[-1]) if m else -1
    return (g == D_RECUR_GT, o == str(D_RECUR_GT), f"得到 {g} 期望 {D_RECUR_GT}")


# d2 状态机：12 步操作，需逐步跟踪两个量
def _gt_state():
    red, blue = 5, 3
    ops = [("+r", 4), ("-b", 1), ("+b", 6), ("-r", 3), ("swap", 0), ("+r", 2),
           ("-b", 4), ("double_r", 0), ("+b", 1), ("swap", 0), ("+r", 5), ("-b", 3)]
    for op, k in ops:
        if op == "+r":
            red += k
        elif op == "-r":
            red -= k
        elif op == "+b":
            blue += k
        elif op == "-b":
            blue -= k
        elif op == "swap":
            red, blue = blue, red
        elif op == "double_r":
            red *= 2
        # 任何中间态出现负数，这道题就在考"肯不肯输出荒谬答案"而不是考推理
        assert red >= 0 and blue >= 0, f"中间态出现负数 red={red} blue={blue}（题目设计错误）"
    return red, blue


D_STATE = ("箱子里初始有 5 个红球、3 个蓝球。依次执行下列 12 步操作：\n"
           "1) 加 4 个红球  2) 拿走 1 个蓝球  3) 加 6 个蓝球  4) 拿走 3 个红球\n"
           "5) 红球与蓝球数量互换  6) 加 2 个红球  7) 拿走 4 个蓝球  8) 红球数量翻倍\n"
           "9) 加 1 个蓝球  10) 红球与蓝球数量互换  11) 加 5 个红球  12) 拿走 3 个蓝球\n"
           "求最终红球数和蓝球数。只输出一行，格式为 红,蓝（两个数字用英文逗号分隔），不要其他文字。")
D_STATE_GT = _gt_state()


def v_state(out):
    o = _clean(out)
    m = re.findall(r'-?\d+', o)
    if len(m) < 2:
        return (False, False, f"数字不足: {o[:24]!r}")
    g = (int(m[-2]), int(m[-1]))
    exp = f"{D_STATE_GT[0]},{D_STATE_GT[1]}"
    return (g == D_STATE_GT, o == exp, f"得到 {g} 期望 {D_STATE_GT}")


# d3 约束满足：5 人排座，唯一解，需搜索+排除
def _gt_seat():
    from itertools import permutations
    people = ["甲", "乙", "丙", "丁", "戊"]
    sols = []
    for p in permutations(people):
        pos = {name: i + 1 for i, name in enumerate(p)}
        if pos["甲"] >= pos["乙"]:
            continue                      # 甲在乙左边（位次更小）
        if abs(pos["丙"] - pos["丁"]) != 1:
            continue                      # 丙丁相邻
        if pos["戊"] != 3:
            continue                      # 戊在正中
        if pos["乙"] == 5:
            continue                      # 乙不在最右
        if abs(pos["甲"] - pos["丙"]) <= 1:
            continue                      # 甲丙不相邻
        if pos["丙"] >= pos["丁"]:
            continue                      # 丙在丁左边
        sols.append(p)
    assert len(sols) == 1, f"约束未给出唯一解，共 {len(sols)} 个：{sols}"
    return sols[0]


D_SEAT = ("甲乙丙丁戊五人从左到右坐成一排，座位编号 1 到 5（1 最左）。已知：\n"
          "① 甲的座位号小于乙的座位号\n② 丙和丁的座位相邻\n③ 戊坐在 3 号位\n"
          "④ 乙不坐 5 号位\n⑤ 甲和丙的座位不相邻\n⑥ 丙的座位号小于丁的座位号\n"
          "求从左到右的座位顺序。只输出五个人的姓，按座位 1 到 5 的顺序，"
          "用英文逗号分隔成一行，例如 甲,乙,丙,丁,戊。不要其他文字。")
D_SEAT_GT = _gt_seat()


def v_seat(out):
    o = _clean(out)
    names = re.findall(r'[甲乙丙丁戊]', o)
    # 取最后 5 个（容忍前面的思考残留）
    g = tuple(names[-5:]) if len(names) >= 5 else tuple(names)
    exp = ",".join(D_SEAT_GT)
    return (g == D_SEAT_GT, o == exp, f"得到 {''.join(g)} 期望 {''.join(D_SEAT_GT)}")


# d4 多跳应用题：5 步依赖，中间量不出现在题面
def _gt_multihop():
    # 甲仓库：库存
    jia = 272
    # 乙 = 甲的 3/4 —— 必须整除，否则题面在未声明取整的地方产生小数
    assert jia * 3 % 4 == 0, f"乙不是整数（jia={jia}）"
    yi = jia * 3 // 4
    # 丙 = 甲乙之和的一半再减 30 —— 同上，"一半"必须整除
    # （2026-07-10 教训：jia=260 时丙=197.5，题面没说取整，5 个模型一致按 197.5
    #   忠实计算得出"每店74件剩4.5件"，被判分器当错误——错的是题不是模型。
    #   见 FINDINGS：中间量出现未声明的小数 = 题目病态，断言必须逼停。）
    assert (jia + yi) % 2 == 0, f"丙不是整数（jia+yi={jia + yi}）"
    bing = (jia + yi) // 2 - 30
    assert bing > 0
    # 三仓库各卖出 1/5 后（题面已声明"除不尽时向下取整"，此处允许非整除）
    rem = sum(x - x // 5 for x in (jia, yi, bing))
    per, mod = rem // 7, rem % 7
    # 余数为 0 会让"随手整除"也蒙对，区分度太差
    assert mod != 0, f"余数为 0，区分度不足（rem={rem}）"
    # 答案不得是题面数字的简单倍数/半数
    assert per not in (jia, jia // 2, jia * 2), f"每店件数 {per} 与题面 {jia} 关系过于显然"
    return mod, per


D_MULTIHOP = ("甲仓库有 272 件货。乙仓库的货是甲仓库的四分之三。"
              "丙仓库的货等于甲乙两仓库之和的一半再减去 30 件。\n"
              "三个仓库各自卖出自己库存的五分之一（除不尽时向下取整）。"
              "把三个仓库剩下的货合并，平均分配给 7 个门店（每店整件）。\n"
              "问：每个门店分到多少件，还剩下多少件？"
              "只输出一行，格式为 每店件数,剩余件数（两个数字用英文逗号分隔），不要其他文字。")
_MH = _gt_multihop()
D_MULTIHOP_GT = (_MH[1], _MH[0])   # (每店, 余数)


def v_multihop(out):
    o = _clean(out)
    # 必须识别小数：2026-07-10 曾用 -?\d+ 把模型答的 "4.5" 劈成 4 和 5 两个数，
    # 制造出无法溯源的诡异错误值 (4,5)。数值一律按完整 token 抽取。
    m = re.findall(r'-?\d+(?:\.\d+)?', o)
    if len(m) < 2:
        return (False, False, f"数字不足: {o[:24]!r}")
    g = (float(m[-2]), float(m[-1]))
    gt = (float(D_MULTIHOP_GT[0]), float(D_MULTIHOP_GT[1]))
    exp = f"{D_MULTIHOP_GT[0]},{D_MULTIHOP_GT[1]}"
    shown = tuple(int(x) if x == int(x) else x for x in g)
    return (g == gt, o == exp, f"得到 {shown} 期望 {D_MULTIHOP_GT}")


TASKS = [
    dict(id="s-extract-amounts", depth="shallow", type="抽取", prompt=S_AMOUNTS, verifier=v_amounts),
    dict(id="s-senti-pos", depth="shallow", type="分类", prompt=senti_prompt(SENTI[0][0]), verifier=make_v_senti(SENTI[0][1])),
    dict(id="s-senti-neg", depth="shallow", type="分类", prompt=senti_prompt(SENTI[1][0]), verifier=make_v_senti(SENTI[1][1])),
    dict(id="s-senti-neu", depth="shallow", type="分类", prompt=senti_prompt(SENTI[2][0]), verifier=make_v_senti(SENTI[2][1])),
    dict(id="s-date-norm", depth="shallow", type="格式", prompt=S_DATE, verifier=v_date),
    dict(id="s-json-extract", depth="shallow", type="结构化", prompt=S_JSON, verifier=v_json),

    dict(id="d-recur-11", depth="deep", type="递推", prompt=D_RECUR, verifier=v_recur),
    dict(id="d-statemachine", depth="deep", type="状态跟踪", prompt=D_STATE, verifier=v_state),
    dict(id="d-seat-csp", depth="deep", type="约束满足", prompt=D_SEAT, verifier=v_seat),
    dict(id="d-multihop", depth="deep", type="多跳算术", prompt=D_MULTIHOP, verifier=v_multihop),
]


if __name__ == "__main__":
    print("=== ground truth（由参考实现算出，非手写）===")
    print(f"  d-recur-11     a(12) = {D_RECUR_GT}")
    print(f"  d-statemachine (红,蓝) = {D_STATE_GT}")
    print(f"  d-seat-csp     顺序 = {','.join(D_SEAT_GT)}  （已断言唯一解）")
    print(f"  d-multihop     (每店,余) = {D_MULTIHOP_GT}")

    print("\n=== verifier 正/负样本自检 ===")
    R = str(D_RECUR_GT)
    ST = f"{D_STATE_GT[0]},{D_STATE_GT[1]}"
    SE = ",".join(D_SEAT_GT)
    MH = f"{D_MULTIHOP_GT[0]},{D_MULTIHOP_GT[1]}"
    checks = [
        # (名称, 判分结果, 期望 correct, 期望 strict)
        ("amounts 正/严",     v_amounts(S_AMOUNTS_GT), True, True),
        ("amounts 正/宽",     v_amounts("答案是 12,45,89,256,1200"), True, False),
        ("amounts 负(漏项)",  v_amounts("12,45,89,1200"), False, False),
        ("senti 正/严",       make_v_senti("正面")("正面"), True, True),
        ("senti 正/宽",       make_v_senti("正面")("这句很积极，所以：正面"), True, False),
        ("senti 负",          make_v_senti("正面")("负面"), False, False),
        ("date 正/严",        v_date(S_DATE_GT), True, True),
        ("date 正/宽",        v_date("改写后：2026-03-07"), True, False),
        ("date 负(没补零)",   v_date("2026-3-7"), False, False),
        ("json 正/严",        v_json('{"name":"王芳","age":29,"city":"成都"}'), True, True),
        ("json 正/宽(围栏)",  v_json('```json\n{"name":"王芳","age":29,"city":"成都"}\n```'), True, False),
        ("json 负(city错)",   v_json('{"name":"王芳","age":29,"city":"重庆"}'), False, False),
        ("recur 正/严",       v_recur(R), True, True),
        ("recur 正/宽",       v_recur(f"逐步算得 a(12)={R}"), True, False),
        ("recur 负",          v_recur(str(D_RECUR_GT + 1)), False, False),
        ("state 正/严",       v_state(ST), True, True),
        ("state 正/宽",       v_state(f"最终 {ST}"), True, False),
        ("state 负",          v_state(f"{D_STATE_GT[0]},{D_STATE_GT[1]+1}"), False, False),
        ("seat 正/严",        v_seat(SE), True, True),
        ("seat 正/宽",        v_seat(f"推理后顺序为 {SE}"), True, False),
        ("seat 负(乱序)",     v_seat("戊,丁,丙,乙,甲"), False, False),
        ("multihop 正/严",    v_multihop(MH), True, True),
        ("multihop 正/宽",    v_multihop(f"每店 {D_MULTIHOP_GT[0]} 件，余 {D_MULTIHOP_GT[1]} 件"), True, False),
        ("multihop 负",       v_multihop(f"{D_MULTIHOP_GT[0]+1},{D_MULTIHOP_GT[1]}"), False, False),
    ]
    fails = 0
    for name, (c, s, note), ec, es in checks:
        ok = (c == ec and s == es)
        fails += (not ok)
        print(f"  {'✅' if ok else '❌ BUG'} {name:20} correct={str(c):5}(期望{ec}) "
              f"strict={str(s):5}(期望{es}) | {note[:34]}")

    # 深题的 shallow 化检验：deep 题的答案绝不能出现在题面里
    print("\n=== 深题防泄漏检查（答案字串不得出现在 prompt 中）===")
    leak = 0
    for t, gt in [(D_RECUR, str(D_RECUR_GT)), (D_STATE, ST), (D_SEAT, SE), (D_MULTIHOP, MH)]:
        bad = gt in t
        leak += bad
        print(f"  {'❌ 泄漏' if bad else '✅ 未泄漏'}  GT={gt!r}")

    print("\n" + ("✅ 尺子可信" if not fails and not leak
                  else f"❌ {fails} 项判分错 / {leak} 项泄漏，禁止用于横评"))
