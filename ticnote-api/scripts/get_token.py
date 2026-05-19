#!/usr/bin/env python3
"""通过 AppKey 登录获取 TicNote JWT Token"""
import argparse
import json
import sys
import os
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url, APPKEY_PREFIX_MAP

VALID_PREFIXES = [p for p, _ in APPKEY_PREFIX_MAP]


def diagnose_appkey(appkey: str) -> list[str]:
    """诊断 AppKey 可能存在的问题，返回提示列表"""
    hints = []

    # 1. 空值 / 空白
    if not appkey or not appkey.strip():
        hints.append("AppKey 为空，请检查是否正确复制")
        return hints

    stripped = appkey.strip()
    if stripped != appkey:
        hints.append("AppKey 首尾有多余空格，请去除后重试")

    # 2. 前缀检查
    has_valid_prefix = any(stripped.startswith(p) for p in VALID_PREFIXES)
    if not has_valid_prefix:
        hints.append(
            f"AppKey 前缀不正确。当前值开头为: '{stripped[:20]}...'\n"
            f"   合法前缀: {', '.join(VALID_PREFIXES)}"
        )

    # 3. 长度检查（前缀 + UUID，最短也应 > 20 字符）
    if len(stripped) < 20:
        hints.append(f"AppKey 长度异常（仅 {len(stripped)} 字符），可能复制不完整")

    # 4. 非法字符
    import re
    if not re.match(r'^[a-zA-Z0-9_\-]+$', stripped):
        hints.append("AppKey 包含非法字符，应仅包含字母、数字、下划线和连字符")

    # 5. 环境提醒
    if has_valid_prefix:
        for prefix, url in APPKEY_PREFIX_MAP:
            if stripped.startswith(prefix):
                env = "SIT 测试" if "sit" in prefix else "生产"
                domain = url.split("//")[1]
                hints.append(f"当前 AppKey 对应 {env} 环境 ({domain})，请确认环境是否正确")
                break

    return hints


def print_failure_report(appkey: str, status: int | None, error: str):
    """打印失败诊断报告"""
    print("\n" + "=" * 60)
    print("❌ Token 获取失败")
    print("=" * 60)

    if status:
        print(f"\nHTTP 状态码: {status}")
        if status == 401:
            print("含义: AppKey 无效或未授权")
        elif status == 403:
            print("含义: AppKey 权限不足或已被禁用")
        elif status == 404:
            print("含义: 接口地址不存在，可能 AppKey 前缀对应的环境有误")
        elif status >= 500:
            print("含义: 服务端错误，请稍后重试")

    print(f"\n错误详情: {error}")

    hints = diagnose_appkey(appkey)
    if hints:
        print("\n🔍 排查建议:")
        for i, hint in enumerate(hints, 1):
            print(f"   {i}. {hint}")

    print("\n📋 请逐项确认:")
    print("   □ AppKey 是否从 TicNote 平台完整复制（无遗漏、无多余字符）")
    print("   □ AppKey 前后是否有空格或换行符")
    print(f"   □ AppKey 前缀是否为合法值: {', '.join(VALID_PREFIXES)}")
    print("   □ AppKey 对应的环境（SIT/生产）是否与预期一致")
    print("   □ 该 AppKey 是否已在 TicNote 平台被删除或禁用")
    print("   □ TicNote 账号是否处于正常状态（未被冻结）")
    print("=" * 60)


def get_token(appkey: str) -> dict:
    base_url = resolve_base_url(appkey)
    url = f"{base_url}/api/p1/appkey/login"
    payload = json.dumps({"appkey": appkey}).encode("utf-8")

    print(f"🔗 Base URL: {base_url}")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "base_url": base_url, "data": data}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": body}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"网络连接失败: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="通过 AppKey 获取 TicNote Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey")
    args = parser.parse_args()

    result = get_token(args.appkey)

    if result["success"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_failure_report(
            args.appkey,
            result.get("status"),
            result.get("error", "未知错误"),
        )
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
