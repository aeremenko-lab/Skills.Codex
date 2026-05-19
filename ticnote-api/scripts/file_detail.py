#!/usr/bin/env python3
"""查看文件详情 / 轮询转写状态（GET /api/v2/file-index/file-detail/{recordId}）"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url

# 需要转码的音视频文件类型（MediaFileTypeEnum 中 uploadNeedTranscode=true）
VOICE_TYPES = {"mp3", "wav", "mp4", "mov", "m4a", "caf", "avi", "rmvb", "opus", "aac"}

# 转码/处理终态
TRANSCODE_DONE = {"suc", "fail", "no_rights"}
STATUS_TERMINAL = {2, 3, 4, 5}  # COMPLETED, FAILED, TRANSSUC, SUMMARYSUC


def get_file_detail(base_url: str, token: str, record_id: str) -> dict:
    """GET /api/v2/file-index/file-detail/{recordId}"""
    url = f"{base_url}/api/v2/file-index/file-detail/{record_id}"
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
            body = json.loads(resp.read().decode("utf-8"))
            data = body.get("data", body)
            return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "status": e.code, "error": err_body}
    except Exception as e:
        return {"success": False, "error": str(e)}


def is_processing_done(detail: dict) -> tuple[bool, str]:
    """判断文件处理是否完成。

    Returns:
        (done, reason) — done=True 时处理已结束，reason 描述结果
    """
    status = detail.get("status")
    transcode_status = detail.get("transcodeStatus")
    is_voice = detail.get("isVoice", False)

    # 非音视频文件不需要转码，status 到终态即完成
    if not is_voice:
        if status is not None and status in STATUS_TERMINAL:
            return True, f"处理完成 (status={status})"
        return False, f"处理中 (status={status})"

    # 音视频文件：检查转码状态
    if transcode_status == "fail":
        return True, "转码失败"
    if transcode_status == "no_rights":
        return True, "无权限（需要 VIP）"
    if transcode_status == "suc" and status is not None and status in STATUS_TERMINAL:
        return True, f"转写完成 (status={status}, transcodeStatus={transcode_status})"

    return False, f"处理中 (status={status}, transcodeStatus={transcode_status})"


def poll_file_detail(base_url: str, token: str, record_id: str,
                     interval: int = 5, timeout: int = 600) -> dict:
    """轮询文件详情，等待处理完成。

    Args:
        interval: 轮询间隔（秒），默认 5
        timeout: 最长等待时间（秒），默认 600（10 分钟）
    """
    start_time = time.time()
    attempt = 0

    while True:
        attempt += 1
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print(f"\n⏰ 轮询超时（已等待 {int(elapsed)} 秒）")
            return {"success": False, "error": f"轮询超时: {timeout}s"}

        result = get_file_detail(base_url, token, record_id)
        if not result["success"]:
            print(f"\n❌ 查询失败: {result.get('error')}")
            return result

        detail = result["data"]
        done, reason = is_processing_done(detail)

        status_str = f"[{int(elapsed):>3}s] #{attempt} status={detail.get('status')} " \
                     f"transcodeStatus={detail.get('transcodeStatus')}"

        if done:
            print(f"\n✅ {reason}")
            return result

        print(f"  ⏳ {status_str} — {reason}", end="\r")
        time.sleep(interval)


def print_file_summary(detail: dict):
    """格式化输出文件详情摘要"""
    print(f"\n{'─' * 50}")
    print(f"📄 文件名: {detail.get('fileName') or detail.get('title', '-')}")
    print(f"📊 状态: {detail.get('status')}")
    print(f"🔄 转码状态: {detail.get('transcodeStatus')}")

    if detail.get("isVoice"):
        duration = detail.get("duration")
        if duration:
            m, s = divmod(int(duration), 60)
            print(f"⏱️ 时长: {m}m{s}s")
        print(f"🌐 语言: {detail.get('language', '-')}")

    if detail.get("transcribeJson"):
        t = detail["transcribeJson"]
        preview = t[:200] + "..." if len(t) > 200 else t
        print(f"📝 转写内容: {preview}")

    if detail.get("summaryJson"):
        s = detail["summaryJson"]
        preview = s[:200] + "..." if len(s) > 200 else s
        print(f"📋 总结内容: {preview}")

    print(f"{'─' * 50}")


def main():
    parser = argparse.ArgumentParser(
        description="查看文件详情 / 轮询转写状态"
    )
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey")
    parser.add_argument("--record-id", required=True, help="知识库记录 ID (recordId)")
    parser.add_argument("--poll", action="store_true",
                        help="启用轮询模式，等待处理完成")
    parser.add_argument("--interval", type=int, default=5,
                        help="轮询间隔（秒），默认 5")
    parser.add_argument("--timeout", type=int, default=600,
                        help="轮询超时（秒），默认 600")
    args = parser.parse_args()

    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")
    print(f"🆔 Record ID: {args.record_id}")

    if args.poll:
        print(f"🔄 轮询模式: 间隔 {args.interval}s, 超时 {args.timeout}s\n")
        result = poll_file_detail(
            base_url, args.token, args.record_id,
            interval=args.interval, timeout=args.timeout,
        )
    else:
        result = get_file_detail(base_url, args.token, args.record_id)

    if not result["success"]:
        print(f"\n❌ 失败: {result.get('error')}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    detail = result["data"]
    print_file_summary(detail)

    # 完整输出
    print("\n📦 完整响应:")
    print(json.dumps(detail, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
