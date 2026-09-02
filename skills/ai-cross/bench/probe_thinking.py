"""探针：确认硅基流动上哪些模型能真正关掉思考，以及用什么参数关。

判据不是"接口没报错"，而是**响应体自证**：
  - reasoning_content 为空 且 completion token 显著下降 → 思考真的关了
  - 接口 200 但 reasoning_content 仍有内容 → 参数被静默忽略（等同 GLM 模型 ID 静默降级那个坑）

不通过的模型一律不进基准。
"""
import json, urllib.request, urllib.error, pathlib, time

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"

MODELS = [
    ("Qwen3.6-35B",    "Qwen/Qwen3.6-35B-A3B"),
    ("GLM-5.2",        "zai-org/GLM-5.2"),
    ("DeepSeek-V4-Pro","deepseek-ai/DeepSeek-V4-Pro"),
    ("Kimi-K2.6",      "Pro/moonshotai/Kimi-K2.6"),
    ("LongCat-2.0",    "meituan-longcat/LongCat-2.0"),
]

# 候选关闭方式（不同厂商约定不同）
VARIANTS = [
    ("baseline",          {}),
    ("enable_thinking=F", {"enable_thinking": False}),
    ("thinking=disabled", {"thinking": {"type": "disabled"}}),
]

PROMPT = ("把下面的日期改写成 YYYY-MM-DD 格式，只输出改写后的日期一行，不要其他文字。\n"
          "日期：2026年3月7日")


def call(model_id, extra, max_tokens=512):
    body = {"model": model_id, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": PROMPT}]}
    body.update(extra)
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", "Bearer " + KEY)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        d = json.loads(resp.read())
    wall = time.time() - t0
    ch = (d.get("choices") or [{}])[0].get("message", {})
    u = d.get("usage", {})
    return dict(
        model_echo=d.get("model"),
        content=(ch.get("content") or "").strip(),
        reasoning=(ch.get("reasoning_content") or "").strip(),
        completion=u.get("completion_tokens"),
        wall=round(wall, 1),
    )


def main():
    print(f"{'模型':16}{'变体':20}{'HTTP':>6}{'reasoning字数':>13}{'completion':>11}{'秒':>6}  回显model")
    print("-" * 100)
    table = {}
    for name, mid in MODELS:
        table[name] = {}
        for vname, extra in VARIANTS:
            try:
                r = call(mid, extra)
                table[name][vname] = r
                print(f"{name:16}{vname:20}{'200':>6}{len(r['reasoning']):>13}"
                      f"{str(r['completion']):>11}{r['wall']:>6}  {r['model_echo']}")
            except urllib.error.HTTPError as e:
                detail = e.read()[:100].decode(errors="replace")
                table[name][vname] = None
                print(f"{name:16}{vname:20}{e.code:>6}{'-':>13}{'-':>11}{'-':>6}  {detail}")
            except Exception as e:
                table[name][vname] = None
                print(f"{name:16}{vname:20}{'ERR':>6}  {type(e).__name__}: {str(e)[:60]}")
            time.sleep(0.5)

    print("\n" + "=" * 100)
    print("判定（进基准的条件：某变体下 reasoning 为空，且 baseline 的 reasoning 非空 → 开关真实可控）")
    print("-" * 100)
    usable = []
    for name, _ in MODELS:
        base = table[name].get("baseline")
        if not base:
            print(f"{name:16} ❌ baseline 调用失败，排除")
            continue
        if not base["reasoning"]:
            print(f"{name:16} ⚠️  baseline 就没有 reasoning_content —— 非推理模型或不回传，无法测开关，排除")
            continue
        for vname, _ in VARIANTS[1:]:
            r = table[name].get(vname)
            if r and not r["reasoning"]:
                drop = (base["completion"] or 0) - (r["completion"] or 0)
                print(f"{name:16} ✅ 用 {vname:20} 关闭成功 "
                      f"(reasoning {len(base['reasoning'])}→0 字, completion {base['completion']}→{r['completion']}, 降 {drop})")
                usable.append((name, vname))
                break
            elif r:
                print(f"{name:16} ✗  {vname:20} 接口 200 但 reasoning 仍有 {len(r['reasoning'])} 字 → 参数被静默忽略")
        else:
            print(f"{name:16} ❌ 无可用关闭方式，排除")

    print("\n可进基准的臂：")
    for n, v in usable:
        print(f"  - {n}  (off 用 {v})")
    if not usable:
        print("  （无）—— 基准无法开展")


if __name__ == "__main__":
    main()
