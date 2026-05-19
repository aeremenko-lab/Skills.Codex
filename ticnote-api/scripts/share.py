#!/usr/bin/env python3
"""分享文件（创建分享 + 访问分享）"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def create_share(base_url: str, token: str, share_type: str,
                 share_data: str) -> dict:
    """POST /api/share/{shareType} — 创建分享

    Args:
        share_type: audio | localFile
        share_data: 请求体 JSON 字符串
    """
    url = f"{base_url}/api/share/{share_type}"
    body = share_data.encode("utf-8")
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


def get_share(base_url: str, share_type: str, share_code: str) -> dict:
    """GET /api/share/{shareType}/{shareCode} — 访问分享（无需认证）"""
    url = f"{base_url}/api/share/{share_type}/{share_code}"
    req = urllib.request.Request(url, method="GET")
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
    parser = argparse.ArgumentParser(description="分享文件（创建 / 访问）")
    sub = parser.add_subparsers(dest="action", required=True)

    # 创建分享
    create_p = sub.add_parser("create", help="创建分享链接")
    create_p.add_argument("--token", required=True, help="Bearer Token")
    create_p.add_argument("--appkey", required=True, help="TicNote AppKey")
    create_p.add_argument("--share-type", required=True, choices=["audio", "localFile"],
                          help="分享类型: audio / localFile")
    create_p.add_argument("--data", required=True, help="请求体 JSON 字符串")

    # 访问分享
    get_p = sub.add_parser("get", help="通过分享码访问分享内容")
    get_p.add_argument("--appkey", required=True, help="TicNote AppKey（用于确定 Base URL）")
    get_p.add_argument("--share-type", required=True, choices=["audio", "localFile"],
                       help="分享类型: audio / localFile")
    get_p.add_argument("--share-code", required=True, help="分享码")

    args = parser.parse_args()
    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")

    if args.action == "create":
        print(f"📤 创建分享: type={args.share_type}")
        result = create_share(base_url, args.token, args.share_type, args.data)
    else:
        print(f"📥 访问分享: type={args.share_type}, code={args.share_code}")
        result = get_share(base_url, args.share_type, args.share_code)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
