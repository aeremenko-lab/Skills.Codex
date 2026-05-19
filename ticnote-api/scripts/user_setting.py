#!/usr/bin/env python3
"""用户设置（GET/PUT /api/v1/user/setting）"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def get_setting(base_url: str, token: str) -> dict:
    """GET /api/v1/user/setting"""
    url = f"{base_url}/api/v1/user/setting"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET",
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


def put_setting(base_url: str, token: str, setting_json: str) -> dict:
    """PUT /api/v1/user/setting

    Args:
        setting_json: 设置内容 JSON 字符串
    """
    url = f"{base_url}/api/v1/user/setting"
    body = setting_json.encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="PUT",
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
    parser = argparse.ArgumentParser(description="用户设置（获取 / 保存）")
    sub = parser.add_subparsers(dest="action", required=True)

    # 获取设置
    get_p = sub.add_parser("get", help="获取当前用户设置")
    get_p.add_argument("--token", required=True, help="Bearer Token")
    get_p.add_argument("--appkey", required=True, help="TicNote AppKey")

    # 保存设置
    put_p = sub.add_parser("put", help="保存用户设置")
    put_p.add_argument("--token", required=True, help="Bearer Token")
    put_p.add_argument("--appkey", required=True, help="TicNote AppKey")
    put_p.add_argument("--data", required=True, help="设置内容 JSON 字符串")

    args = parser.parse_args()
    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")

    if args.action == "get":
        print("📋 获取用户设置...")
        result = get_setting(base_url, args.token)
    else:
        print("💾 保存用户设置...")
        result = put_setting(base_url, args.token, args.data)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
