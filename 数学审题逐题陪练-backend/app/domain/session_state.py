#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话状态机 —— 15 号文的 S1—S8
================================================================================

【为什么要有这个文件】
  v1 是确定性流程：谁也不能跳步。状态与转移表放在一个地方，
  API、测试、前端都从这里读，不靠“大家记得”。

【12 个状态、8 条守卫】
  CREATED → READING → CONFIRMING → PREPARING → READY
  → ANNOTATING → GRADING_CONDITIONS → PROBING_IMPLICIT → CLOSING → CLOSED
  任意非终态 → DISCARDED；READING/PREPARING 失败 → ERROR（可重试）
"""

# 12 个状态。[源: 15·§4]
状态 = (
    "CREATED", "READING", "CONFIRMING", "PREPARING", "READY",
    "ANNOTATING", "GRADING_CONDITIONS", "PROBING_IMPLICIT",
    "CLOSING", "CLOSED", "DISCARDED", "ERROR",
)

终态 = {"CLOSED", "DISCARDED"}

# 允许的转移。没有列出的转移一律拒绝。
转移 = {
    "CREATED":           {"READING", "DISCARDED"},
    "READING":           {"CONFIRMING", "ERROR", "DISCARDED"},
    "CONFIRMING":        {"PREPARING", "DISCARDED"},
    "PREPARING":         {"READY", "ERROR", "DISCARDED"},
    "READY":             {"ANNOTATING", "DISCARDED"},
    "ANNOTATING":        {"GRADING_CONDITIONS", "DISCARDED"},
    "GRADING_CONDITIONS": {"PROBING_IMPLICIT", "DISCARDED"},
    "PROBING_IMPLICIT":  {"CLOSING", "DISCARDED"},
    "CLOSING":           {"CLOSED", "DISCARDED"},
    "ERROR":             {"READING", "PREPARING", "DISCARDED"},
    "CLOSED":            set(),
    "DISCARDED":         set(),
}

# 步骤 → 当前状态
步骤状态 = {
    "S5": "ANNOTATING",
    "S6": "GRADING_CONDITIONS",
    "S7": "PROBING_IMPLICIT",
}

# 状态 → 步骤（反查）
状态步骤 = {v: k for k, v in 步骤状态.items()}


class 状态错误(Exception):
    def __init__(self, 消息):
        super().__init__(消息)
        self.code = "E_STATE"


def 能转移(当前, 目标):
    return 目标 in 转移.get(当前, set())


def 检查转移(当前, 目标):
    if not 能转移(当前, 目标):
        raise 状态错误("当前状态 %s 不能转到 %s" % (当前, 目标))
    return 目标


def 检查步骤(状态值, 步骤):
    """步骤必须和当前状态匹配，否则 E_STATE。"""
    if 步骤 not in 步骤状态:
        raise 状态错误("步骤只能是 S5/S6/S7")
    if 状态步骤.get(状态值) != 步骤:
        raise 状态错误("当前状态 %s 不在 %s" % (状态值, 步骤))
    return 步骤
