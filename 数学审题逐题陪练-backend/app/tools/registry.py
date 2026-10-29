#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具契约 —— TOOL_META + Guard（L1 顺序门 / L2 限次 / L3 去重）
================================================================================

【v1 没有自由 Agent】
  流程由 flow.py 的状态机决定；这里只把「每个工具允许在什么状态调用、
  最多调几次」写成声明，启动时可自检。

【为什么还要 TOOL_META】
  以后加工具/加角色时，不需要在 API 里散落 if；只改这张表。
  样板 29 号文的“工具即键 + 双向断言”在这里降级成最小可用版。
"""

# 工具 → 允许的状态 + 每次会话的调用上限
# [源: 17·§4.1]
TOOL_META = {
    "read_problem": {
        "personas": ["student"],
        "allowed_status": {"CREATED", "CONFIRMING", "ERROR"},
        "call_limit": 3,
    },
    "prep_problem": {
        "personas": ["student"],
        "allowed_status": {"CONFIRMING", "ERROR"},
        "call_limit": 1,
    },
    "judge_answer": {
        "personas": ["student"],
        "allowed_status": {"ANNOTATING", "GRADING_CONDITIONS", "PROBING_IMPLICIT"},
        "call_limit": None,
    },
    "probe_implicit": {
        "personas": ["student"],
        "allowed_status": {"PROBING_IMPLICIT"},
        "call_limit": 2,
    },
    "close_session": {
        "personas": ["student"],
        "allowed_status": {"CLOSING"},
        "call_limit": 1,
    },
    "save_record": {
        "personas": ["student"],
        "allowed_status": {"CLOSED"},
        "call_limit": 1,
    },
}


class 工具错误(Exception):
    def __init__(self, code, 消息):
        super().__init__(消息)
        self.code = code


def 检查(工具, 会话):
    """L1 顺序门：工具只能在允许的状态调用。"""
    元 = TOOL_META.get(工具)
    if 元 is None:
        raise 工具错误("E_STATE", "没有注册的工具：%s" % 工具)
    状态 = 会话.get("status")
    if 状态 not in 元["allowed_status"]:
        raise 工具错误(
            "E_STATE",
            "工具 %s 不能在状态 %s 调用（允许：%s）"
            % (工具, 状态, "/".join(sorted(元["allowed_status"]))),
        )
    return True


def 自检():
    """启动时双向断言：表里的工具有实现、实现有元数据。"""
    # v1 的工具实现分散在 flow/prep/judge；这里只断言表非空且状态合法。
    from ..domain import session_state
    for 名, 元 in TOOL_META.items():
        for 状态 in 元["allowed_status"]:
            if 状态 not in session_state.状态:
                raise AssertionError("工具 %s 引用了未知状态 %s" % (名, 状态))
    return True
