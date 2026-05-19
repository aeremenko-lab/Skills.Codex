#!/usr/bin/env python3
"""知识库文件管理（批量删除、重命名、复制、移动）"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def _request(url: str, token: str, method: str, body: bytes = None) -> dict:
    """通用请求封装"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_batch(base_url: str, token: str, record_ids: list[int]) -> dict:
    """POST /api/v1/knowledge/delete/batch"""
    url = f"{base_url}/api/v1/knowledge/delete/batch"
    body = json.dumps(record_ids).encode("utf-8")
    return _request(url, token, "POST", body)


def rename(base_url: str, token: str, record_id: int,
           title: str = "", color: str = "", icon: str = "") -> dict:
    """PUT /api/v1/knowledge/edit/{recordId}"""
    url = f"{base_url}/api/v1/knowledge/edit/{record_id}"
    payload = {}
    if title:
        payload["title"] = title
    if color:
        payload["color"] = color
    if icon:
        payload["icon"] = icon
    body = json.dumps(payload).encode("utf-8")
    return _request(url, token, "PUT", body)


def copy_to(base_url: str, token: str, target_parent_id: int,
            record_ids: list[int]) -> dict:
    """POST /api/v1/knowledge/copyTo/{targetParentId}"""
    url = f"{base_url}/api/v1/knowledge/copyTo/{target_parent_id}"
    body = json.dumps(record_ids).encode("utf-8")
    return _request(url, token, "POST", body)


def move_to(base_url: str, token: str, target_parent_id: int,
            record_ids: list[int]) -> dict:
    """POST /api/v1/knowledge/moveTo/{targetParentId}"""
    url = f"{base_url}/api/v1/knowledge/moveTo/{target_parent_id}"
    body = json.dumps(record_ids).encode("utf-8")
    return _request(url, token, "POST", body)


def main():
    parser = argparse.ArgumentParser(description="知识库文件管理")
    sub = parser.add_subparsers(dest="action", required=True)

    # 批量删除
    del_p = sub.add_parser("delete", help="批量删除文件")
    del_p.add_argument("--token", required=True, help="Bearer Token")
    del_p.add_argument("--appkey", required=True, help="TicNote AppKey")
    del_p.add_argument("--record-ids", required=True, nargs="+", type=int,
                       help="要删除的 recordId 列表")

    # 重命名
    ren_p = sub.add_parser("rename", help="文件重命名")
    ren_p.add_argument("--token", required=True, help="Bearer Token")
    ren_p.add_argument("--appkey", required=True, help="TicNote AppKey")
    ren_p.add_argument("--record-id", required=True, type=int, help="recordId")
    ren_p.add_argument("--title", default="", help="新标题/文件名")
    ren_p.add_argument("--color", default="", help="颜色")
    ren_p.add_argument("--icon", default="", help="图标")

    # 复制
    cp_p = sub.add_parser("copy", help="复制文件到目标目录")
    cp_p.add_argument("--token", required=True, help="Bearer Token")
    cp_p.add_argument("--appkey", required=True, help="TicNote AppKey")
    cp_p.add_argument("--target-parent-id", required=True, type=int,
                      help="目标目录 recordId")
    cp_p.add_argument("--record-ids", required=True, nargs="+", type=int,
                      help="要复制的 recordId 列表")

    # 移动
    mv_p = sub.add_parser("move", help="移动文件到目标目录")
    mv_p.add_argument("--token", required=True, help="Bearer Token")
    mv_p.add_argument("--appkey", required=True, help="TicNote AppKey")
    mv_p.add_argument("--target-parent-id", required=True, type=int,
                      help="目标目录 recordId")
    mv_p.add_argument("--record-ids", required=True, nargs="+", type=int,
                      help="要移动的 recordId 列表")

    args = parser.parse_args()
    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")

    if args.action == "delete":
        print(f"🗑️  批量删除: {args.record_ids}")
        result = delete_batch(base_url, args.token, args.record_ids)
    elif args.action == "rename":
        print(f"✏️  重命名: recordId={args.record_id}")
        result = rename(base_url, args.token, args.record_id,
                        title=args.title, color=args.color, icon=args.icon)
    elif args.action == "copy":
        print(f"📋 复制: {args.record_ids} → {args.target_parent_id}")
        result = copy_to(base_url, args.token, args.target_parent_id, args.record_ids)
    elif args.action == "move":
        print(f"📦 移动: {args.record_ids} → {args.target_parent_id}")
        result = move_to(base_url, args.token, args.target_parent_id, args.record_ids)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
