#!/usr/bin/env python3
"""翻译（POST /api/v1/translate）"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def translate(base_url: str, token: str, transcribe_id: int,
              target_language: str) -> dict:
    """POST /api/v1/translate

    Args:
        transcribe_id: 转写 ID（来自 file-detail 响应的 transcribeId）
        target_language: 目标语言代码，如 en、zh、ja
    """
    url = f"{base_url}/api/v1/translate"
    payload = {
        "transcribeId": transcribe_id,
        "targetLanguage": target_language,
    }
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
    parser = argparse.ArgumentParser(description="翻译转写内容")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey")
    parser.add_argument("--transcribe-id", required=True, type=int, help="转写 ID (transcribeId)")
    parser.add_argument("--target-language", required=True, help="目标语言代码，如 en、zh、ja")
    args = parser.parse_args()

    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")
    print(f"🆔 Transcribe ID: {args.transcribe_id}")
    print(f"🌐 Target Language: {args.target_language}")

    result = translate(base_url, args.token, args.transcribe_id, args.target_language)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
