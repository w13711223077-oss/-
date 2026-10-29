#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端点组① —— 转发模型调用（把 key 藏在服务端）
================================================================================

【这一组只干一件事：让 key 不出现在网页源码里。】

§8.1 技术边界第二条摆着：「API 密钥会暴露在网页源码里 → 不能公开分发」。
v1 的 index.html 是直连 DeepSeek 的，key 就写在页面里。
选 A（加极薄存储层）之后，顺带把这条也解决了——因为已经有一个服务端了。

【薄到什么程度】
  不引入任何框架。就是一个 urllib 转发 + 两条提示词。
  key 只从服务端环境变量读，永远不进响应体。

两个入口：
  POST /api/v1/model/read      读图抄题（F1）。这是流程的第一步，最常用。
  POST /api/v1/model/forward   通用转发（F2 备课 / F3 判定 / F10 批改 之后都走它）

依赖：只用 Python 标准库。
"""

import json
import os
import urllib.error
import urllib.request

# ─────────────────────────────────────────────────────────────
# 配置：key 只在这里读，只在出站请求里用
# ─────────────────────────────────────────────────────────────

def _key():
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def _桩模式():
    """
    桩模式：不调模型，返回一份假转录。
    照 p0_judge.py 的 --baseline 一个道理——先证明管道通，再去花真钱。
    开法：环境变量 PEILIAN_STUB=1
    """
    return os.environ.get("PEILIAN_STUB", "").strip() in ("1", "true", "yes")


def _base_url():
    return os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")


def _model():
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")


# ─────────────────────────────────────────────────────────────
# 提示词
# ─────────────────────────────────────────────────────────────
# 口径和 v1/index.html 里那段读图的提示词保持一致：
#   · 只让它「抄题」，不让它「解题」——抄写是转录，解题越界了（§5·9.4）
#   · 印刷不清的地方照抄，不要猜——猜出来的题目比读不出来更危险

读图提示词 = (
    "把这张图片里的数学题目逐字抄写出来，保持原有的标点、数字、单位。\n"
    "只抄题目本身，不要解答、不要解释、不要加任何自己的话。\n"
    "如果图片里有印刷不清楚的地方，照抄你看到的样子，不要猜。"
)

# 【产品铁律】——不管调用方要什么，这几条都必须排在前面。
# §6·决策 8 说这条口径「**要写死在提示词里**」，理由写得很直白：
#   「AI 乐于助人」的默认行为**正好和它相反**——模型天然想说得更具体。
# 所以它不是「建议」，是每次转发都要带上的前置约束。
铁律提示词 = (
    "你在一个面向初中生的「审题陪练」产品里工作。这个产品有一条不能越过的线。\n"
    "\n"
    "1. 不给答案、不给解法、不写解题过程。解题是学生自己的事。\n"
    "2. 批改时【只给数量级定位，不点名】：\n"
    "     ✅「这道题你有三个条件没用上」「有一级判断反了」「少用了一个数」\n"
    "     ❌「你漏的是『最后一辆车只坐 15 人』」——这样等于换个方式把答案给了出去。\n"
    "   让他自己回头把那几个条件找出来；找的过程，就是这个产品要练的东西。\n"
    "3. 没把握就说不确定，不要为了显得聪明而硬判。判错一个正确的东西，代价比不判大得多。\n"
)


# ─────────────────────────────────────────────────────────────
# 出站调用
# ─────────────────────────────────────────────────────────────

def _调模型(messages, temperature=0, 超时=120):
    body = json.dumps({
        "model": _model(),
        "temperature": temperature,
        "messages": messages,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        _base_url() + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + _key(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=超时) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        细节 = e.read().decode("utf-8", "replace")[:200]
        raise RuntimeError("模型返回 HTTP %s：%s" % (e.code, 细节))
    except urllib.error.URLError as e:
        raise RuntimeError("连不上模型：%s" % e.reason)

    return (payload.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()


# ─────────────────────────────────────────────────────────────
# POST /api/v1/model/read  —— F1 拍照识题
# ─────────────────────────────────────────────────────────────

_桩转录 = (
    "（桩模式）七年七班计划组织学生去植物园研学。若每辆车坐 45 人，"
    "则有 10 人没有座位；若每辆车坐 50 人，则最后一辆车只坐了 15 人。"
    "问：一共有多少名学生？计划租多少辆车？（列方程解答，写出必要过程。）"
)


def 读题(请求体, _查询):
    """
    入参（二选一）：
      {"image_data_url": "data:image/...;base64,...", "mode": "image"}
      {"text": "题目原文…", "mode": "text"}      ← F13 兜底输入，不用调模型
    出参：
      {"text": "抄写出来的题目", "mode": "...", "桩": bool}
    """
    模式 = (请求体.get("mode") or ("image" if 请求体.get("image_data_url") else "text")).strip()
    图片 = 请求体.get("image_data_url")
    文本 = (请求体.get("text") or "").strip()

    # F13 兜底：学生直接打字/粘贴，没有图可读，直接原样返回
    if 模式 == "text" or (not 图片 and 文本):
        if not 文本:
            return 400, {"错误": "既没给图片，也没给文本"}
        return 200, {"text": 文本, "mode": "text", "桩": False, "说明": "F13 兜底输入，不经模型"}

    if not 图片:
        return 400, {"错误": "缺少 image_data_url"}

    if _桩模式():
        return 200, {"text": _桩转录, "mode": "image", "桩": True}

    if not _key():
        return 503, {"错误": "服务端没有 DEEPSEEK_API_KEY",
                     "提示": "设好环境变量再启动；或先开 PEILIAN_STUB=1 跑桩模式验证管道"}

    try:
        文本 = _调模型([{
            "role": "user",
            "content": [
                {"type": "text", "text": 读图提示词},
                {"type": "image_url", "image_url": {"url": 图片, "detail": "original"}},
            ],
        }])
    except RuntimeError as e:
        return 502, {"错误": str(e)}

    return 200, {"text": 文本, "mode": "image", "桩": False}


# ─────────────────────────────────────────────────────────────
# POST /api/v1/model/forward  —— 通用转发
# ─────────────────────────────────────────────────────────────

def 转发(请求体, _查询):
    """
    入参：
      {"messages": [{role, content}...], "temperature": 0, "system": "可选"}
    出参：
      {"text": "模型回的正文"}

    这是给 F2 备课 / F3 判定 / F10 批改 之后复用的口子。
    现在只保证「能转发、能藏 key」，具体口径由调用方在 system 里写。

    注意：调用方给的 system **追加**在铁律后面，**替换不了**铁律。
    产品的那条线不外包给调用方。
    """
    messages = 请求体.get("messages")
    if not isinstance(messages, list) or not messages:
        return 400, {"错误": "messages 必须是非空数组"}

    前置 = [{"role": "system", "content": 铁律提示词}]
    系统 = (请求体.get("system") or "").strip()
    if 系统:
        前置.append({"role": "system", "content": 系统})
    messages = 前置 + messages

    if _桩模式():
        return 200, {"text": "（桩模式）这里本该是模型的回答。", "桩": True}

    if not _key():
        return 503, {"错误": "服务端没有 DEEPSEEK_API_KEY"}

    try:
        文本 = _调模型(messages, temperature=请求体.get("temperature", 0))
    except RuntimeError as e:
        return 502, {"错误": str(e)}

    return 200, {"text": 文本, "桩": False}


# ─────────────────────────────────────────────────────────────
# 路由表（main.py 读它）
# ─────────────────────────────────────────────────────────────
路由 = [
    ("POST", "/api/v1/model/read", 读题),
    ("POST", "/api/v1/model/forward", 转发),
]
