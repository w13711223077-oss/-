#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容端点 —— POST /api/v1/prep、POST /api/v1/judge
================================================================================

新架构把业务放在 engine/prep.py 与 engine/judge.py；这两个端点保留给：
  · P0 脚本 / 测试直接打；
  · 前端/脚本只想拿单次备课或单次判定，不想建会话。

**它们不持有会话状态**；S1—S8 的完整流程走 /api/v1/sessions。
"""

from ..domain import schema
from ..engine import judge
from ..engine import prep as prep_engine

_码到HTTP = {
    "E_TEXT_EMPTY": 400,
    "E_NO_KEY": 503,
    "E_PREP": 502,
    "E_MODEL": 502,
}


def 备课(请求体, _查询):
    """
    入参：{"题目原文": "..."}（兼容 {"text": "..."}）
    出参：{"备课": {...}, "桩": bool}
    """
    题目 = (请求体.get("题目原文") or 请求体.get("text") or "").strip()
    try:
        结果 = prep_engine.prepare(题目)
    except prep_engine.备课错误 as e:
        return _码到HTTP.get(e.code, 500), {"错误": str(e), "码": e.code}
    return 200, 结果


def 判定(请求体, _查询):
    """
    入参：{"备课解剖": {...}, "学生输入": "...", "步骤": "S5|S6|S7"}
    出参：{"结果": "一致|不一致|不判定", "依据": "...", "来源": "..."}
    """
    步骤 = (请求体.get("步骤") or "").strip()
    if 步骤 not in ("S5", "S6", "S7"):
        return 400, {"错误": "步骤只能是 S5/S6/S7", "码": "E_STATE"}

    解剖 = 请求体.get("备课解剖")
    if not isinstance(解剖, dict):
        return 400, {"错误": "缺少 备课解剖（对象）", "码": "E_STATE"}

    错 = schema.校验("备课解剖", 解剖)
    for n, 分句 in enumerate(解剖.get("分句") or []):
        错 += schema.校验("分句", 分句, "$.分句[%d]" % n)
    if 错:
        return 422, {"错误": "备课解剖不合契约", "码": "E_CONTRACT", "明细": 错}

    if "学生输入" not in 请求体:
        return 400, {"错误": "缺少 学生输入", "码": "E_STATE"}

    return 200, judge.判(解剖, 请求体.get("学生输入"), 步骤)


# 测试/兼容用：保留旧名字
_解析备课 = prep_engine.解析备课
_桩备课 = prep_engine.桩备课

路由 = [
    ("POST", "/api/v1/prep", 备课),
    ("POST", "/api/v1/judge", 判定),
]
