#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可见性投影 / 答案字段剥离
================================================================================

【这是「不给答案」的工程保障，不是文案。】
  内部会话可以含 type/level/note/evidence；学生响应只能拿：
    · 句子原文
    · 当前该做什么（progress.next）
    · 判定结果（一致/不一致/不判定）
    · 聚合后的卡点类型/数量
  绝不返回：type/level/implicit_set/note/target_ref/answer/solution。

  样板 29·§5.3 剥离 `_component/_route`；我们反过来，剥离“答案类字段”。
"""

import re

_答案字段 = {
    "answer", "solution", "final_value", "reference_step",
    "correct_answer", "完整解答", "答案", "解法", "解析",
}

_证据字段 = {"target_ref", "evidence_ref", "note", "confidence", "type", "level"}


def 剥答案(值):
    """递归删除答案类字段；返回新对象。"""
    if isinstance(值, dict):
        return {
            k: 剥答案(v)
            for k, v in 值.items()
            if k not in _答案字段
        }
    if isinstance(值, list):
        return [剥答案(x) for x in 值]
    return 值


def _句(session, i):
    for 分句 in (session.get("prep") or {}).get("分句") or []:
        if 分句.get("i") == i:
            return 分句
    return None


def _条件(session):
    return [
        x for x in (session.get("prep") or {}).get("分句") or []
        if x.get("type") == "条件"
    ]


def _已答(session, 步骤):
    return (session.get("answers") or {}).get(步骤) or {}


def 进度(session):
    """计算学生下一步该做什么；只含 text，不含 type/level。"""
    状态 = session.get("status")
    prep = session.get("prep") or {}
    句 = prep.get("分句") or []

    if 状态 == "ANNOTATING":
        已 = _已答(session, "S5")
        for 分句 in 句:
            i = 分句.get("i")
            if str(i) not in 已:
                return {
                    "step": "S5",
                    "answered": len(已),
                    "total": len(句),
                    "next": {"step": "S5", "target_ref": "sentence:%d" % i,
                             "text": 分句.get("text", "")},
                }
        return {"step": "S5", "answered": len(已), "total": len(句), "next": None}

    if 状态 == "GRADING_CONDITIONS":
        条件 = _条件(session)
        已 = _已答(session, "S6")
        for 分句 in 条件:
            i = 分句.get("i")
            if str(i) not in 已:
                return {
                    "step": "S6",
                    "answered": len(已),
                    "total": len(条件),
                    "next": {"step": "S6", "target_ref": "condition:%d" % i,
                             "text": 分句.get("text", "")},
                }
        return {"step": "S6", "answered": len(已), "total": len(条件), "next": None}

    if 状态 == "PROBING_IMPLICIT":
        次数 = len(_已答(session, "S7"))
        return {
            "step": "S7",
            "answered": 次数,
            "total": 2,
            "next": {"step": "S7", "target_ref": "implicit",
                     "text": "这几句里，有没有藏着一个没说出来的东西？"},
        }

    if 状态 in ("CLOSING", "CLOSED"):
        return {"step": "S8", "answered": 0, "total": 0, "next": None}

    return {"step": None, "answered": 0, "total": 0, "next": None}


def 卡点摘要(session):
    """学生只看到类型 + 次数，不看到具体句子/条件。"""
    统计 = {}
    for 事件 in session.get("checkpoints") or []:
        if 事件.get("visibility") != "student":
            continue
        类 = 事件.get("type")
        if 类:
            统计[类] = 统计.get(类, 0) + 1
    return 统计


def 公开会话(session):
    """学生投影；任何内部字段都不出现。"""
    出 = {
        "session_id": session.get("session_id"),
        "status": session.get("status"),
        "first_experience": session.get("first_experience", True),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "progress": 进度(session),
        "checkpoints": 卡点摘要(session),
    }
    if (session.get("problem") or {}).get("confirmed_text"):
        出["problem"] = {"confirmed_text": session["problem"]["confirmed_text"]}
    if session.get("summary"):
        出["summary"] = 剥答案(session["summary"])
    if session.get("error"):
        出["error"] = {
            "码": session["error"].get("码"),
            "提示": session["error"].get("提示"),
        }
    return 剥答案(出)


def 有答案泄露(文本):
    """极简扫描：面向发布前抽检，不作为唯一保障。"""
    if not isinstance(文本, str):
        return False
    return bool(re.search(r"(答案是|解得|所以\s*[xX]\s*=|完整解答)", 文本))
