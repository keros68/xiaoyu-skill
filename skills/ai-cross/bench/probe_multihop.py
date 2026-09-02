"""探针：d-multihop 开思考臂的错误全是同一个值 (4,5)——是共识错误还是判分 bug？

主跑没存原始 content（只有 note 前 60 字），无法事后检查。
重跑 3 次 GLM-5.2 + 2 次 DeepSeek（thinking on），打印完整 content 逐字检查。
"""
import json, urllib.request, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks_depth import D_MULTIHOP, v_multihop

KEY = pathlib.Path(r"C:\Users\keros\.claude\jobs\a04d5793\tmp\sf_key.txt").read_text().strip()
URL = "https://api.siliconflow.cn/v1/chat/completions"

for model, n in [("zai-org/GLM-5.2", 3), ("deepseek-ai/DeepSeek-V4-Pro", 2)]:
    for i in range(n):
        body = {"model": model, "max_tokens": 16384,
                "messages": [{"role": "user", "content": D_MULTIHOP}]}
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST")
        req.add_header("content-type", "application/json")
        req.add_header("authorization", "Bearer " + KEY)
        with urllib.request.urlopen(req, timeout=300) as resp:
            d = json.loads(resp.read())
        ch = d["choices"][0]["message"]
        content = (ch.get("content") or "").strip()
        ok, _, note = v_multihop(content)
        print(f"=== {model} #{i+1}  判分={'✅' if ok else '❌'} ===")
        print(f"content 全文（repr）: {content!r}")
        print(f"note: {note}\n")
