"""基准任务集：每个任务必须有【程序可判定】的 ground truth，不靠模型自述。

任务分类维度：
  type       : recon(侦察) / implement(实现) / analyze(分析)
  difficulty : low / mid
"""
import re, json, importlib.util, sys, io, contextlib, pathlib

TARGET = pathlib.Path(__file__).parent.parent / "test-run2" / "merge_intervals.py"


# CLI 会在正文后追加横幅/诊断行；混进 exec() 会造成 verifier 假阴性（踩过）。
NOISE = re.compile(r'^(Reading additional input|OpenAI Codex|workdir:|model:|provider:|'
                   r'approval:|sandbox:|reasoning |session id:|-{4,}|user$|codex$|warning:|tokens used)')

def _cut_trailing_noise(lines):
    out = []
    for l in lines:
        if NOISE.match(l.strip()):
            break
        out.append(l)
    return "\n".join(out)


# ---------- verifiers：输入模型原始输出，返回 (是否正确, 说明) ----------

def v_null(out):
    return (len(out.strip()) > 0, "任何非空回复即可（用于测固定开销）")


def v_count_asserts(out):
    m = re.search(r'\{[^}]*"asserts"\s*:\s*(\d+)[^}]*"raises"\s*:\s*(\d+)', out)
    if not m:
        return (False, f"未找到 JSON，原始输出前80字: {out.strip()[:80]!r}")
    a, r = int(m.group(1)), int(m.group(2))
    ok = (a == 16 and r == 4)
    return (ok, f"asserts={a}(期望16) raises={r}(期望4)")


def v_find_line(out):
    m = re.search(r'\b(\d+)\b', out)
    if not m:
        return (False, "未找到数字")
    n = int(m.group(1))
    return (n == 1, f"回答行号={n}(期望1)")


def _run_code(out, func_name, checks):
    """把模型输出里的代码抽出来跑，用【我们自己的】用例独立核验。"""
    code = re.sub(r'\x1b\[[0-9;]*m', '', out)
    code = re.sub(r'^```(?:python)?\s*$', '', code, flags=re.M)
    lines = code.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if re.match(r'^\s*(from |import |[A-Z_]+\s*=|def )', l)), None)
    if start is None:
        return (False, "未找到代码起点")
    src = _cut_trailing_noise(lines[start:])
    # 掐掉模型自带的自测块，只留实现——我们用自己的用例判定
    src = re.split(r'^if __name__', src, flags=re.M)[0]

    ns = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(src, "<model>", "exec"), ns)
    except Exception as e:
        return (False, f"代码无法执行: {type(e).__name__}: {e}")
    fn = ns.get(func_name)
    if not callable(fn):
        return (False, f"未定义 {func_name}")

    fails = []
    for arg, expect in checks:
        try:
            got = fn(arg)
            if expect is ValueError:
                fails.append(f"{arg!r} 未抛 ValueError")
            elif got != expect:
                fails.append(f"{arg!r}→{got!r} 期望{expect!r}")
        except ValueError:
            if expect is not ValueError:
                fails.append(f"{arg!r} 误抛 ValueError")
        except Exception as e:
            fails.append(f"{arg!r} 抛 {type(e).__name__}")
    return (not fails, "全部通过" if not fails else f"{len(fails)}项失败: {fails[:3]}")


ROMAN_CHECKS = [("I", 1), ("III", 3), ("IV", 4), ("IX", 9), ("XL", 40), ("LVIII", 58),
                ("XC", 90), ("CD", 400), ("CM", 900), ("MCMXCIV", 1994), ("MMMCMXCIX", 3999),
                ("", ValueError), ("ABC", ValueError), ("iv", ValueError), (123, ValueError)]

def v_roman(out):
    return _run_code(out, "roman_to_int", ROMAN_CHECKS)


CHUNK_CHECKS = [(([1,2,3,4,5], 2), [[1,2],[3,4],[5]]),
                (([], 3), []),
                (([1], 5), [[1]]),
                (([1,2,3,4], 2), [[1,2],[3,4]])]

def v_chunk(out):
    code = re.sub(r'^```(?:python)?\s*$', '', out, flags=re.M)
    lines = code.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r'^\s*(from |import |def )', l)), None)
    if start is None:
        return (False, "未找到代码起点")
    src = re.split(r'^if __name__', _cut_trailing_noise(lines[start:]), flags=re.M)[0]
    ns = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(src, "<model>", "exec"), ns)
    except Exception as e:
        return (False, f"代码无法执行: {type(e).__name__}: {e}")
    fn = ns.get("chunk")
    if not callable(fn):
        return (False, "未定义 chunk")
    fails = []
    for (lst, n), expect in CHUNK_CHECKS:
        try:
            got = fn(list(lst), n)
            if got != expect:
                fails.append(f"chunk({lst},{n})→{got} 期望{expect}")
        except Exception as e:
            fails.append(f"chunk({lst},{n}) 抛 {type(e).__name__}")
    # n=0 必须显式校验：仅靠 range(step=0) 的副作用会“蒙对”，而 n=-1 时会静默返回 [] —— 故两者都测
    for bad_n in (0, -1):
        try:
            got = fn([1, 2], bad_n)
            fails.append(f"n={bad_n} 未抛 ValueError(返回{got!r})")
        except ValueError:
            pass
        except Exception as e:
            fails.append(f"n={bad_n} 抛 {type(e).__name__} 非 ValueError")
    # 不修改入参
    src = [1, 2, 3]
    try:
        fn(src, 2)
        if src != [1, 2, 3]:
            fails.append("修改了入参")
    except Exception:
        pass
    return (not fails, "全部通过" if not fails else f"{len(fails)}项失败: {fails[:3]}")


def v_median(out):
    m = re.search(r'"median"\s*:\s*([\d.]+)', out)
    if not m:
        return (False, "未找到 median")
    val = float(m.group(1))
    return (abs(val - 9.5) < 1e-9, f"median={val}(期望9.5)")


# ---------- 任务定义 ----------

TASKS = [
    dict(id="null", type="null", difficulty="low",
         prompt="只回复两个字：收到",
         verifier=v_null, needs_fs=False),

    dict(id="recon-count", type="recon", difficulty="low",
         prompt=f"读取 {TARGET.as_posix()}，统计其中 assert 语句的数量、以及 raise ValueError 的数量。"
                '只回复一行 JSON，不要其他内容: {"asserts":N,"raises":M}',
         verifier=v_count_asserts, needs_fs=True),

    dict(id="recon-locate", type="recon", difficulty="low",
         prompt=f"读取 {TARGET.as_posix()}，回答 def merge_intervals 定义在第几行。只回复一个数字。",
         verifier=v_find_line, needs_fs=True),

    dict(id="impl-roman", type="implement", difficulty="mid",
         prompt="写一个 Python 函数 roman_to_int(s)，把罗马数字字符串转为整数。要求：支持 "
                "IV/IX/XL/XC/CD/CM 六种减法规则；输入非字符串、空字符串、或含非法字符（含小写）"
                "时抛 ValueError。只输出完整 Python 代码，不要 markdown 围栏，不要解释。",
         verifier=v_roman, needs_fs=False),

    dict(id="impl-chunk", type="implement", difficulty="mid",
         prompt="写一个 Python 函数 chunk(lst, n)，把列表切成每段最多 n 个元素的子列表，"
                "返回子列表组成的列表。要求：空列表返回 []；n<=0 抛 ValueError；不修改入参。"
                "只输出完整 Python 代码，不要 markdown 围栏，不要解释。",
         verifier=v_chunk, needs_fs=False),

    dict(id="analyze-stats", type="analyze", difficulty="mid",
         prompt="数据集 [12, 7, 3, 45, 9, 11, 8, 300, 10, 6]。计算中位数。"
                '最后一行只输出 JSON: {"median": ...}',
         verifier=v_median, needs_fs=False),
]
