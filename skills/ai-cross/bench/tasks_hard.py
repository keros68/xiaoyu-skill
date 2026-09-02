"""高难度基准任务集（全部自造，规避训练集污染）。

设计约束（来自前几轮踩过的坑）：
  1. ground truth 必须由【参考实现】程序判定，且参考实现自身先过自检。
  2. verifier 必须过正/负样本自检（无假阴性/假阳性）才能使用。
  3. 代码类任务：剥掉模型自带的自测块，只跑我们的用例（测"实现正确性"）；
     另单独记录"交付物完整性"（模型自带自测能否通过）——两个指标不得混为一谈。
  4. 任务须含【真实决策点/歧义】，以便检验 advisor 模式。

运行 `python tasks_hard.py` 执行全部自检。
"""
import re, io, json, contextlib, random

# ── CLI 会在正文后追加横幅；混进 exec() 会造成假阴性（踩过） ──
NOISE = re.compile(r'^(Reading additional input|OpenAI Codex|workdir:|model:|provider:|'
                   r'approval:|sandbox:|reasoning |session id:|-{4,}|user$|codex$|warning:|tokens used)')


def _try_exec(code, must_define):
    """剥掉自测块后执行；成功且定义了目标函数则返回它。"""
    code = re.split(r'^if __name__', code, flags=re.M)[0]
    ns = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(code, "<model>", "exec"), ns)
    except Exception:
        return None
    fn = ns.get(must_define)
    return fn if callable(fn) else None


def _longest_compilable_prefix(lines, must_define):
    """从末尾往回缩，找【能编译执行且定义了目标函数】的最长前缀。

    这样就不必猜"代码在哪结束"——模型在代码后跟一段中文解释时，
    解释行会被自然截掉。（早先靠猜边界，把中文解释当代码 exec，
    产出 `SyntaxError: invalid character '，'` 的假阴性，codex 全线误判 0%。）
    """
    for end in range(len(lines), 0, -1):
        fn = _try_exec("\n".join(lines[:end]), must_define)
        if fn is not None:
            return fn
    return None


def _extract(out, must_define):
    """从模型输出里抽出可执行的实现。优先 ```python 围栏；否则渐进式编译。"""
    src = re.sub(r'\x1b\[[0-9;]*m', '', out)

    candidates = []
    for blk in re.findall(r'```(?:python|py)?\s*\n(.*?)```', src, flags=re.S):
        candidates.append(blk)
    # 无围栏（或围栏里没有目标函数）时：从第一行像代码的地方起，取到 CLI 横幅为止
    lines = src.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if re.match(r'^\s*(from |import |[A-Z_]{2,}\s*=|def |class |#\s*AMBIGUITY)', l)), None)
    if start is not None:
        tail = []
        for l in lines[start:]:
            if NOISE.match(l.strip()):
                break
            tail.append(l)
        candidates.append("\n".join(tail))

    if not candidates:
        return None, "未找到代码起点"
    for cand in candidates:
        cl = [l for l in cand.splitlines() if not l.strip().startswith("```")]
        fn = _longest_compilable_prefix(cl, must_define)
        if fn is not None:
            return fn, ""
    return None, f"未能从输出中提取到可执行的 {must_define}"


def _judge(fn, cases):
    fails = []
    for arg, expect in cases:
        args = arg if isinstance(arg, tuple) else (arg,)
        try:
            got = fn(*args)
            if expect is ValueError:
                fails.append(f"{arg!r} 未抛 ValueError(返回{got!r})")
            elif got != expect:
                fails.append(f"{arg!r}→{got!r} 期望{expect!r}")
        except ValueError:
            if expect is not ValueError:
                fails.append(f"{arg!r} 误抛 ValueError")
        except Exception as e:
            fails.append(f"{arg!r} 抛 {type(e).__name__}")
    return (not fails, "全部通过" if not fails else f"{len(fails)}/{len(cases)}项失败: {fails[:2]}")


# ══════════════════ 任务 1：跨午夜时段语言（自造规格） ══════════════════
SPEC_INTERVAL = """实现 Python 函数 parse_merge(s) -> list[tuple[int,int]]

输入 s 是逗号分隔的时段串，每段格式严格为 "HH:MM-HH:MM"（两位零填充，24小时制，HH 取 00..23，MM 取 00..59）。

规则：
1. 每段转为分钟数 [start, end)，end 独占。start = HH*60+MM。
2. 若某段的 end <= start，视为【跨午夜】，拆成两段：[start, 1440) 和 [0, end)。
   例："23:00-01:00" → [1380,1440) 与 [0,60)。
   特例：若 end == start，抛 ValueError（零长度非法，不算跨午夜）。
3. 合并所有重叠【或相邻】的段。相邻指前段 end == 后段 start，例 [0,60) 与 [60,120) 合并为 [0,120)。
4. 返回按 start 升序排列的 (start, end) 元组列表。
5. 空字符串返回 []。
6. 任何格式不合法（非两位数字、缺冒号、缺连字符、HH>23、MM>59、多余空白）抛 ValueError。
7. 不修改入参。

请把【完整的 Python 代码】直接写在你最终回复的正文里（用 ```python 围栏）。
不要执行任何命令，不要写入任何文件，不要只描述思路，不要反问。代码之后不要再追加说明。"""

def ref_parse_merge(s):
    if not isinstance(s, str):
        raise ValueError("need str")
    if s == "":
        return []
    segs = []
    for part in s.split(","):
        if not re.fullmatch(r'\d{2}:\d{2}-\d{2}:\d{2}', part):
            raise ValueError(f"bad segment {part!r}")
        h1, m1, h2, m2 = int(part[0:2]), int(part[3:5]), int(part[6:8]), int(part[9:11])
        for h, m in ((h1, m1), (h2, m2)):
            if h > 23 or m > 59:
                raise ValueError("out of range")
        a, b = h1 * 60 + m1, h2 * 60 + m2
        if a == b:
            raise ValueError("zero length")
        if b < a:
            segs.append((a, 1440)); segs.append((0, b))
        else:
            segs.append((a, b))
    segs.sort()
    merged = [list(segs[0])]
    for a, b in segs[1:]:
        if a <= merged[-1][1]:              # 重叠或相邻
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [tuple(x) for x in merged]

INTERVAL_CASES = [
    ("09:00-10:30,13:15-14:00", [(540, 630), (795, 840)]),
    ("23:00-01:00", [(0, 60), (1380, 1440)]),
    ("23:00-01:00,00:30-02:00", [(0, 120), (1380, 1440)]),
    ("01:00-02:00,02:00-03:00", [(60, 180)]),          # 相邻必须合并
    ("", []),
    ("10:00-10:00", ValueError),                        # 零长度
    ("24:00-01:00", ValueError),                        # HH 越界
    ("9:00-10:00", ValueError),                         # 非两位
    ("09:00 - 10:00", ValueError),                      # 多余空白
    ("22:00-23:00,23:00-01:00", [(0, 60), (1320, 1440)]),  # 相邻 + 跨午夜
]

def v_interval(out):
    fn, err = _extract(out, "parse_merge")
    if fn is None:
        return (False, err)
    return _judge(fn, INTERVAL_CASES)


# ══════════════════ 任务 2：自造校验和（纯精确性） ══════════════════
SPEC_CHECKSUM = """实现 Python 函数 checksum(data: bytes) -> int，严格按以下算法：

acc = 0
对 data 中每个字节 b（下标 i 从 0 开始）：
  若 i % 3 == 0：  acc = (acc + b * 7) % 65521
  若 i % 3 == 1：  acc = (acc ^ (b << 1)) & 0xFFFF
  若 i % 3 == 2：  acc = (acc - b) % 65521
遍历结束后返回 (acc * 31 + len(data)) % 65521

注意：Python 的 % 对负数返回非负结果，必须保持这一语义。
输入非 bytes 抛 TypeError。空 bytes 合法。

请把【完整的 Python 代码】直接写在你最终回复的正文里（用 ```python 围栏）。
不要执行任何命令，不要写入任何文件，不要只描述思路，不要反问。代码之后不要再追加说明。"""

def ref_checksum(data):
    if not isinstance(data, bytes):
        raise TypeError("need bytes")
    acc = 0
    for i, b in enumerate(data):
        if i % 3 == 0:
            acc = (acc + b * 7) % 65521
        elif i % 3 == 1:
            acc = (acc ^ (b << 1)) & 0xFFFF
        else:
            acc = (acc - b) % 65521
    return (acc * 31 + len(data)) % 65521

def _checksum_cases():
    rnd = random.Random(20260708)
    # 必含判别用例：在 i%3==2 处触发 acc < b，逼出【负数取模】语义。
    # 若缺此用例，把 `% 65521` 误写成 `& 0xFFFF` 的实现会蒙混过关（自检抓到过）。
    cases = [(b"", ref_checksum(b"")), (b"\x00", ref_checksum(b"\x00")),
             (b"'\x9e\x98", ref_checksum(b"'\x9e\x98"))]
    for _ in range(8):
        d = bytes(rnd.randrange(256) for _ in range(rnd.randrange(1, 40)))
        cases.append((d, ref_checksum(d)))
    return cases

CHECKSUM_CASES = _checksum_cases()

def v_checksum(out):
    fn, err = _extract(out, "checksum")
    if fn is None:
        return (False, err)
    fails = []
    for d, expect in CHECKSUM_CASES:
        try:
            got = fn(d)
        except Exception as e:
            fails.append(f"{d!r} 抛 {type(e).__name__}"); continue
        if got != expect:
            fails.append(f"len={len(d)} → {got} 期望 {expect}")
    try:
        fn("not bytes"); fails.append("非 bytes 未抛 TypeError")
    except TypeError:
        pass
    except Exception as e:
        fails.append(f"非 bytes 抛 {type(e).__name__} 非 TypeError")
    return (not fails, "全部通过" if not fails else f"{len(fails)}项失败: {fails[:2]}")


# ══════════════════ 任务 3：精确递推算术（StepFun 弱项） ══════════════════
def _recur():
    f = [3]
    for _ in range(50):
        f.append((f[-1] * 7 + 11) % 1009)
    return f[50], sum(f) % 1009

R_F50, R_SUM = _recur()

SPEC_RECUR = f"""定义整数序列：f(0) = 3，且对 n >= 1 有 f(n) = (f(n-1) * 7 + 11) mod 1009。

请精确计算：
  A = f(50)
  B = (f(0) + f(1) + ... + f(50)) mod 1009

你可以心算、手算或写代码计算，方式不限，但必须给出【确切数值】。
不要只给通项公式，不要反问，不要提供后续选项。
你最终回复的【最后一行】必须且只能是这行 JSON（不要包在围栏里）：
{{"A": <整数>, "B": <整数>}}"""

def v_recur(out):
    m = re.search(r'"A"\s*:\s*(-?\d+)\s*,\s*"B"\s*:\s*(-?\d+)', out)
    if not m:
        return (False, f"未找到 JSON，尾部: {out.strip()[-70:]!r}")
    a, b = int(m.group(1)), int(m.group(2))
    ok = (a == R_F50 and b == R_SUM)
    return (ok, f"A={a}(期望{R_F50}) B={b}(期望{R_SUM})")


# ══════════════════ 任务 4：规格歧义（advisor 模式的靶子） ══════════════════
SPEC_AMBIG = """实现 Python 函数 pack(items, cap) -> list[list[int]]

items 是正整数重量列表，cap 是正整数容量上限。
按【原始顺序】把 items 依次装入若干段，每段元素之和不得超过 cap；
装不下就开新的一段。返回段的列表。

约束：cap <= 0 抛 ValueError；items 为空返回 []；不修改入参。

【重要】本规格存在一处真实歧义。若你发现了，必须在代码【第一行】写一条注释，
以 `# AMBIGUITY:` 开头，指出歧义是什么、以及你选择了哪种解释。然后按你选择的解释实现。

请把【完整的 Python 代码】直接写在你最终回复的正文里（用 ```python 围栏）。
不要执行任何命令，不要写入任何文件，不要只描述思路，不要反问。代码之后不要再追加说明。"""
# 歧义：某个 item 本身 > cap 时怎么办（抛错？单独成段？跳过？）规格未定义。

AMBIG_CASES_COMMON = [
    (([1, 2, 3], 3), [[1, 2], [3]]),
    (([3, 3, 3], 3), [[3], [3], [3]]),
    (([], 5), []),
    (([1, 1, 1, 1], 2), [[1, 1], [1, 1]]),
    # 判别用例：输入乱序。若实现擅自排序，结果会变成 [[1,2],[3]]（自检抓到过）
    (([3, 1, 2], 3), [[3], [1, 2]]),
]

def v_ambig(out):
    """两个维度：①是否显式标注歧义 ②实现在【无歧义输入】上是否正确、且不修改入参。"""
    flagged = bool(re.search(r'#\s*AMBIGUITY\s*:', out))
    fn, err = _extract(out, "pack")
    if fn is None:
        return (False, f"{'已标注歧义; ' if flagged else '未标注歧义; '}{err}")
    ok, note = _judge(fn, AMBIG_CASES_COMMON)
    # cap<=0
    extra = []
    try:
        fn([1], 0); extra.append("cap=0 未抛 ValueError")
    except ValueError:
        pass
    except Exception as e:
        extra.append(f"cap=0 抛 {type(e).__name__}")
    src = [2, 1, 3]      # 必须乱序，否则 items.sort() 看不出来（自检抓到过）
    try:
        fn(src, 3)
        if src != [2, 1, 3]:
            extra.append("修改了入参")
    except Exception:
        pass
    impl_ok = ok and not extra
    # 通过条件：实现正确【且】标注了歧义
    return (impl_ok and flagged,
            f"{'✔标注歧义' if flagged else '✘未标注歧义'} | 实现:{note}"
            + (f" | {extra}" if extra else ""))


TASKS_HARD = [
    dict(id="h-interval", type="implement", difficulty="hard", prompt=SPEC_INTERVAL, verifier=v_interval),
    dict(id="h-checksum", type="implement", difficulty="hard", prompt=SPEC_CHECKSUM, verifier=v_checksum),
    dict(id="h-recur",    type="analyze",   difficulty="hard", prompt=SPEC_RECUR,    verifier=v_recur),
    dict(id="h-ambig",    type="judgment",  difficulty="hard", prompt=SPEC_AMBIG,    verifier=v_ambig),
]


# ══════════════════ 自检：参考实现 + verifier 正负样本 ══════════════════
if __name__ == "__main__":
    fails = 0

    print("=== A. 参考实现自检 ===")
    ok, note = _judge(ref_parse_merge, INTERVAL_CASES)
    print(f"  {'✅' if ok else '❌'} ref_parse_merge: {note}"); fails += (not ok)
    ok2 = all(ref_checksum(d) == e for d, e in CHECKSUM_CASES)
    print(f"  {'✅' if ok2 else '❌'} ref_checksum 自洽"); fails += (not ok2)
    print(f"  ✅ 递推 ground truth: A={R_F50} B={R_SUM}")

    print("\n=== B. verifier 正/负样本自检 ===")
    import inspect, textwrap
    good_interval = "import re\n" + textwrap.dedent(inspect.getsource(ref_parse_merge)).replace(
        "ref_parse_merge", "parse_merge")
    # 负样本：不合并相邻段
    bad_interval = good_interval.replace("if a <= merged[-1][1]:", "if a < merged[-1][1]:")
    good_checksum = textwrap.dedent(inspect.getsource(ref_checksum)).replace("ref_checksum", "checksum")
    bad_checksum = good_checksum.replace("acc = (acc - b) % 65521", "acc = (acc - b) & 0xFFFF")
    good_ambig = ("# AMBIGUITY: 单个 item 重量 > cap 时规格未定义；本实现选择抛 ValueError\n"
                  "def pack(items, cap):\n"
                  "    if cap <= 0: raise ValueError('cap')\n"
                  "    out=[]; cur=[]; s=0\n"
                  "    for x in items:\n"
                  "        if x > cap: raise ValueError('item > cap')\n"
                  "        if s + x > cap: out.append(cur); cur=[]; s=0\n"
                  "        cur.append(x); s+=x\n"
                  "    if cur: out.append(cur)\n"
                  "    return out\n")
    noflag_ambig = good_ambig.split("\n", 1)[1]           # 去掉 AMBIGUITY 注释
    mutate_ambig = good_ambig.replace("for x in items:", "items.sort()\n    for x in items:")

    # 真实踩过的假阴性场景，一律固化为正样本：
    CN_PROSE = ("\n\n这个实现的要点是：\n1. 先用正则严格校验格式，避免 “09:00 - 10:00” 这类输入混入。\n"
                "2. 跨午夜时拆成两段，再统一合并。\n如果你需要，我可以补充单元测试。\n")
    PROSE_BEFORE = "好的，我来实现这个函数。思路是先校验、再拆段、最后合并。\n\n"

    checks = [
        ("interval 正样本(带CLI横幅)", v_interval(good_interval + "\nOpenAI Codex v0.1\nworkdir: x"), True),
        ("interval 正样本(代码后跟中文解释)", v_interval(good_interval + CN_PROSE), True),
        ("interval 正样本(前后都有中文散文+围栏)",
         v_interval(PROSE_BEFORE + "```python\n" + good_interval + "\n```" + CN_PROSE), True),
        ("interval 负样本(纯散文无代码)", v_interval("我建议你先校验格式，再合并区间。"), False),
        ("interval 负样本(不合并相邻)", v_interval(bad_interval), False),
        ("checksum 正样本(带围栏)",     v_checksum("```python\n" + good_checksum + "\n```"), True),
        ("checksum 正样本(围栏+尾部解释)",
         v_checksum("```python\n" + good_checksum + "\n```" + CN_PROSE), True),
        ("checksum 负样本(负数取模错)", v_checksum(bad_checksum), False),
        ("recur 正样本",                v_recur(f'{{"A": {R_F50}, "B": {R_SUM}}}'), True),
        ("recur 负样本",                v_recur(f'{{"A": {R_F50}, "B": {(R_SUM+1)%1009}}}'), False),
        ("ambig 正样本(标注+正确)",     v_ambig(good_ambig), True),
        ("ambig 负样本(未标注歧义)",    v_ambig(noflag_ambig), False),
        ("ambig 负样本(修改入参)",      v_ambig(mutate_ambig), False),
    ]
    for name, (got, note), expect in checks:
        good = (got == expect); fails += (not good)
        print(f"  {'✅' if good else '❌ VERIFIER BUG'} {name:28} 判定={str(got):5} 期望={expect} | {note[:52]}")

    print("\n" + ("✅ 全部自检通过，尺子可信" if not fails else f"❌ {fails} 项有问题，禁止用于基准"))
