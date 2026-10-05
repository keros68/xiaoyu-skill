#!/usr/bin/env python3
"""
ai-cross 的盘点脚本：探测本机模型入口，把用户确认过的清单存成 manifest，派发时按它选人。

  detect [--human]        只读探测：各 CLI 的版本与路径、各自的模型清单事实源、cc-switch 供应商。
                          不登录、不发模型请求、不读密钥字段、不写任何文件。
  save --plan FILE        把用户确认过的方案写进 manifest（同名条目覆盖，其余保留）。
       [--replace]        模型 ID 逐个对照探测结果，不在清单里的拒收。--replace 先清空旧条目。
  show [--human]          输出 manifest，标出超过 30 天未冒烟的条目。
  pick --role reviewer|executor --host NAME
       [--author VENDOR|none] [--n N] [--tier low|mid|high]
                          选默认人选。reviewer 排除被审产出的厂商（默认是宿主厂商），
                          多选时各选不同厂商。
  set  [--smoke ENTRY=ok|fail[:原因]] [--billing ENTRY=subscription|per-call]
       [--reviewers A,B,...] [--executor ENTRY[:tier]] [--note 文本] [--remove ENTRY]
                          改 manifest 里的单项。

manifest 位置：$AICROSS_HOME/skill/manifest.json，未设 AICROSS_HOME 时是 ~/.aicross/skill/manifest.json。
它在用户主目录下，各宿主共用一份，skill 更新不影响它。

退出码：0 成功；1 没有可选的人选；2 参数或方案有误；3 还没有 manifest。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import cc_switch  # noqa: E402  同目录的只读桥，复用它的 provider 读取

HOME = Path.home()
SCHEMA = "ai-cross-manifest/1"
STALE_DAYS = 30
TIERS = ("low", "mid", "high")
BILLING = ("subscription", "unknown", "per-call")  # 也是选人时的先后顺序

# 模型 ID → 权重厂商。只收有把握的前缀；认不出的留空，由方案里的 vendor 字段申报。
VENDOR_RULES = (
    (r"^(claude|haiku|sonnet|opus|fable)", "Anthropic"),
    (r"^(gpt|o\d|codex|chatgpt)", "OpenAI"),
    (r"^gemini", "Google"),
    (r"^(glm|zai)", "Zhipu"),
    (r"^(kimi|k\d|moonshot)", "Moonshot"),
    (r"^deepseek", "DeepSeek"),
    (r"^(qwen|qwq)", "Alibaba"),
    (r"^minimax", "MiniMax"),
    (r"^grok", "xAI"),
    (r"^doubao", "ByteDance"),
    (r"^(step-|stepfun)", "StepFun"),
    (r"^ernie", "Baidu"),
    (r"^(mistral|codestral)", "Mistral"),
)

# 宿主 → 它自己的厂商。聚合型或底层不透明的宿主留空：不把宿主算作交叉验证的一方。
HOST_VENDOR = {
    "claude-code": "Anthropic",
    "codex": "OpenAI",
    "kimi": "Moonshot",
    "antigravity": "Google",
}

# 各通道做盲审时的隔离程度（依据见 channels.md 开头）：
# full = 空目录之外，用户级指令也已实测可隔离；partial = 只做到空目录。
ISOLATION = {"claude": "full", "pi": "full"}

# 只做存在检测的 CLI：独立 CLI 已下线或没有可读的模型清单
EXTRA_CLIS = ("aichat", "qoder", "codebuddy", "hermes")


# 厂商的常见别称 → 规范名。方案和 --author 里手写的厂商名先过这张表，同一家才比得出来。
VENDOR_ALIASES = {
    "claude": "Anthropic", "智谱": "Zhipu", "z.ai": "Zhipu", "glm": "Zhipu",
    "kimi": "Moonshot", "月之暗面": "Moonshot", "gpt": "OpenAI", "chatgpt": "OpenAI",
    "gemini": "Google", "谷歌": "Google", "qwen": "Alibaba", "通义": "Alibaba",
    "阿里": "Alibaba", "百炼": "Alibaba", "grok": "xAI", "豆包": "ByteDance", "字节": "ByteDance",
    "阶跃": "StepFun", "百度": "Baidu", "文心": "Baidu",
}


def vendor_of(model_id):
    name = (model_id or "").strip().lower().rsplit("/", 1)[-1]
    for pattern, vendor in VENDOR_RULES:
        if re.search(pattern, name):
            return vendor
    return None


def canon_vendor(name):
    text = (name or "").strip()
    if not text:
        return None
    low = text.lower()
    for _, vendor in VENDOR_RULES:
        if vendor.lower() == low:
            return vendor
    return VENDOR_ALIASES.get(low, text)


def data_root():
    env = os.environ.get("AICROSS_HOME", "").strip()
    return Path(env) if env else HOME / ".aicross"


def manifest_path():
    return data_root() / "skill" / "manifest.json"


def today():
    return date.today().isoformat()


def fail(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


# ---------- 探测 ----------

def find_cli(name):
    """PATH 里找不到时补试已知的安装位置（kimi、agy 在 Windows 上装完不进 PATH）。"""
    found = shutil.which(name)
    if found:
        return found
    fallbacks = {
        "kimi": [HOME / ".kimi-code" / "bin" / "kimi.exe", HOME / ".kimi-code" / "bin" / "kimi"],
        "agy": [Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"],
    }
    for cand in fallbacks.get(name, []):
        if str(cand) not in ("", ".") and cand.is_file():
            return str(cand)
    return None


def run_cli(path, args, timeout=40):
    """跑一条只读命令，返回 (退出码, stdout)。任何异常都算没跑成。"""
    try:
        res = subprocess.run(
            [path] + args, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, stdin=subprocess.DEVNULL,
        )
        return res.returncode, res.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return None, ""


def cli_version(path):
    code, out = run_cli(path, ["--version"], timeout=20)
    line = out.strip().splitlines()[0].strip() if out.strip() else ""
    return line if code == 0 else None


def model(mid, tier=None, note=None):
    entry = {"id": mid, "vendor": vendor_of(mid)}
    if tier:
        entry["tier"] = tier
    if note:
        entry["note"] = note
    return entry


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def toml_string(text, key):
    """只取顶层的一个字符串字段，不解析整份文件（配置里可能有登录凭据段）。"""
    for line in text.splitlines():
        if line.lstrip().startswith("["):
            break
        m = re.match(r'\s*%s\s*=\s*"([^"]*)"' % re.escape(key), line)
        if m:
            return m.group(1)
    return None


def probe_claude(path):
    ch = {"models": [model("haiku", "low"), model("sonnet", "mid"), model("opus", "high")],
          "source": "静态档位表（claude 不提供模型清单）"}
    cfg = read_json(HOME / ".claude" / "settings.json")
    if isinstance(cfg, dict):
        if isinstance(cfg.get("model"), str):
            ch["preferred_model"] = cfg["model"]
        env = cfg.get("env")
        if isinstance(env, dict) and "ANTHROPIC_BASE_URL" in env:
            ch["warning"] = ("~/.claude/settings.json 的 env 里写了 ANTHROPIC_BASE_URL："
                             "本机所有 claude 调用都被重定向到第三方端点，这个通道不能按 Anthropic 官方算")
    return ch


def probe_codex(path):
    cache = HOME / ".codex" / "models_cache.json"
    data = read_json(cache)
    models = []
    if isinstance(data, dict):
        for m in data.get("models") or []:
            if isinstance(m, dict) and m.get("slug") and m.get("visibility") != "hide":
                models.append(model(m["slug"], note=m.get("description")))
    ch = {"models": models,
          "source": "读:~/.codex/models_cache.json" if models else "未读到模型清单（models_cache.json 缺失）"}
    try:
        pref = toml_string((HOME / ".codex" / "config.toml").read_text(encoding="utf-8", errors="replace"), "model")
    except OSError:
        pref = None
    if pref:
        ch["preferred_model"] = pref
    return ch


def probe_kimi(path):
    cfg = HOME / ".kimi-code" / "config.toml"
    models, pref = [], None
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    current = None
    for line in text.splitlines():
        head = re.match(r'\s*\[models\."([^"]+)"\]', line)
        if head:
            current = model(head.group(1))
            current["vendor"] = "Moonshot"
            models.append(current)
            continue
        if line.lstrip().startswith("["):
            current = None
            continue
        if current is not None:
            m = re.match(r'\s*display_name\s*=\s*"([^"]*)"', line)
            if m:
                current["note"] = m.group(1)
    pref = toml_string(text, "default_model")
    ch = {"models": models,
          "source": "读:~/.kimi-code/config.toml [models]" if models else "未读到模型清单（config.toml 缺失）"}
    if pref:
        ch["preferred_model"] = pref
    return ch


def probe_agy(path):
    code, out = run_cli(path, ["models"])
    models = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].strip() and " " not in parts[0].strip():
            models.append(model(parts[0].strip(), note=parts[1].strip()))
    return {"models": models,
            "source": "读:agy models" if models else "未读到模型清单（agy models 没有输出，可能未登录）"}


def probe_pi(path):
    """pi 是壳：每个已登录的 provider 各算一个通道。--list-models 只列已鉴权的。"""
    code, out = run_cli(path, ["--list-models"])
    providers, in_table = {}, False
    name = re.compile(r"^[A-Za-z0-9][\w.\[\]-]*$")
    for line in out.splitlines():
        cols = line.split()
        if cols[:2] == ["provider", "model"]:  # 表头之前的输出（告警等）不算
            in_table = True
        elif in_table and len(cols) >= 4 and name.match(cols[0]) and name.match(cols[1]):
            providers.setdefault(cols[0], []).append(model(cols[1]))
    return providers


def probe_cc_switch():
    """经 cc_switch 只读桥拿 provider 清单。只收能直接派发的：Anthropic 兼容端点且已存 key。"""
    if not os.path.exists(cc_switch.DB):
        return []
    try:
        con = cc_switch._conn()
        provs = cc_switch._providers(con)
        con.close()
    except Exception:
        return []
    out = []
    for p in provs:
        if p["app_type"] != "claude" or not (p["has_token"] and p["endpoint"]):
            continue
        tiers = {"haiku": "low", "sonnet": "mid", "opus": "high"}
        seen, models = set(), []
        for alias, tier in tiers.items():
            mid = p["tier_models"].get(alias)
            if mid and mid not in seen:
                seen.add(mid)
                models.append(model(mid, tier))
        out.append({
            "id": "cc-switch:" + p["name"], "kind": "cc-switch", "installed": True,
            "endpoint": p["endpoint"], "models": models,
            "source": "读:cc_switch.py list",
        })
    return out


def detect():
    probes = {"claude": probe_claude, "codex": probe_codex, "kimi": probe_kimi, "agy": probe_agy}
    names = list(probes) + ["pi"] + list(EXTRA_CLIS)
    paths = {n: find_cli(n) for n in names}
    with ThreadPoolExecutor(max_workers=8) as pool:  # 各家互不依赖，并行跑省等待
        version_jobs = {n: pool.submit(cli_version, paths[n]) for n in names if paths[n]}
        probe_jobs = {n: pool.submit(probe, paths[n]) for n, probe in probes.items() if paths[n]}
        pi_job = pool.submit(probe_pi, paths["pi"]) if paths["pi"] else None
        versions = {n: (version_jobs[n].result() if n in version_jobs else None) for n in names}
        probed = {n: job.result() for n, job in probe_jobs.items()}
        providers = pi_job.result() if pi_job else {}

    channels, not_found = [], []
    for name in probes:
        if not paths[name]:
            not_found.append(name)
            continue
        ch = {"id": name, "kind": "cli", "installed": True, "path": paths[name], "version": versions[name]}
        ch.update(probed[name])
        ch["isolation"] = ISOLATION.get(name, "partial")
        channels.append(ch)

    if paths["pi"]:
        for prov, models in providers.items():
            channels.append({
                "id": "pi:" + prov, "kind": "pi", "installed": True, "path": paths["pi"],
                "version": versions["pi"], "models": models, "source": "读:pi --list-models",
                "isolation": "full",
            })
        if not providers:
            channels.append({
                "id": "pi", "kind": "pi", "installed": True, "path": paths["pi"], "version": versions["pi"],
                "models": [], "source": "pi --list-models 没有列出任何已登录的 provider", "isolation": "full",
            })
    else:
        not_found.append("pi")

    for ch in probe_cc_switch():
        ch["isolation"] = "partial"
        if not paths["claude"]:
            ch["warning"] = "经 cc_switch.py 派发要用 claude CLI 作载体，本机没有找到 claude"
        channels.append(ch)

    other = []
    for name in EXTRA_CLIS:
        if paths[name]:
            other.append({"id": name, "path": paths[name], "version": versions[name]})
        else:
            not_found.append(name)

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "channels": channels,
        "other_clis": other,
        "not_found": not_found,
        "manifest": str(manifest_path()),
        "manifest_exists": manifest_path().exists(),
    }


def vendors_line(models):
    vendors = []
    for m in models:
        v = m.get("vendor") or "未识别"
        if v not in vendors:
            vendors.append(v)
    return "、".join(vendors) if vendors else "—"


def print_detect(result):
    print("本机模型入口（只读探测，未发模型请求，未读取密钥）\n")
    for ch in result["channels"]:
        ver = f"  {ch['version']}" if ch.get("version") else ""
        print(f"[{ch['id']}]{ver}")
        print(f"    厂商：{vendors_line(ch['models'])} ｜ 模型 {len(ch['models'])} 个 ｜ {ch['source']}")
        if ch.get("preferred_model"):
            print(f"    当前默认模型：{ch['preferred_model']}")
        if ch.get("warning"):
            print(f"    注意：{ch['warning']}")
    if result["other_clis"]:
        print("\n已装但没有可读的模型清单：" + "、".join(c["id"] for c in result["other_clis"]))
    if result["not_found"]:
        print("未找到：" + "、".join(result["not_found"]))
    state = "已存在" if result["manifest_exists"] else "尚未建立"
    print(f"\nmanifest：{result['manifest']}（{state}）")


# ---------- manifest ----------

def load_manifest(required=True):
    path = manifest_path()
    if not path.exists():
        if required:
            fail(f"还没有 manifest（{path}）。先跑 inventory.py detect，用户确认后再 save。", 3)
        return {"schema": SCHEMA, "entries": [], "roles": {"reviewer_first": [], "executor": None}, "notes": []}
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        fail(f"manifest 读不出来或格式不对：{path}。修好或删掉它后重新盘点。", 2)
    data.setdefault("roles", {})
    data["roles"].setdefault("reviewer_first", [])
    data["roles"].setdefault("executor", None)
    data.setdefault("notes", [])
    return data


def write_manifest(data):
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["schema"] = SCHEMA
    data["updated"] = today()
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def find_entry(data, entry_id):
    for e in data["entries"]:
        if e["id"] == entry_id:
            return e
    known = "、".join(e["id"] for e in data["entries"]) or "（空）"
    fail(f"manifest 里没有条目「{entry_id}」。现有：{known}")


def slug(text):
    """条目名只留小写字母、数字、点和连字符，在任何 shell 里都不用加引号。"""
    return re.sub(r"[^a-z0-9.]+", "-", text.lower()).strip("-.")


def build_entry(item, channels):
    """把方案里的一项核对成 manifest 条目。模型 ID 必须出自探测到的清单。"""
    channel = item.get("channel")
    tiers = item.get("tiers")
    if not channel or not isinstance(tiers, dict) or not tiers:
        fail(f"方案条目缺 channel 或 tiers：{json.dumps(item, ensure_ascii=False)}")
    bad = [t for t in tiers if t not in TIERS]
    if bad:
        fail(f"{channel}：档位只能是 low / mid / high，收到 {bad}")
    billing = item.get("billing", "unknown")
    if billing not in BILLING:
        fail(f"{channel}：billing 只能是 subscription / per-call / unknown，收到 {billing}")

    declared = channel.startswith("manual:")
    entry = {"channel": channel, "billing": billing}
    if declared:
        if not item.get("vendor"):
            fail(f"{channel}：手工申报的通道必须写 vendor")
        entry.update(kind="manual", isolation="partial", source=f"申报({today()})")
        vendors, unknown = set(), []
    else:
        ch = channels.get(channel)
        if not ch:
            fail(f"本机没有探测到通道「{channel}」。可用：{'、'.join(channels) or '（无）'}；"
                 f"探测不到的入口用 manual:<名字> 申报。")
        known = {m["id"]: m for m in ch["models"]}
        missing = [mid for mid in tiers.values() if mid not in known]
        if missing:
            fail(f"{channel}：模型 {missing} 不在它的清单里（{ch['source']}）。"
                 f"清单：{'、'.join(known) or '（空）'}")
        entry.update(kind=ch["kind"], isolation=ch.get("isolation", "partial"), source=ch["source"])
        for key in ("path", "version", "endpoint"):
            if ch.get(key):
                entry[key] = ch[key]
        vendors = {known[mid]["vendor"] for mid in tiers.values()} - {None}
        unknown = [mid for mid in tiers.values() if not known[mid]["vendor"]]

    vendor = canon_vendor(item.get("vendor"))
    if not vendor:
        if unknown or len(vendors) != 1:
            fail(f"{channel}：认不出厂商的模型 {unknown or '无'}，已认出的厂商 {sorted(vendors) or '无'}。"
                 f"一个条目只放一家厂商的模型；认不出时在方案里写明 vendor。")
        vendor = vendors.pop()
    elif vendors - {vendor} and not item.get("vendor_confirmed"):
        fail(f"{channel}：方案写的厂商是 {vendor}，但模型 ID 看起来属于 {sorted(vendors)}。"
             f"确认无误就在该条目加 \"vendor_confirmed\": true。")
    entry["vendor"] = vendor
    entry["tiers"] = {t: tiers[t] for t in TIERS if t in tiers}
    entry["id"] = slug(item.get("id") or f"{channel}.{vendor}")
    entry["smoke"] = {"status": "untested", "date": None}
    for key in ("billing_source", "note"):  # billing_source：额度算在哪份订阅上，同源的一起熔断
        if item.get(key):
            entry[key] = item[key]
    return entry


def reviewer_order(data):
    """审查顺序：用户点名排前的在先；其余订阅内的先于按次计费的，盲审隔离完整的先于部分的。"""
    ids = [e["id"] for e in data["entries"]]
    first = [i for i in data["roles"]["reviewer_first"] if i in ids]
    ranked = sorted(
        (pair for pair in enumerate(data["entries"]) if pair[1]["id"] not in first),
        key=lambda pair: (BILLING.index(pair[1]["billing"]),
                          0 if pair[1].get("isolation") == "full" else 1, pair[0]),
    )
    return first + [e["id"] for _, e in ranked]


def drop_dangling_roles(data):
    ids = {e["id"] for e in data["entries"]}
    data["roles"]["reviewer_first"] = [i for i in data["roles"]["reviewer_first"] if i in ids]
    executor = data["roles"].get("executor")
    if executor and (executor.get("entry") not in ids):
        data["roles"]["executor"] = None


def cmd_save(args):
    plan = read_json(args.plan)
    if not isinstance(plan, dict) or not isinstance(plan.get("entries"), list) or not plan["entries"]:
        fail(f"方案文件读不出来或没有 entries：{args.plan}")
    channels = {ch["id"]: ch for ch in detect()["channels"]}
    data = load_manifest(required=False)
    if args.replace:
        data["entries"] = []
    old = {e["id"]: e for e in data["entries"]}
    new_ids = []
    for item in plan["entries"]:
        entry = build_entry(item, channels)
        if entry["id"] in new_ids:
            fail(f"方案里有两个条目都叫「{entry['id']}」。同一通道同一厂商只留一条，或用 id 字段区分。")
        prev = old.get(entry["id"])
        if prev and prev.get("tiers") == entry["tiers"]:
            entry["smoke"] = prev.get("smoke", entry["smoke"])  # 模型没变，冒烟记录沿用
        for key in ("billing_source", "note"):
            if prev and prev.get(key) and key not in entry:
                entry[key] = prev[key]
        old[entry["id"]] = entry
        new_ids.append(entry["id"])
    data["entries"] = list(old.values())
    drop_dangling_roles(data)
    write_manifest(data)
    print(f"已写入 {manifest_path()}：{len(new_ids)} 个条目（共 {len(data['entries'])} 个）。")
    print_manifest(data)


def stale_days(entry):
    d = (entry.get("smoke") or {}).get("date")
    if not d:
        return None
    try:
        return (date.today() - date.fromisoformat(d)).days
    except ValueError:
        return None


def smoke_text(entry):
    smoke = entry.get("smoke") or {}
    status = smoke.get("status", "untested")
    if status == "untested":
        return "未冒烟"
    days = stale_days(entry)
    text = ("通过 " if status == "ok" else "失败 ") + (smoke.get("date") or "")
    if status == "fail" and smoke.get("reason"):
        text += f"（{smoke['reason']}）"
    if status == "ok" and days is not None and days > STALE_DAYS:
        text += f"，已过 {days} 天，派发前先冒烟"
    return text


def print_manifest(data):
    billing_text = {"subscription": "订阅内", "per-call": "按次计费", "unknown": "计费未标"}
    print(f"\n能力清单（更新于 {data.get('updated', '—')}）\n")
    for e in data["entries"]:
        tiers = " / ".join(f"{t}={e['tiers'][t]}" for t in TIERS if t in e["tiers"])
        print(f"[{e['id']}]  {e['vendor']} ｜ {billing_text[e['billing']]} ｜ 盲审隔离"
              f"{'完整' if e.get('isolation') == 'full' else '部分'} ｜ {smoke_text(e)}")
        quota = f" ｜ 额度归属 {e['billing_source']}" if e.get("billing_source") else ""
        print(f"    {tiers} ｜ 来源 {e['source']}{quota}")
        if e.get("note"):
            print(f"    备注：{e['note']}")
    vendors = sorted({e["vendor"] for e in data["entries"]})
    cross = "可用" if len(vendors) >= 2 else "不可用（只有一家厂商，同厂商复查只算复核）"
    print(f"\n厂商 {len(vendors)} 家：{'、'.join(vendors) or '—'} ｜ 交叉验证{cross}")
    print("默认审查顺序：" + (" → ".join(reviewer_order(data)) or "—"))
    executor = data["roles"].get("executor")
    print("默认执行者：" + (f"{executor['entry']}（{executor['tier']} 档）" if executor else "未设，按路由表"))
    for note in data["notes"]:
        print(f"备注（{note.get('date', '')}）：{note.get('text', '')}")


def cmd_show(args):
    data = load_manifest()
    if args.human:
        print_manifest(data)
        return
    for e in data["entries"]:
        e["stale"] = (stale_days(e) or 0) > STALE_DAYS
    data["reviewer_order"] = reviewer_order(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def describe(entry, tier):
    """按要的档位取模型；该档没配时往下找最近的一档。"""
    order = TIERS[: TIERS.index(tier) + 1][::-1] + TIERS[TIERS.index(tier) + 1:]
    used = next(t for t in order if t in entry["tiers"])
    out = {k: entry[k] for k in ("id", "channel", "kind", "vendor", "billing", "isolation") if k in entry}
    out.update(tier=used, model=entry["tiers"][used], smoke=smoke_text(entry))
    for key in ("path", "endpoint", "billing_source"):
        if entry.get(key):
            out[key] = entry[key]
    return out


def host_vendor_of(host, notes):
    vendor = HOST_VENDOR.get(host.strip().lower())
    if vendor == "Anthropic" and os.environ.get("ANTHROPIC_BASE_URL"):
        notes.append("当前会话设了 ANTHROPIC_BASE_URL，宿主走的是第三方端点，不按 Anthropic 算。")
        return None
    return vendor


def choose_reviewers(data, host, author=None, n=None, tier=None):
    """按 manifest 选审查者。返回 pick 子命令输出的那个结构，dispatch.py 也用它。"""
    entries = {e["id"]: e for e in data["entries"]}
    notes = []
    host_vendor = host_vendor_of(host, notes)
    no_author = (author or "").strip().lower() in ("none", "无")  # 被审材料不出自任何一家（如演示代码）
    explicit_author = None if no_author else canon_vendor(author)
    author = None if no_author else (explicit_author or host_vendor)
    if author:
        notes.append(f"被审产出的厂商按 {author} 算，同厂商的条目不选。")
    elif no_author:
        notes.append("没有要回避的厂商，按顺序选不同厂商。")
    else:
        notes.append(f"宿主「{host}」的底层模型不确定，不把它算作交叉验证的一方，改选两家外部厂商互审。")
    count = n or (1 if author else 2)

    picked, seen, skipped = [], set(), []
    for entry_id in reviewer_order(data):
        entry = entries[entry_id]
        if entry["vendor"] == author or entry["vendor"] in seen:
            continue
        if (entry.get("smoke") or {}).get("status") == "fail":
            skipped.append(entry_id)
            continue
        picked.append(describe(entry, tier or "high"))
        seen.add(entry["vendor"])
        if len(picked) == count:
            break

    if skipped:
        notes.append("冒烟失败的条目已跳过：" + "、".join(skipped))
    if explicit_author and host_vendor and host_vendor != explicit_author:
        notes.append(f"宿主自己（{host_vendor}）与被审产出不同厂商，也可以充当一方。")
    if any(p["billing"] == "per-call" for p in picked):
        notes.append("选中的条目里有按次计费的，派发前向用户说明。")
    if len(picked) < count:
        notes.append(f"需要 {count} 家不同厂商，manifest 里只凑得出 {len(picked)} 家。"
                     + ("交叉验证不可用，同厂商复查只算复核。" if not picked else ""))
    return {"role": "reviewer", "host": host, "author_vendor": author, "picked": picked, "notes": notes}


def mark_smoke(data, entry_id, status, reason=None):
    entry = find_entry(data, entry_id)
    entry["smoke"] = {"status": status, "date": today()}
    if reason:
        entry["smoke"]["reason"] = reason


def cmd_pick(args):
    data = load_manifest()
    if args.role == "executor":
        notes = []
        host_vendor_of(args.host, notes)
        entries = {e["id"]: e for e in data["entries"]}
        executor = data["roles"].get("executor")
        entry = entries.get(executor["entry"]) if executor else None
        if not entry:
            print(json.dumps({"role": "executor", "picked": [],
                              "notes": ["没有设默认执行者，按 SKILL.md 的路由表选。"]}, ensure_ascii=False, indent=2))
            return
        print(json.dumps({"role": "executor", "picked": [describe(entry, args.tier or executor["tier"])],
                          "notes": notes}, ensure_ascii=False, indent=2))
        return

    result = choose_reviewers(data, args.host, args.author, args.n, args.tier)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["picked"]:
        sys.exit(1)


def split_pair(text, flag):
    if "=" not in text:
        fail(f"{flag} 的写法是 条目=值，收到 {text}")
    key, value = text.split("=", 1)
    return key.strip(), value.strip()


def cmd_set(args):
    data = load_manifest()
    done = []
    for item in args.smoke or []:
        entry_id, value = split_pair(item, "--smoke")
        status, _, reason = value.partition(":")
        if status not in ("ok", "fail"):
            fail(f"--smoke 的值只能是 ok 或 fail[:原因]，收到 {value}")
        mark_smoke(data, entry_id, status, reason)
        done.append(f"{entry_id} 冒烟记为{'通过' if status == 'ok' else '失败'}")
    for item in args.billing or []:
        entry_id, value = split_pair(item, "--billing")
        if value not in BILLING:
            fail(f"--billing 的值只能是 subscription / per-call / unknown，收到 {value}")
        find_entry(data, entry_id)["billing"] = value
        done.append(f"{entry_id} 计费记为 {value}")
    if args.remove:
        for entry_id in args.remove:
            find_entry(data, entry_id)
            data["entries"] = [e for e in data["entries"] if e["id"] != entry_id]
            done.append(f"已移除 {entry_id}")
        drop_dangling_roles(data)
    if args.reviewers is not None:
        first = [i.strip() for i in args.reviewers.split(",") if i.strip()]
        for entry_id in first:
            find_entry(data, entry_id)
        data["roles"]["reviewer_first"] = first
        done.append("默认审查顺序：" + " → ".join(reviewer_order(data)))
    if args.executor is not None:
        if args.executor == "":
            data["roles"]["executor"] = None
            done.append("默认执行者已清除")
        else:
            entry_id, _, tier = args.executor.partition(":")
            entry = find_entry(data, entry_id)
            tier = tier or next(t for t in TIERS if t in entry["tiers"])
            if tier not in TIERS:
                fail(f"档位只能是 low / mid / high，收到 {tier}")
            if tier not in entry["tiers"]:
                fail(f"{entry_id} 没有 {tier} 档，已配：{'、'.join(entry['tiers'])}")
            data["roles"]["executor"] = {"entry": entry_id, "tier": tier}
            done.append(f"默认执行者：{entry_id}（{tier} 档）")
    if args.note:
        data["notes"].append({"date": today(), "text": args.note})
        done.append("已记备注")
    if not done:
        fail("没有要改的内容。可用：--smoke / --billing / --reviewers / --executor / --note / --remove")
    write_manifest(data)
    print("；".join(done) + "。")


def main():
    p = argparse.ArgumentParser(description="ai-cross 盘点：探测、保存、选人")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="只读探测本机模型入口")
    d.add_argument("--human", action="store_true", help="人类可读摘要（默认输出 JSON）")
    s = sub.add_parser("save", help="把确认过的方案写进 manifest")
    s.add_argument("--plan", required=True, help="方案 JSON 文件")
    s.add_argument("--replace", action="store_true", help="先清空旧条目")
    w = sub.add_parser("show", help="输出 manifest")
    w.add_argument("--human", action="store_true")
    k = sub.add_parser("pick", help="选默认人选")
    k.add_argument("--role", required=True, choices=["reviewer", "executor"])
    k.add_argument("--host", required=True, help="当前宿主：claude-code / codex / kimi / antigravity / 其他名字")
    k.add_argument("--author", help="被审产出出自哪家厂商（默认是宿主厂商）；none = 不回避任何一家")
    k.add_argument("--n", type=int, help="选几家（默认 1；宿主厂商不确定时 2）")
    k.add_argument("--tier", choices=TIERS)
    e = sub.add_parser("set", help="改 manifest 里的单项")
    e.add_argument("--smoke", action="append", metavar="ENTRY=ok|fail[:原因]")
    e.add_argument("--billing", action="append", metavar="ENTRY=subscription|per-call")
    e.add_argument("--reviewers", metavar="A,B", help='排在最前的审查者，其余按默认规则顺延；传 "" 恢复默认')
    e.add_argument("--executor", metavar="ENTRY[:tier]", help='默认执行者；传 "" 清除')
    e.add_argument("--note")
    e.add_argument("--remove", action="append", metavar="ENTRY")
    a = p.parse_args()

    for stream in (sys.stdout, sys.stderr):  # Windows 默认 GBK，中文输出统一成 UTF-8
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if a.cmd == "detect":
        result = detect()
        if a.human:
            print_detect(result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif a.cmd == "save":
        cmd_save(a)
    elif a.cmd == "show":
        cmd_show(a)
    elif a.cmd == "pick":
        cmd_pick(a)
    else:
        cmd_set(a)


if __name__ == "__main__":
    main()
