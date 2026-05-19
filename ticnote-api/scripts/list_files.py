#!/usr/bin/env python3
"""获取 TicNote 项目下的文件列表（文件树）"""
import argparse
import json
import sys
import os
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


def list_files(token: str, appkey: str, root_id: str) -> dict:
    """调用 GET /api/v1/file-index/file-tree 获取项目下文件列表

    重要：此接口始终传顶层项目 ID（project_id）作为 rootId。
    子目录的文件通过响应中节点的 children 字段递归获取，
    而非对子目录 ID 再次调用本接口（那样会返回空）。

    Args:
        token: Bearer Token
        appkey: TicNote AppKey（用于确定 Base URL）
        root_id: 顶层项目 ID（project_id）
    """
    base_url = resolve_base_url(appkey)
    print("🔗 Base URL: " + base_url)

    url = base_url + "/api/v1/file-index/file-tree?rootId=" + urllib.parse.quote(str(root_id))

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + token,
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


def flatten_tree(nodes, depth=0):
    """递归展平文件树，返回 (depth, node) 列表

    子目录节点本身也会包含在列表中（标记为目录），
    其 children 的文件紧随其后缩进展示。
    """
    result = []
    for node in nodes:
        result.append((depth, node))
        children = node.get("children", [])
        if children:
            result.extend(flatten_tree(children, depth + 1))
    return result


def find_node_by_id(nodes, target_id):
    """在文件树中递归查找指定 ID 的节点"""
    for node in nodes:
        if node.get("id") == target_id:
            return node
        children = node.get("children", [])
        if children:
            found = find_node_by_id(children, target_id)
            if found:
                return found
    return None


def is_directory(node):
    """判断节点是否为目录"""
    return str(node.get("fileType", "")) == "0" or node.get("type") == "directory"


def print_tree(nodes, depth=0, parent_num="", counter=None, prefix=""):
    """递归打印文件树，用树形符号 + 层级编号体现层级关系

    编号规则：顶层为 1, 2, 3...；子层为 4.1, 4.2...；更深层为 4.1.1, 4.1.2...

    Args:
        nodes: 当前层节点列表
        depth: 当前缩进层级
        parent_num: 父节点编号字符串（如 "4"），用于拼接子编号
        counter: 当前层计数器列表
        prefix: 当前行的树形前缀（如 "│  "）
    """
    if counter is None:
        counter = [0]
    for idx, node in enumerate(nodes):
        counter[0] += 1
        name = node.get("name", "-")
        ftype = str(node.get("fileType", "-"))
        rid = node.get("id", "-")
        children = node.get("children", [])
        is_last = (idx == len(nodes) - 1)

        # 计算当前节点编号
        if parent_num:
            num = parent_num + "." + str(counter[0])
        else:
            num = str(counter[0])

        if depth == 0:
            connector = ""
            child_prefix = ""
        else:
            connector = "└─ " if is_last else "├─ "
            child_prefix = prefix + ("   " if is_last else "│  ")

        if is_directory(node):
            print(num + ". " + prefix + connector + "📁 " + name)
            if children:
                print_tree(children, depth + 1, num, [0], child_prefix)
        else:
            print(num + ". " + prefix + connector + name)


def format_output(data: dict, dir_id: str = None):
    """格式化输出文件列表

    Args:
        data: API 响应数据
        dir_id: 若指定，则只展示该子目录下的文件；否则展示整棵树（含子目录展开）
    """
    file_tree = data.get("fileTree", [])

    if dir_id:
        node = find_node_by_id(file_tree, dir_id)
        if not node:
            print("❌ 未找到 ID 为 " + dir_id + " 的目录节点")
            return
        dir_name = node.get("name", dir_id)
        children = node.get("children", [])
        flat = flatten_tree(children)
        print("\n📁 [" + dir_name + "] 目录下共 " + str(len(flat)) + " 个文件\n")
        print_tree(children, depth=1, parent_num="", counter=[0], prefix="")
    else:
        flat = flatten_tree(file_tree)
        print("\n📁 文件列表 (共 " + str(len(flat)) + " 个，含子目录展开)\n")
        print_tree(file_tree, depth=0, parent_num="", counter=[0], prefix="")


def main():
    parser = argparse.ArgumentParser(description="获取 TicNote 项目下的文件列表")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey（用于确定 Base URL）")
    parser.add_argument("--root-id", required=True, help="顶层项目 ID（project_id）")
    parser.add_argument(
        "--dir-id",
        default=None,
        help="子目录节点 ID（可选）。指定后只展示该目录下的文件，"
             "文件通过父项目树的 children 字段解析，无需单独调用接口",
    )
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = parser.parse_args()

    result = list_files(args.token, args.appkey, args.root_id)

    if result["success"]:
        if args.json:
            print(json.dumps(result["data"], ensure_ascii=False, indent=2))
        else:
            format_output(result["data"], dir_id=args.dir_id)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
