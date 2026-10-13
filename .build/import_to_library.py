# -*- coding: utf-8 -*-
"""把本地 zip 导入资料库页面。

绕开 page/import_html.py 的字段过期问题：后端 get-upload-credential 现在
返回 confirmKey / taskId（不再是 cosKey），这里按新字段走完整三步——
取凭证 → PUT 到 COS → 触发导入。
"""
import json
import os
import subprocess
import sys
import urllib.request

SKILL = r"C:\Program Files\WorkBuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\library"
SPACE_API = os.path.join(SKILL, "space_api.py")
PY = sys.executable or "python3"


def call(api: str, body: dict) -> dict:
    p = subprocess.run(
        [PY, SPACE_API, api, "--stdin"],
        input=json.dumps(body).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out = p.stdout.decode("utf-8", "replace").strip()
    if p.returncode != 0 or not out:
        raise RuntimeError(f"{api} 无输出: {p.stderr.decode('utf-8','replace')[:300]}")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError(f"{api} 返回非 JSON: {out[:300]}")


def main(argv) -> int:
    args = [a for a in argv if not a.startswith('--')]
    node_block_id = ''
    for a in argv:
        if a.startswith('--node-block-id='):
            node_block_id = a.split('=', 1)[1].strip()
    if len(args) < 3:
        print('用法: import_to_library.py <zip> <显示名> <标题> [--node-block-id=xxx]', file=sys.stderr)
        return 2
    path, display_name, title = args[0], args[1], args[2]

    size = os.path.getsize(path)
    with open(path, "rb") as f:
        content = f.read()

    cred = call("space.importer.get-upload-credential",
                {"fileName": display_name, "fileSize": size})
    data = cred.get("data") or {}
    if cred.get("code") not in (0, None) and not data:
        raise RuntimeError(f"取凭证失败: {json.dumps(cred, ensure_ascii=False)[:300]}")

    upload_url, headers = data.get("uploadUrl"), data.get("headers") or {}
    if not upload_url:
        raise RuntimeError("凭证里没有 uploadUrl")

    req = urllib.request.Request(upload_url, data=content, method="PUT")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        print("PUT ->", r.status, flush=True)

    payload = {"fileName": display_name, "title": title}
    if node_block_id:
        payload["nodeBlockId"] = node_block_id
    if data.get("confirmKey"):
        payload["confirmKey"] = data["confirmKey"]
    if data.get("taskId"):
        payload["taskId"] = data["taskId"]
    if data.get("cosKey"):
        payload["cosKey"] = data["cosKey"]

    res = call("space.importer.import-local-file", payload)
    print("KS_IMPORT_RAW", json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
