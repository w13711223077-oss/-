#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F2 备课引擎 —— 把题目解剖成 S5/S6/S7 的判定基准
================================================================================

【为什么独立成 engine，而不是留在 api】
  F2 是唯一真源：S5/S6/S7、v2 批改都消费同一份。
  它不应该绑定 HTTP；API 只是它的一个调用方。

【输出】
  题目原文 / 分句（i,text,type,level,confidence,note）/
  隐含条件集合（集合，不是单点）/ 不确定项（必须能输出“不知道”）
"""

import json
import re

from ..api import forward
from ..domain import schema


class 备课错误(Exception):
    """带业务码的备课失败；API 层负责映射 HTTP 状态。"""
    def __init__(self, code, 消息):
        super().__init__(消息)
        self.code = code


_备课提示词 = (
    "你是「数学审题逐题陪练」的 F2 备课模块。你的任务是把一道七年级应用题解剖成 JSON，"
    "供后续逐句标注（S5）、条件定级（S6）、隐含条件追问（S7）使用。\n"
    "只输出一个 JSON 对象，不要 markdown、不要解释、不要解题。\n"
    "\n"
    "JSON 结构：\n"
    "{\n"
    '  "题目原文": "学生确认过的题目文本",\n'
    '  "分句": [\n'
    '    {"i": 0, "text": "句子原话", "type": "背景|条件|问题|指令", '
    '"level": "直接|间接|隐含", "confidence": "高|中|低", "note": "判断依据"}\n'
    "  ],\n"
    '  "隐含条件集合": ["题目里没说、但必须成立的条件"],\n'
    '  "不确定项": ["没把握的项"]\n'
    "}\n"
    "\n"
    "规则：\n"
    "1. 分句按句号、问号、分号切，4—6 句为宜；每句都要原样保留。\n"
    "2. level 只给「条件」句；非条件句不要出现 level 字段。\n"
    "3. 隐含条件写成集合，允许有多个说法。\n"
    "4. 任何一项没把握，confidence 写「低」，并把这一项写进 不确定项。\n"
    "5. 不要给答案、不要给解法、不要写解题过程。\n"
)


def 切句(文本):
    """按句末标点切句；切不出来就把整段当一句。"""
    句 = [x.strip() for x in re.split(r"(?<=[。！？；])", 文本) if x.strip()]
    return 句 or [文本.strip()]


def 桩备课(题目):
    """
    桩模式：只做分句 + 很粗的启发式分类，**不参与判定**。
    所有 confidence 写「低」，F3 会走「不判定」；这些 type/level 只是占位。
    """
    分句 = []
    for i, 句 in enumerate(切句(题目)):
        if re.search(r"(多少|几|问)", 句):
            类 = "问题"
        elif re.search(r"(解答|求出|写出|列方程|计算)", 句):
            类 = "指令"
        elif re.search(r"\d", 句):
            类 = "条件"
        else:
            类 = "背景"

        项 = {
            "i": i,
            "text": 句,
            "type": 类,
            "confidence": "低",
            "note": "桩模式：只做分句和启发式分类，不参与判定",
        }
        if 类 == "条件":
            项["level"] = "直接"
            项["note"] += "；级别是占位，不参与判定"
        分句.append(项)

    return {
        "题目原文": 题目,
        "分句": 分句,
        "隐含条件集合": [],
        "不确定项": ["桩模式：类型 / 级别 / 隐含条件均未判定"],
    }


def 剥代码围栏(文本):
    文本 = (文本 or "").strip()
    if 文本.startswith("```"):
        文本 = re.sub(r"^```[a-zA-Z]*\s*", "", 文本)
        if 文本.endswith("```"):
            文本 = 文本[:-3]
    return 文本.strip()


def 解析备课(原文, 题目):
    """
    返回解剖对象；解析/校验失败返回错误字符串。
    失败时不猜、不补——备课错一次，后面全错（§3.2·S3）。
    """
    文本 = 剥代码围栏(原文)
    起 = 文本.find("{")
    止 = 文本.rfind("}")
    if 起 < 0 or 止 < 起:
        return "模型没有返回 JSON 对象"
    try:
        解剖 = json.loads(文本[起:止 + 1])
    except json.JSONDecodeError as e:
        return "JSON 解析失败：%s" % e
    if not isinstance(解剖, dict):
        return "模型返回的不是 JSON 对象"

    解剖.setdefault("题目原文", 题目)
    错 = schema.校验("备课解剖", 解剖)
    for n, 分句 in enumerate(解剖.get("分句") or []):
        错 += schema.校验("分句", 分句, "$.分句[%d]" % n)
    if 错:
        return "备课输出不合契约：" + "；".join(错)
    return 解剖


def prepare(题目):
    """
    返回 {"备课": 解剖, "桩": bool}；失败抛 备课错误。
    """
    题目 = (题目 or "").strip()
    if not 题目:
        raise 备课错误("E_TEXT_EMPTY", "缺少题目原文")

    if forward._桩模式():
        return {
            "备课": 桩备课(题目),
            "桩": True,
            "说明": "桩模式：只做分句和启发式分类；F3 仍返回「不判定」。",
        }

    if not forward._key():
        raise 备课错误(
            "E_NO_KEY",
            "服务端没有 DEEPSEEK_API_KEY；设好环境变量，或先开 PEILIAN_STUB=1 跑桩模式",
        )

    try:
        原文 = forward._调模型([
            {"role": "system", "content": forward.铁律提示词 + "\n\n" + _备课提示词},
            {"role": "user", "content": "题目原文：\n" + 题目},
        ], temperature=0)
    except RuntimeError as e:
        raise 备课错误("E_MODEL", str(e))

    解剖 = 解析备课(原文, 题目)
    if isinstance(解剖, str):
        raise 备课错误("E_PREP", 解剖 + "；原文：" + 原文[:300])
    return {"备课": 解剖, "桩": False}
