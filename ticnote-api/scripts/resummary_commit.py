#!/usr/bin/env python3
"""重新总结 - 音频文件（POST /api/v1/task/resummary/commit）"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def resummary_commit(base_url: str, token: str, file_id: int,
                     model: str = "", detail_level: str = "",
                     lang: str = "", has_speakers: bool = False,
                     template: str = "", template_customize: str = "") -> dict:
    """POST /api/v1/task/resummary/commit"""
    url = f"{base_url}/api/v1/task/resummary/commit"
    payload = {"fileId": file_id}
    if model:
        payload["model"] = model
    if detail_level:
        payload["detailLevel"] = detail_level
    if lang:
        payload["lang"] = lang
    if has_speakers:
        payload["hasSpeakers"] = True
    if template:
        payload["template"] = template
    if template_customize:
        payload["templateCustomize"] = template_customize

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="重新总结（音频文件）")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey")
    parser.add_argument("--file-id", required=True, type=int, help="文件 ID (fileId)")
    parser.add_argument("--model", default="", help="总结模型，如 qwen-max-latest、o4-mini")
    parser.add_argument("--detail-level", default="", help="详细程度，如 more_details")
    parser.add_argument("--lang", default="", help="输入文本的语言，如 zh、en")
    parser.add_argument("--has-speakers", action="store_true", help="是否区分说话人")
    parser.add_argument("--template", default="", help="模板")
    parser.add_argument("--template-customize", default="", help="用户自定义模板")
    args = parser.parse_args()

    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")
    print(f"🆔 File ID: {args.file_id}")

    result = resummary_commit(
        base_url, args.token, args.file_id,
        model=args.model, detail_level=args.detail_level,
        lang=args.lang, has_speakers=args.has_speakers,
        template=args.template, template_customize=args.template_customize,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
