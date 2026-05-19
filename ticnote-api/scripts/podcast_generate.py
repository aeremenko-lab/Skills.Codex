#!/usr/bin/env python3
"""生成播客（POST /api/podcast/generate）"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def podcast_generate(base_url: str, token: str,
                     summary_id: int = None, local_file_id: int = None) -> dict:
    """POST /api/podcast/generate

    Args:
        summary_id: 总结 ID（音频文件使用）
        local_file_id: 本地文件 ID（文档文件使用）
    二选一：音频文件传 summary_id，文档文件传 local_file_id。
    """
    url = f"{base_url}/api/podcast/generate"
    payload = {}
    if summary_id is not None:
        payload["summaryId"] = summary_id
    if local_file_id is not None:
        payload["localFileId"] = local_file_id

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
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="生成播客")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary-id", type=int, help="总结 ID（音频文件使用）")
    group.add_argument("--local-file-id", type=int, help="本地文件 ID（文档文件使用）")
    args = parser.parse_args()

    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")
    if args.summary_id:
        print(f"🆔 Summary ID: {args.summary_id}")
    else:
        print(f"🆔 Local File ID: {args.local_file_id}")

    result = podcast_generate(base_url, args.token,
                              summary_id=args.summary_id,
                              local_file_id=args.local_file_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
