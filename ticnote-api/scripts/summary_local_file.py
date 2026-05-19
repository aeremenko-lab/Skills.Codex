#!/usr/bin/env python3
"""文件总结 - 非音频文件（POST /api/project/project/summary/local_file）"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def summary_local_file(base_url: str, token: str, task_id: int,
                       model: str = "", detail_level: str = "") -> dict:
    """POST /api/project/project/summary/local_file

    Args:
        task_id: 文件 ID（即 fileId）
        model: 总结模型，如 qwen-max-latest、o4-mini
        detail_level: 详细程度，如 more_details
    """
    params = {"taskId": task_id}
    if model:
        params["model"] = model
    if detail_level:
        params["detailLevel"] = detail_level

    url = f"{base_url}/api/project/project/summary/local_file?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
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
    parser = argparse.ArgumentParser(description="文件总结（非音频文件）")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey")
    parser.add_argument("--file-id", required=True, type=int, help="文件 ID (fileId，即 taskId)")
    parser.add_argument("--model", default="", help="总结模型，如 qwen-max-latest、o4-mini")
    parser.add_argument("--detail-level", default="", help="详细程度，如 more_details")
    args = parser.parse_args()

    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")
    print(f"🆔 File ID: {args.file_id}")

    result = summary_local_file(
        base_url, args.token, args.file_id,
        model=args.model, detail_level=args.detail_level,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
