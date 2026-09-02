#!/usr/bin/env python3
"""
ai-cross 模型真身校验器。

第三方 Anthropic 兼容端点（GLM/Kimi 等）对「格式合法但它不提供」的模型名
可能【不报错、静默用默认模型应答】。CLI 的 modelUsage 记的是请求值、不可信。
本脚本绕开 CLI，直接 POST {base}/v1/messages，读【响应体服务端自报的 model】，
与请求比对：不一致即静默降级。冒烟判据从「有没有回答」升级到「回答的是不是它」。

用法：
  python verify_model.py --provider "Zhipu GLM"
        不带 --models 时，校验 cc-switch 里该 provider 的 haiku/sonnet/opus 三档 ID。
  python verify_model.py --provider "Zhipu GLM" --models "glm-4.7,glm-5.2,glm-5.2[1m],glm-5.1"
        校验指定 ID 列表（逗号分隔）。

退出码：0=全部一致；8=检测到静默降级或 HTTP 错误；2/4=找不到 provider/缺凭据。
token 只在本进程读取并注入请求头，绝不打印、绝不落盘。
"""
import sqlite3, os, json, sys, argparse, urllib.request, urllib.error

DB = os.path.expanduser("~/.cc-switch/cc-switch.db")


def _provider_env(name):
    if not os.path.exists(DB):
        print(json.dumps({"error": "未找到 cc-switch 数据库", "path": DB,
                          "hint": "没装 cc-switch 就直接用 --provider 对应端点手测，或走 setup.md。"},
                         ensure_ascii=False))
        sys.exit(2)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    row = None
    for r in con.execute("SELECT settings_config FROM providers WHERE name=?", (name,)):
        row = r
        break
    con.close()
    if not row:
        print(f"未找到 provider: {name}（名字需与 cc-switch 里完全一致）", file=sys.stderr)
        sys.exit(2)
    env = json.loads(row["settings_config"]).get("env", {}) or {}
    return env


def _norm(s):
    return (s or "").strip().lower()


def probe(base, token, req_model):
    """打端点，返回 (served_model, text, http_err)。token 不出现在返回里。"""
    body = json.dumps({
        "model": req_model, "max_tokens": 16,
        "messages": [{"role": "user", "content": "Reply with just: OK"}],
    }).encode()
    req = urllib.request.Request(f"{base}/v1/messages", data=body, method="POST", headers={
        "content-type": "application/json", "anthropic-version": "2023-06-01",
        "x-api-key": token, "authorization": f"Bearer {token}",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        text = "".join(b.get("text", "") for b in d.get("content", []) if isinstance(b, dict))
        return d.get("model"), text.strip()[:20], None
    except urllib.error.HTTPError as e:
        return None, None, f"HTTP {e.code}: {e.read()[:120].decode('utf-8', 'replace')}"
    except Exception as e:
        return None, None, f"{type(e).__name__}: {str(e)[:120]}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--provider", required=True)
    p.add_argument("--models", help="逗号分隔的模型 ID 列表；不给则校验 cc-switch 里的三档")
    a = p.parse_args()

    env = _provider_env(a.provider)
    base = (env.get("ANTHROPIC_BASE_URL") or "").rstrip("/")
    token = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")
    if not (base and token):
        print(f"provider「{a.provider}」缺 endpoint 或 token（很可能建了条目没填 key）。", file=sys.stderr)
        sys.exit(4)

    if a.models:
        req_models = [m.strip() for m in a.models.split(",") if m.strip()]
        source = "指定列表"
    else:
        tiers = [("haiku", env.get("ANTHROPIC_DEFAULT_HAIKU_MODEL")),
                 ("sonnet", env.get("ANTHROPIC_DEFAULT_SONNET_MODEL")),
                 ("opus", env.get("ANTHROPIC_DEFAULT_OPUS_MODEL"))]
        req_models = [(t, m) for t, m in tiers if m]
        source = "cc-switch 三档映射"

    print(f"校验 provider「{a.provider}」 端点 {base}\n来源：{source}\n")
    print(f"{'档位/请求':<22} {'→ 服务端 model':<26} 判定")
    print("-" * 70)

    downgraded = errored = 0
    for item in req_models:
        tier, req_model = item if isinstance(item, tuple) else ("", item)
        served, text, err = probe(base, token, req_model)
        label = f"{tier + '=' if tier else ''}{req_model}"
        if err:
            print(f"{label:<22} {'—':<26} ❌ {err}")
            errored += 1
        elif _norm(served) == _norm(req_model):
            print(f"{label:<22} {served!s:<26} ✅ 一致")
        else:
            print(f"{label:<22} {served!s:<26} ⚠️ 静默降级（服务端≠请求）")
            downgraded += 1

    print("-" * 70)
    if downgraded or errored:
        print(f"结论：{downgraded} 个静默降级、{errored} 个错误。请纠正对应档位的模型 ID，"
              f"并把可用 ID 记入 manifest.md。")
        sys.exit(8)
    print("结论：全部一致，无静默降级。可放心把这些 ID 记入 manifest.md。")
    sys.exit(0)


if __name__ == "__main__":
    main()
