#!/usr/bin/env python3
"""usage_probe.py — 只读扫描本机各 agent CLI 的用量日志，输出聚合元数据。

用途（通用方案，不依赖任何私有工具）：
  1. 新鲜度：某 (通道, 模型) 最近还在日志里出现 = "在用"证据，可为 manifest 官方 CLI
     条目续期；第三方 Anthropic 兼容端点仍必须过 verify_model.py（日志多记请求值非真身）。
  2. 发现：已知 CLI 的数据目录存在 + 近期活动 = 用户实际在用的提示，供申报确认（不自动纳入）。

隐私铁律：只输出 模型ID/别名/次数/时间戳/目录存在性；对话内容、prompt、title 一律不读不输出。

用法：python usage_probe.py [--days 30]
输出：JSON 到 stdout。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()


def iso(ts_epoch):
    return datetime.fromtimestamp(ts_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_ts(v):
    """把各家时间字段统一成 ISO 字符串；认不出就返回 None。"""
    if isinstance(v, (int, float)):
        if v > 1e12:  # 毫秒
            v /= 1000
        try:
            return iso(v)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(v, str) and len(v) >= 10:
        return v
    return None


def bump(agg, source, model, alias, ts):
    if not model or model.startswith("<"):  # 过滤 <synthetic> 类占位
        return
    key = (source, model, alias or "")
    e = agg.setdefault(key, {"count": 0, "first_seen": ts, "last_seen": ts})
    e["count"] += 1
    if ts:
        if not e["first_seen"] or ts < e["first_seen"]:
            e["first_seen"] = ts
        if not e["last_seen"] or ts > e["last_seen"]:
            e["last_seen"] = ts


def scan_jsonl_files(files, prefilter, extract, agg, stats):
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if prefilter not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    extract(rec, agg)
            stats["files_scanned"] += 1
        except OSError:
            stats["files_skipped"] += 1


def recent_files(root, pattern, cutoff_epoch):
    if not root.exists():
        return []
    out = []
    for p in root.rglob(pattern):
        try:
            if p.stat().st_mtime >= cutoff_epoch:
                out.append(p)
        except OSError:
            continue
    return out


def main():
    ap = argparse.ArgumentParser(description="聚合各 agent CLI 用量日志（只读，仅元数据）")
    ap.add_argument("--days", type=int, default=30, help="回看窗口天数（按文件 mtime 过滤）")
    args = ap.parse_args()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=args.days)).timestamp()

    agg = {}
    stats = {"files_scanned": 0, "files_skipped": 0}

    # Claude Code：assistant 记录的 message.model 是 API 响应侧的值
    scan_jsonl_files(
        recent_files(HOME / ".claude" / "projects", "*.jsonl", cutoff),
        '"type":"assistant"',
        lambda r, a: bump(a, "claude", (r.get("message") or {}).get("model"), None,
                          norm_ts(r.get("timestamp"))),
        agg, stats)

    # Codex：turn_context 记录的 payload.model（请求侧）
    scan_jsonl_files(
        recent_files(HOME / ".codex" / "sessions", "*.jsonl", cutoff),
        '"type":"turn_context"',
        lambda r, a: bump(a, "codex", (r.get("payload") or {}).get("model"), None,
                          norm_ts(r.get("timestamp"))),
        agg, stats)

    # Kimi Code：wire.jsonl 的 llm.request 记录（请求侧，含别名与 effort）
    def kimi_extract(r, a):
        if r.get("type") == "llm.request":
            bump(a, "kimi", r.get("model"), r.get("modelAlias"), norm_ts(r.get("time")))
    scan_jsonl_files(
        recent_files(HOME / ".kimi-code" / "sessions", "wire.jsonl", cutoff),
        '"llm.request"', kimi_extract, agg, stats)

    # 已知 CLI 数据目录的存在性与最近活动（浅层，只看顶层 mtime，不解析）
    roster = {
        "claude": HOME / ".claude",
        "codex": HOME / ".codex",
        "kimi": HOME / ".kimi-code",
        "gemini": HOME / ".gemini",
        "qoder": HOME / ".qoder",
        "cc-switch": HOME / ".cc-switch",
        "aichat": Path(os.environ.get("APPDATA", HOME / ".config")) / "aichat",
    }
    installs = []
    for name, path in roster.items():
        entry = {"name": name, "path": str(path), "exists": path.exists()}
        if entry["exists"]:
            try:
                newest = max((c.stat().st_mtime for c in path.iterdir()), default=None)
                entry["last_activity"] = iso(newest) if newest else None
            except OSError:
                entry["last_activity"] = None
        installs.append(entry)

    usage = [
        {"source": s, "model": m, **({"alias": al} if al else {}), **e}
        for (s, m, al), e in sorted(agg.items(),
                                    key=lambda kv: kv[1]["last_seen"] or "", reverse=True)
    ]
    json.dump({
        "generated_at": iso(datetime.now(tz=timezone.utc).timestamp()),
        "window_days": args.days,
        "note": "模型字段多为请求值，不代表服务端真身；真身核对用 verify_model.py",
        "usage": usage,
        "installs": installs,
        **stats,
    }, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
