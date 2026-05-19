#!/usr/bin/env python3
"""Deep Research（POST /api/v1/deep/research/query）

参数说明：
  sessionId   — 从 file-detail 接口返回的 dprSessionId（文件创建时自动生成）
  sessionType — ChatTypeEnum 枚举值：
                  6 = FILE_DP_RESEARCH（音频文件 Deep Research）
                  9 = LOCAL_FILE_RESEARCH（非音频文件 Deep Research）
                  5 = DEEP_RESEARCH_REPORT（项目级 Deep Research）
  question    — 用户输入的研究问题
  msgId       — 消息 ID，后端会用 System.currentTimeMillis() 覆盖，传任意值即可
  outline     — 研究大纲，可选
  source      — 来源标识，后端不校验，仅用于统计追踪
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import resolve_base_url


# ChatTypeEnum 常用值
SESSION_TYPE_DEEP_RESEARCH_REPORT = 5   # 项目级 Deep Research
SESSION_TYPE_FILE_DP_RESEARCH = 6       # 音频文件 Deep Research
SESSION_TYPE_LOCAL_FILE_RESEARCH = 9    # 非音频文件 Deep Research


def deep_research(base_url: str, token: str, question: str,
                  session_id: str, session_type: int,
                  msg_id: int = None,
                  outline: str = "", source: int = 3) -> dict:
    """POST /api/v1/deep/research/query

    Args:
        base_url:     API base URL
        token:        Bearer Token
        question:     研究问题
        session_id:   会话 ID（file-detail 返回的 dprSessionId）
        session_type: 会话类型（6=音频, 9=非音频, 5=项目级）
        msg_id:       消息 ID（可选，后端会用当前时间戳覆盖）
        outline:      研究大纲（可选）
        source:       来源标识（可选，默认 3）
    """
    url = f"{base_url}/api/v1/deep/research/query"
    payload = {
        "sessionId": str(session_id),
        "sessionType": session_type,
        "question": question,
        "msgId": msg_id if msg_id is not None else int(time.time() * 1000),
        "source": source,
    }
    if outline:
        payload["outline"] = outline

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


def get_session_id_from_detail(base_url: str, token: str, record_id: str) -> dict:
    """从 file-detail 接口获取 dprSessionId 和文件类型信息。

    Returns:
        {"dprSessionId": "...", "isVoice": bool, "sessionType": int}
    """
    # 复用 file_detail 脚本
    from file_detail import get_file_detail
    r = get_file_detail(base_url, token, record_id)
    if not r["success"]:
        return r

    detail = r["data"]
    dpr_session_id = detail.get("dprSessionId")
    if not dpr_session_id:
        return {"success": False, "error": f"文件 {record_id} 没有 dprSessionId，可能尚未初始化"}

    is_voice = detail.get("isVoice", False)
    session_type = SESSION_TYPE_FILE_DP_RESEARCH if is_voice else SESSION_TYPE_LOCAL_FILE_RESEARCH

    return {
        "success": True,
        "dprSessionId": str(dpr_session_id),
        "isVoice": is_voice,
        "sessionType": session_type,
        "detail": detail,
    }


def main():
    parser = argparse.ArgumentParser(description="Deep Research")
    parser.add_argument("--token", required=True, help="Bearer Token")
    parser.add_argument("--appkey", required=True, help="TicNote AppKey")
    parser.add_argument("--question", required=True, help="研究问题")

    # 方式一：直接传 sessionId + sessionType
    parser.add_argument("--session-id", default=None,
                        help="会话 ID（file-detail 返回的 dprSessionId）")
    parser.add_argument("--session-type", type=int, default=None,
                        help="会话类型（6=音频, 9=非音频, 5=项目级）")

    # 方式二：传 recordId，自动从 file-detail 获取
    parser.add_argument("--record-id", default=None,
                        help="文件 recordId（自动获取 dprSessionId 和 sessionType）")

    parser.add_argument("--msg-id", type=int, default=None, help="消息 ID（可选）")
    parser.add_argument("--outline", default="", help="研究大纲（可选）")
    parser.add_argument("--source", type=int, default=3, help="来源标识（默认 3）")
    args = parser.parse_args()

    base_url = resolve_base_url(args.appkey)
    print(f"🔗 Base URL: {base_url}")

    # 确定 sessionId 和 sessionType
    session_id = args.session_id
    session_type = args.session_type

    if session_id and session_type is not None:
        print(f"🆔 Session ID: {session_id}")
        print(f"📋 Session Type: {session_type}")
    elif args.record_id:
        print(f"🆔 Record ID: {args.record_id}")
        print(f"📡 从 file-detail 获取 dprSessionId...")
        info = get_session_id_from_detail(base_url, args.token, args.record_id)
        if not info["success"]:
            print(f"❌ 获取失败: {info.get('error')}")
            sys.exit(1)
        session_id = info["dprSessionId"]
        session_type = info["sessionType"]
        print(f"✅ dprSessionId: {session_id}")
        print(f"✅ sessionType: {session_type} ({'音频' if info['isVoice'] else '非音频'})")
    else:
        print("❌ 请提供 --session-id + --session-type，或 --record-id")
        sys.exit(1)

    print(f"❓ Question: {args.question}")

    result = deep_research(
        base_url, args.token, args.question,
        session_id=session_id, session_type=session_type,
        msg_id=args.msg_id, outline=args.outline, source=args.source,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
