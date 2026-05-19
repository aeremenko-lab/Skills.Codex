#!/usr/bin/env python3
"""获取 TicNote 知识库项目/文件夹列表"""
import argparse
import json
import sys
import os
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def list_projects(token: str, appkey: str, query: str = "") -> dict:
    """调用 GET /api/v2/file-index/chats 获取项目列表

    Args:
        token: Bearer Token
        appkey: TicNote AppKey（用于确定 Base URL）
        query: 可选搜索关键词，按项目名称模糊匹配
    """
    base_url = resolve_base_url(appkey)
    print(f"🔗 Base URL: {base_url}")

    url = f"{base_url}/api/v2/file-index/chats"
    if query:
        url += f"?query={urllib.parse.quote(query)}"

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
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": body}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_output(data: dict):
    """格式化输出项目列表（仅展示序号、名称、文件数）"""
    chats = data.get("data", [])
    if not isinstance(chats, list):
        chats = data.get("data", {}).get("chats", [])

    print(f"\n📚 知识库项目列表 (共 {len(chats)} 个)\n")
    print(f"{'序号':<6} {'名称':<24} {'文件数'}")
    print("-" * 40)
    for i, chat in enumerate(chats, 1):
        name = chat.get("name", "-")
        file_num = "-"
        project_info = chat.get("projectInfo")
        if project_info:
            file_num = str(project_info.get("fileNum", "-"))
        print(f"{i:<6} {name:<24} {file_num}")


def main():
    parser = argparse.ArgumentParser(description="获取 TicNote 知识库项目/文件夹列表")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey（用于确定 Base URL）")
    parser.add_argument("--query", default="", help="搜索关键词（可选，按项目名称模糊匹配）")
    args = parser.parse_args()

    result = list_projects(args.token, args.appkey, args.query)

    if result["success"]:
        format_output(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
