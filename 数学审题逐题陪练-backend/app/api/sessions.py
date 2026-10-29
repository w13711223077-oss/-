#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话端点 —— S1—S8 的 HTTP 外壳
================================================================================

  POST /api/v1/sessions                    创建
  POST /api/v1/sessions/{id}/problem       上传题目
  POST /api/v1/sessions/{id}/confirm       确认 + 备课
  POST /api/v1/sessions/{id}/answer        答题
  POST /api/v1/sessions/{id}/close         收束
  GET  /api/v1/sessions/{id}               读状态
  POST /api/v1/sessions/{id}/discard       丢弃

所有业务规则在 engine/flow.py；这里只做 HTTP 映射。
"""

from ..engine import audit, flow

_码到HTTP = {
    "E_NOT_FOUND": 404,
    "E_STATE": 400,
    "E_TEXT_EMPTY": 400,
    "E_LIMIT": 409,
    "E_DEDUP": 409,
    "E_NO_KEY": 503,
    "E_PREP": 502,
    "E_MODEL": 502,
}


def _错误(e):
    return _码到HTTP.get(getattr(e, "code", ""), 500), {
        "错误": str(e),
        "码": getattr(e, "code", "E_UNKNOWN"),
    }


def 创建(_请求体, _查询):
    try:
        s = flow.新建()
        return 201, audit.公开会话(s)
    except Exception as e:  # noqa: BLE001
        return _错误(e)


def 读取(_请求体, _查询, session_id):
    try:
        return 200, flow.公开(session_id)
    except Exception as e:  # noqa: BLE001
        return _错误(e)


def 上传(请求体, _查询, session_id):
    try:
        return 200, flow.上传题目(session_id, 请求体)
    except Exception as e:  # noqa: BLE001
        return _错误(e)


def 确认(请求体, _查询, session_id):
    try:
        return 200, flow.确认题目(session_id, 请求体.get("text") or "")
    except Exception as e:  # noqa: BLE001
        return _错误(e)


def 开始(请求体, _查询, session_id):
    try:
        return 200, flow.开始(session_id)
    except Exception as e:  # noqa: BLE001
        return _错误(e)


def 答题(请求体, _查询, session_id):
    try:
        return 200, flow.答题(session_id, 请求体)
    except Exception as e:  # noqa: BLE001
        return _错误(e)


def 收束(请求体, _查询, session_id):
    try:
        return 200, flow.收束(session_id)
    except Exception as e:  # noqa: BLE001
        return _错误(e)


def 丢弃(请求体, _查询, session_id):
    try:
        return 200, flow.丢弃(session_id)
    except Exception as e:  # noqa: BLE001
        return _错误(e)


# 精确路由：POST /api/v1/sessions
路由 = [
    ("POST", "/api/v1/sessions", 创建),
]

# 动态路由：POST/GET /api/v1/sessions/{id}/...
动态路由 = {
    ("POST", "problem"): 上传,
    ("POST", "confirm"): 确认,
    ("POST", "start"): 开始,
    ("POST", "answer"): 答题,
    ("POST", "close"): 收束,
    ("POST", "discard"): 丢弃,
    ("GET", None): 读取,
}
