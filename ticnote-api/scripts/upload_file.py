#!/usr/bin/env python3
"""上传文件到 TicNote 知识库（三步流程：获取签名 → PUT 上传 COS → 注册知识库）"""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
import sys
import uuid
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url, resolve_cos_config
from list_files import list_files


# ─── 工具函数 ───

def build_cos_key(file_path: str, appkey: str) -> str:
    """构建 COS 存储 key: {env}/{YYYY-MM}/{uuid}.{ext}

    与前端 UploadTool.ts _joinFileName 逻辑一致：
    - env: ticnote-web-prd / ticnote-web-sit
    - 文件名: uuid (不含连字符的 32 位 hex)
    - ext: 文件扩展名
    """
    cos_config = resolve_cos_config(appkey)
    year_month = datetime.now().strftime("%Y-%m")

    filename = os.path.basename(file_path)
    ext = ""
    dot_index = filename.rfind(".")
    if dot_index > 0:
        ext = filename[dot_index + 1:].lower()

    file_uuid = uuid.uuid4().hex  # 32 位 hex，无连字符
    if ext:
        return f"{cos_config.env}/{year_month}/{file_uuid}.{ext}"
    return f"{cos_config.env}/{year_month}/{file_uuid}"


def compute_file_md5(file_path: str) -> str:
    """计算文件内容的 MD5 哈希值，返回 Base64 编码（腾讯云 COS Content-MD5 要求）"""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)  # 4MB 分片，与前端 sliceSize 一致
            if not chunk:
                break
            md5.update(chunk)
    return base64.b64encode(md5.digest()).decode("ascii")


def guess_content_type(file_path: str) -> str:
    """根据文件扩展名猜测 MIME 类型

    与前端 UploadTool.ts getContentType 对齐，
    mimetypes 模块覆盖了绝大部分常见类型。
    """
    ct, _ = mimetypes.guess_type(file_path)
    return ct or "application/octet-stream"


# ─── 步骤一：获取 COS 上传签名 ───

def get_upload_token(base_url: str, token: str, bucket: str, cos_key: str,
                     content_type: str = "", content_md5: str = "",
                     method: str = "PUT") -> dict:
    """GET /api/v1/tencent/oss/apply/token — 获取 COS 上传签名

    参数与前端 ufile_tencent.js getUFileToken 一致：
    - method: 上传方式（普通上传 PUT，分片初始化 POST）
    - bucket: COS Bucket 名称
    - key: COS 文件路径（URL 编码由 urlencode 自动处理）
    - content_md5: 文件 MD5（可为空）
    - contentType: MIME 类型
    - date: 空字符串

    返回值为 JSON，签名在 .data 字段中（普通上传）。
    """
    params = urllib.parse.urlencode({
        "method": method,
        "bucket": bucket,
        "key": cos_key,
        "content_md5": content_md5,
        "contentType": content_type or "",
        "date": "",
    })
    url = f"{base_url}/api/v1/tencent/oss/apply/token?{params}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8").strip()
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    if data.get("code") is not None and data.get("code") != 0:
                        return {"success": False, "error": f"获取签名失败: {data}"}
                    # 普通上传用 .data，分片上传用 .auth
                    auth = data.get("data") or data.get("auth") or body
                    return {"success": True, "authorization": auth}
                return {"success": True, "authorization": body}
            except (json.JSONDecodeError, ValueError):
                return {"success": True, "authorization": body}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": err_body}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 步骤二：PUT 上传文件到腾讯云 COS ───

def upload_to_cos(file_path: str, bucket: str, region: str, cos_key: str,
                  authorization: str, content_type: str = "",
                  content_md5: str = "") -> dict:
    """使用签名直接 PUT 上传文件到腾讯云 COS

    与前端 ufile_tencent.js uploadFile 一致：
    - method: PUT
    - Authorization: 签名字符串
    - Content-MD5: 文件 MD5（前端会传）
    - Content-Type: MIME 类型
    """
    cos_url = f"https://{bucket}.cos.{region}.myqcloud.com/{cos_key}"

    with open(file_path, "rb") as f:
        file_data = f.read()

    headers = {
        "Authorization": authorization,
    }
    if content_type:
        headers["Content-Type"] = content_type
    if content_md5:
        headers["Content-MD5"] = content_md5

    print(f"☁️  上传到 COS: {cos_key}")
    print(f"   URL: {cos_url}")

    req = urllib.request.Request(
        cos_url,
        data=file_data,
        headers=headers,
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            print(f"✅ COS 上传成功 (HTTP {resp.status})")
            return {"success": True, "file_url": cos_url, "cos_key": cos_key}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": f"COS 上传失败 (HTTP {e.code}): {err_body}"}
    except Exception as e:
        return {"success": False, "error": f"COS 上传失败: {e}"}


# ─── 步骤三：注册文件到知识库 ───

def register_to_knowledge(base_url: str, token: str, file_path: str,
                           file_url: str, parent_id: str = None) -> dict:
    """POST /api/v1/knowledge/upload"""
    filename = os.path.basename(file_path)
    ext = ""
    dot_index = filename.rfind(".")
    if dot_index > 0:
        ext = filename[dot_index + 1:].lower()

    payload = [
        {
            "fileName": filename,
            "fileType": ext or "unknown",
            "fileUrl": file_url,
        }
    ]

    url = f"{base_url}/api/v1/knowledge/upload"
    if parent_id:
        url += f"?parentId={parent_id}"

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # 检查业务层错误码
            biz_code = data.get("code")
            if biz_code is not None and biz_code != 0 and biz_code != 200:
                error_msg = data.get("msg", "未知错误")
                # code 503 通常是当前用户对该项目无写入权限
                if biz_code == 503:
                    error_msg = (
                        f"无权限写入该项目（parentId={parent_id}）。"
                        f"当前 AppKey 对应的账号不是该项目的 owner，无法上传文件到他人项目。"
                        f"请选择当前账号拥有的项目，或使用对应 owner 的 AppKey。"
                    )
                return {
                    "success": False,
                    "error": error_msg,
                    "biz_code": biz_code,
                    "data": data,
                }
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": error_body}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 步骤四：从文件列表确认真实 fileId ───

def confirm_file_id(base_url: str, token: str, parent_id: str, filename: str) -> str:
    """通过文件列表接口查找刚上传的文件，返回真实的 fileId。

    注册接口返回的 fileId 可能与实际入库的不一致，
    需要通过 GET /api/v1/file-index/file-tree 确认。
    """
    url = f"{base_url}/api/v1/file-index/file-tree?rootId={urllib.parse.quote(str(parent_id))}"
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
            file_tree = data.get("fileTree", [])
            # 按文件名匹配，取最新创建的（createTimestamp 最大）
            matches = [f for f in file_tree if f.get("name") == filename]
            if matches:
                matches.sort(key=lambda x: x.get("createTimestamp", 0), reverse=True)
                return matches[0].get("fileId", "")
    except Exception:
        pass
    return ""


# ─── 获取项目列表（用于目录选择） ───

def fetch_projects(base_url: str, token: str) -> dict:
    """GET /api/v2/file-index/chats 获取项目列表"""
    url = f"{base_url}/api/v2/file-index/chats"
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


def extract_projects(api_data: dict) -> list[dict]:
    """从接口响应中提取项目列表，返回 [{project_id, name, file_num}, ...]"""
    raw = api_data.get("data", api_data)
    chats = raw if isinstance(raw, list) else raw.get("chats", [])
    projects = []
    for chat in chats:
        pid = chat.get("project_id")
        if not pid:
            continue
        name = chat.get("name", "-")
        file_num = "-"
        project_info = chat.get("projectInfo")
        if project_info:
            file_num = project_info.get("fileNum", "-")
        projects.append({"project_id": str(pid), "name": name, "file_num": file_num})
    return projects


def prompt_select_project(token: str, appkey: str) -> dict:
    """获取项目列表并输出，供调用方让用户选择。

    输出 ACTION_REQUIRED 标记 + 项目列表 JSON，调用方解析后展示给用户。
    用户可以选择某个项目，也可以跳过（不选），跳过时 agent 以 parentId 为空上传。

    Returns:
        {"action": "select_project", "projects": [...]} 或 错误 dict
    """
    base_url = resolve_base_url(appkey)
    print("📂 未指定目标目录，正在获取项目列表...")
    result = fetch_projects(base_url, token)
    if not result["success"]:
        return result

    projects = extract_projects(result["data"])
    if not projects:
        print("⚠️  未找到任何项目，文件将上传到默认目录")
        return {"action": "no_projects"}

    print(f"\n📚 找到 {len(projects)} 个项目，请选择上传目标目录：\n")
    print(f"  {'序号':<6} {'名称':<24} {'文件数'}")
    print("  " + "-" * 40)
    for i, p in enumerate(projects, 1):
        print(f"  {i:<6} {p['name']:<24} {p['file_num']}")
    print()
    print("💡 请选择一个项目，或直接让我继续（将上传到默认目录）")

    # 输出机器可读标记，供 agent 解析
    print(f"\nACTION_REQUIRED: SELECT_PROJECT")
    print(json.dumps({"action": "select_project", "projects": projects}, ensure_ascii=False))

    return {"action": "select_project", "projects": projects}


# ─── 去重检查 ───

def check_duplicate(token: str, appkey: str, file_path: str, parent_id: str) -> dict | None:
    """检查目标项目中是否已存在同名文件。

    Args:
        token: Bearer Token
        appkey: TicNote AppKey
        file_path: 本地文件路径
        parent_id: 目标项目 ID

    Returns:
        已存在的文件节点 dict（含 id/name/fileType 等），不存在则返回 None
    """
    if not parent_id:
        return None  # 未指定目录时无法检查，跳过

    filename = os.path.basename(file_path)
    result = list_files(token, appkey, parent_id)
    if not result["success"]:
        # 查询失败不阻塞上传，仅打印警告
        print(f"⚠️  去重检查失败（不影响上传）: {result.get('error', '未知错误')}")
        return None

    file_tree = result["data"].get("fileTree", [])

    def find_in_tree(nodes):
        for node in nodes:
            if node.get("name") == filename and node.get("type") == "file":
                return node
            children = node.get("children", [])
            if children:
                found = find_in_tree(children)
                if found:
                    return found
        return None

    return find_in_tree(file_tree)


# ─── 主流程 ───

def upload_file(token: str, appkey: str, file_path: str, parent_id: str = None) -> dict:
    """完整上传流程：去重检查 → 构建 key → 获取签名 → PUT 上传 COS → 注册知识库"""
    if not os.path.isfile(file_path):
        return {"success": False, "error": f"文件不存在: {file_path}"}

    # 去重检查：目标项目中已存在同名文件时跳过上传
    if parent_id:
        print("\n🔍 检查是否已存在同名文件...")
        existing = check_duplicate(token, appkey, file_path, parent_id)
        if existing:
            print(f"⚠️  文件已存在，跳过上传:")
            print(f"   名称: {existing.get('name')}")
            print(f"   recordId: {existing.get('id')}")
            print(f"   fileType: {existing.get('fileType')}")
            return {
                "success": True,
                "skipped": True,
                "reason": "duplicate",
                "existing_file": existing,
                "data": {
                    "totalCount": 0,
                    "successCount": 0,
                    "failedCount": 0,
                    "message": f"文件 '{existing.get('name')}' 已存在于目标项目中 (recordId: {existing.get('id')})"
                }
            }
        print("✅ 无重复文件，继续上传")

    base_url = resolve_base_url(appkey)
    print(f"🔗 Base URL: {base_url}")

    # 获取 COS 配置
    cos_config = resolve_cos_config(appkey)
    cos_key = build_cos_key(file_path, appkey)
    content_type = guess_content_type(file_path)
    content_md5 = compute_file_md5(file_path)
    print(f"📦 COS Key: {cos_key}")
    print(f"🪣 Bucket: {cos_config.bucket} ({cos_config.region})")
    print(f"📄 Content-Type: {content_type}")
    print(f"🔑 Content-MD5: {content_md5}")

    # 步骤一：获取上传签名（普通上传用 PUT）
    print("\n📋 步骤一：获取 COS 上传签名...")
    token_result = get_upload_token(base_url, token, cos_config.bucket, cos_key,
                                     content_type, content_md5, method="PUT")
    if not token_result["success"]:
        print(f"❌ {token_result.get('error', '未知错误')}")
        return token_result

    authorization = token_result["authorization"]
    print(f"✅ 签名获取成功")

    # 步骤二：PUT 上传文件到 COS
    print("\n📋 步骤二：上传文件到腾讯云 COS...")
    cos_result = upload_to_cos(file_path, cos_config.bucket, cos_config.region,
                                cos_key, authorization, content_type, content_md5)
    if not cos_result["success"]:
        print(f"❌ {cos_result.get('error', '未知错误')}")
        return cos_result

    # 注册到知识库时使用 CDN URL（与前端 UploadTool.ts 一致：_bucketUrlCDN + "/" + key）
    file_url = f"{cos_config.cdn}/{cos_key}"
    print(f"🌐 CDN URL: {file_url}")

    # 步骤三：注册到知识库
    print("\n📋 步骤三：注册文件到知识库...")
    reg_result = register_to_knowledge(base_url, token, file_path, file_url, parent_id)
    if not reg_result["success"]:
        print(f"❌ {reg_result.get('error', '未知错误')}")
        return reg_result

    reg_data = reg_result.get("data", {})
    data_inner = reg_data.get("data", reg_data)
    success_count = data_inner.get("successCount", 0)
    failed_count = data_inner.get("failedCount", 0)
    print(f"✅ 注册完成: 成功 {success_count}, 失败 {failed_count}")

    if failed_count > 0:
        failed_files = data_inner.get("failedFiles", [])
        for f in failed_files:
            print(f"   ⚠️ {f.get('fileName')}: {f.get('failureReason', '未知原因')}")

    # 步骤四：从文件列表确认真实 fileId
    # 注册接口返回的 fileId 可能与实际入库的不一致，需要通过文件列表确认
    if success_count > 0 and parent_id:
        print("\n📋 步骤四：确认真实文件 ID...")
        confirmed_file_id = confirm_file_id(base_url, token, parent_id, os.path.basename(file_path))
        if confirmed_file_id:
            print(f"✅ 确认 fileId: {confirmed_file_id}")
            reg_result["confirmed_file_id"] = confirmed_file_id
        else:
            # fallback: 使用注册接口返回的 fileId
            fallback_id = None
            success_files = data_inner.get("successFiles", [])
            if success_files:
                fallback_id = success_files[0].get("fileId")
            if fallback_id:
                print(f"⚠️ 未能从文件列表确认，使用注册返回的 fileId: {fallback_id}")
                reg_result["confirmed_file_id"] = fallback_id

    return reg_result


def main():
    parser = argparse.ArgumentParser(description="上传文件到 TicNote 知识库")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey（用于确定 Base URL 和 COS 环境）")
    parser.add_argument("--file", required=True, help="要上传的文件路径")
    parser.add_argument("--parent-id", default=None, help="父目录 ID（即 project_id），不传则先列出项目让用户选择")
    args = parser.parse_args()

    file_path = os.path.abspath(args.file)
    file_size = os.path.getsize(file_path)
    print(f"📁 准备上传: {os.path.basename(file_path)} ({file_size / 1024:.1f} KB)")

    # 未提供 parent_id 时，先获取项目列表让用户选择
    if not args.parent_id:
        select_result = prompt_select_project(args.token, args.appkey)
        if select_result.get("action") == "select_project":
            # 需要用户选择，脚本到此结束，等待用户指定 --parent-id 后重新运行
            sys.exit(0)
        # action == "no_projects": 没有项目，继续上传到根目录
        # 其他情况：获取列表失败
        if not select_result.get("action"):
            print(json.dumps(select_result, ensure_ascii=False, indent=2))
            sys.exit(1)

    result = upload_file(args.token, args.appkey, file_path, args.parent_id)
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))

    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
