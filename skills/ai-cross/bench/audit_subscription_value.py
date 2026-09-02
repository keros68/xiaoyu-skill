# 订阅回本审计：聚合本机三家 CLI 的 token 用量日志，按官方 API 牌价折算
# 只输出聚合数字，绝不输出对话内容。
# 数据源（均为客户端记录的 API 返回值）：
#   kimi   ~/.kimi-code/sessions/**/wire.jsonl   usage.record 事件（含 model）
#   codex  ~/.codex/sessions/**/*.jsonl          token_count.last_token_usage 增量，模型取最近 turn_context
#   claude ~/.claude/projects/**/*.jsonl         assistant 记录 message.usage，按 message.id 去重取最大
# 牌价与汇率见 PRICES / FX，抓取日期与出处见文章正文；改价后重跑即可。
import json, glob, os, collections
from datetime import datetime, timezone

FX = 6.777  # USD/CNY, 2026-07-17, exchangerates.org.uk

# 每百万 token 价格。cache_write 为 None 表示日志无该字段或官方未单列（不计入）。
PRICES = {
    # Kimi K3（人民币，platform.kimi.com 官方页 2026-07-19 抓取）
    "kimi/k3": dict(cur="CNY", inp=20.0, cache_read=2.0, cache_write=None, out=100.0),
    # GPT-5.6 Sol（美元，developers.openai.com/api/docs/pricing 官方页 2026-07-19 抓取）
    "codex/gpt-5.6-sol": dict(cur="USD", inp=5.0, cache_read=0.5, cache_write=None, out=30.0),
    # Anthropic（美元；缓存读=0.1x 输入价，缓存写(5m)=1.25x 输入价）
    "claude/claude-opus-4-8": dict(cur="USD", inp=5.0, cache_read=0.5, cache_write=6.25, out=25.0),
    "claude/claude-fable-5": dict(cur="USD", inp=10.0, cache_read=1.0, cache_write=12.5, out=50.0),
    "claude/claude-sonnet-5": dict(cur="USD", inp=3.0, cache_read=0.3, cache_write=3.75, out=15.0),
    "claude/claude-haiku-4-5-20251001": dict(cur="USD", inp=1.0, cache_read=0.1, cache_write=1.25, out=5.0),
}

# 月费（用户实际订阅档位）
FEES = {
    "kimi": ("CNY", 199.0, "Kimi Allegretto ¥199/月"),
    "codex": ("USD", 100.0, "ChatGPT Pro $100/月 (5x)"),
    "claude": ("USD", 100.0, "Claude Max 5x $100/月"),
}

HOME = os.path.expanduser("~")
Usage = lambda: dict(inp=0, cache_read=0, cache_write=0, out=0, calls=0, t0=None, t1=None)


def seen(u, ts):
    if ts is None:
        return
    u["t0"] = ts if u["t0"] is None else min(u["t0"], ts)
    u["t1"] = ts if u["t1"] is None else max(u["t1"], ts)


def scan_kimi(agg):
    for f in glob.glob(os.path.join(HOME, ".kimi-code", "sessions", "**", "wire.jsonl"), recursive=True):
        try:
            fh = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"usage.record"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") != "usage.record":
                    continue
                usage, model = rec.get("usage") or {}, rec.get("model")
                if not usage or model != "kimi-code/k3":
                    continue
                u = agg["kimi/k3"]
                u["inp"] += usage.get("inputOther", 0)
                u["cache_read"] += usage.get("inputCacheRead", 0)
                u["cache_write"] += usage.get("inputCacheCreation", 0)
                u["out"] += usage.get("output", 0)
                u["calls"] += 1
                ts = rec.get("time")
                if isinstance(ts, (int, float)):
                    seen(u, datetime.fromtimestamp(ts / 1000, tz=timezone.utc))


def parse_iso(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def scan_codex(agg):
    for f in glob.glob(os.path.join(HOME, ".codex", "sessions", "**", "*.jsonl"), recursive=True):
        model = None
        try:
            fh = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                payload = rec.get("payload") or {}
                rtype = rec.get("type")
                if rtype == "turn_context":
                    model = payload.get("model") or model
                elif rtype == "event_msg" and payload.get("type") == "token_count":
                    if model != "gpt-5.6-sol":
                        continue
                    last = (payload.get("info") or {}).get("last_token_usage") or {}
                    if not last:
                        continue
                    u = agg["codex/gpt-5.6-sol"]
                    cached = last.get("cached_input_tokens", 0)
                    u["inp"] += last.get("input_tokens", 0) - cached  # input 含 cached，扣除
                    u["cache_read"] += cached
                    u["out"] += last.get("output_tokens", 0)
                    u["calls"] += 1
                    seen(u, parse_iso(rec.get("timestamp") or ""))


def scan_claude(agg):
    KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    best = {}
    ts_by_key = {}
    for f in glob.glob(os.path.join(HOME, ".claude", "projects", "**", "*.jsonl"), recursive=True):
        try:
            fh = open(f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"assistant"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message") or {}
                usage, mid = msg.get("usage") or {}, msg.get("id")
                model = msg.get("model")
                key = f"claude/{model}"
                if not usage or mid is None or key not in PRICES:
                    continue
                cur = best.setdefault((key, mid), dict.fromkeys(KEYS, 0))
                for k in KEYS:
                    v = usage.get(k)
                    if isinstance(v, (int, float)):
                        cur[k] = max(cur[k], v)
                ts = parse_iso(rec.get("timestamp") or "")
                if ts:
                    ts_by_key.setdefault((key, mid), ts)
    for (key, mid), c in best.items():
        u = agg[key]
        u["inp"] += c["input_tokens"]
        u["cache_write"] += c["cache_creation_input_tokens"]
        u["cache_read"] += c["cache_read_input_tokens"]
        u["out"] += c["output_tokens"]
        u["calls"] += 1
        seen(u, ts_by_key.get((key, mid)))


def fold(key, u):
    p = PRICES[key]
    cost = (u["inp"] * p["inp"] + u["cache_read"] * p["cache_read"] + u["out"] * p["out"]) / 1e6
    if p["cache_write"] is not None:
        cost += u["cache_write"] * p["cache_write"] / 1e6
    nocache = (u["inp"] * p["inp"] + u["out"] * p["out"]) / 1e6
    return cost, nocache, p["cur"]


def main():
    agg = collections.defaultdict(Usage)
    scan_kimi(agg)
    scan_codex(agg)
    scan_claude(agg)

    vendor = collections.defaultdict(lambda: dict(cost_cny=0.0, nocache_cny=0.0, t0=None, t1=None, calls=0))
    print("=== 按模型折算（官方牌价）===")
    for key in sorted(agg):
        u = agg[key]
        if u["calls"] == 0:
            continue
        cost, nocache, cur = fold(key, u)
        cny = cost * (FX if cur == "USD" else 1)
        days = max((u["t1"] - u["t0"]).total_seconds() / 86400, 1e-9)
        print(f"\n{key}  calls={u['calls']}  span={u['t0']:%m-%d %H:%M}..{u['t1']:%m-%d %H:%M}UTC ({days:.2f}天)")
        print(f"  非缓存输入 {u['inp']:,} | 缓存读 {u['cache_read']:,} | 缓存写 {u['cache_write']:,} | 输出 {u['out']:,}")
        print(f"  折算 {cur} {cost:,.2f}（≈¥{cny:,.2f}）  其中去缓存口径 {cur} {nocache:,.2f}")
        v = vendor[key.split("/")[0]]
        v["cost_cny"] += cny
        v["nocache_cny"] += nocache * (FX if cur == "USD" else 1)
        v["calls"] += u["calls"]
        v["t0"] = u["t0"] if v["t0"] is None else min(v["t0"], u["t0"])
        v["t1"] = u["t1"] if v["t1"] is None else max(v["t1"], u["t1"])

    print("\n=== 按订阅汇总（月费回本倍数）===")
    for name, v in sorted(vendor.items()):
        cur, fee, label = FEES[name]
        fee_cny = fee * (FX if cur == "USD" else 1)
        days = max((v["t1"] - v["t0"]).total_seconds() / 86400, 1e-9)
        daily = v["cost_cny"] / days
        daily_fee = fee_cny / 30
        print(f"\n[{name}] {label}（≈¥{fee_cny:,.0f}/月，日摊 ¥{daily_fee:.2f}）")
        print(f"  观测窗口 {days:.2f} 天，{v['calls']} 次调用")
        print(f"  折算消耗 ¥{v['cost_cny']:,.2f}（日均 ¥{daily:,.2f}）  去缓存口径 ¥{v['nocache_cny']:,.2f}")
        print(f"  回本倍数（日均消耗/日摊月费）：{daily / daily_fee:,.1f}x")
        print(f"  窗口内消耗 = 月费的 {v['cost_cny'] / fee_cny:,.2f} 倍")


if __name__ == "__main__":
    main()
