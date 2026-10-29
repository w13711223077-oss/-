#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
确定性流程编排 + 顺序门 —— S1—S8 的“谁能在什么时候做什么”
================================================================================

【为什么不是自由 Agent】
  15·§9·决策 6：单流程产品要可复现。流程由这里的状态机决定；
  LLM 只在 prep/judge 内部工作，不决定下一步。

【职责】
  create / attach_problem / confirm / answer / close / discard
  每一步先过 registry 的顺序门，再改会话，再落盘。
"""

import hashlib
import uuid
from datetime import datetime
from ..api import forward
from ..domain import session_state
from ..store import session_store
from ..tools import registry
from . import audit, judge, prep


class 流程错误(Exception):
    def __init__(self, code, 消息):
        super().__init__(消息)
        self.code = code


def _现在():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _新ID(前缀):
    return "%s-%s" % (前缀, uuid.uuid4().hex[:12])


def _存(s):
    s["updated_at"] = _现在()
    session_store.存(s)
    return s


def _取(session_id):
    s = session_store.读(session_id)
    if not s:
        raise 流程错误("E_NOT_FOUND", "会话不存在：%s" % session_id)
    return s


def _转(s, 目标):
    session_state.检查转移(s.get("status"), 目标)
    s["status"] = 目标


def _检查工具(工具, s):
    try:
        registry.检查(工具, s)
    except registry.工具错误 as e:
        raise 流程错误(e.code, str(e))


def 新建():
    s = {
        "session_id": _新ID("S"),
        "status": "CREATED",
        "first_experience": True,
        "created_at": _现在(),
        "updated_at": _现在(),
        "problem": {},
        "prep": {},
        "answers": {"S5": {}, "S6": {}, "S7": []},
        "checkpoints": [],
        "stuck": [],
        "summary": {},
        "error": None,
    }
    return _存(s)


def 公开(session_id):
    return audit.公开会话(_取(session_id))


def 上传题目(session_id, 请求体):
    s = _取(session_id)
    _检查工具("read_problem", s)

    模式 = (请求体.get("mode") or ("image" if 请求体.get("image_data_url") else "text")).strip()
    正文 = {"mode": 模式}
    if 模式 == "image":
        正文["image_data_url"] = 请求体.get("image_data_url")
    else:
        正文["text"] = 请求体.get("text")

    if s["status"] == "ERROR":
        _转(s, "READING")
    elif s["status"] == "CREATED":
        _转(s, "READING")
    # CONFIRMING：允许重新拍/重新粘贴，状态不变

    状态, 数据 = forward.读题(正文, {})
    if 状态 != 200:
        s["status"] = "ERROR"
        s["error"] = {"码": 数据.get("错误", "E_MODEL"), "提示": 数据.get("提示") or 数据.get("错误")}
        _存(s)
        raise 流程错误("E_MODEL", 数据.get("错误") or "读题失败")

    if s["status"] != "CONFIRMING":
        _转(s, "CONFIRMING")
    s["problem"] = {
        "problem_id": _新ID("P"),
        "source_type": 模式,
        "raw_text": 数据.get("text") or "",
        "confirmed_text": "",
        "text_hash": "",
        "image_ref": None,
    }
    s["error"] = None
    _存(s)
    return {"session": audit.公开会话(s), "text": 数据.get("text") or "",
            "mode": 数据.get("mode"), "桩": bool(数据.get("桩"))}


def 确认题目(session_id, 文本):
    s = _取(session_id)
    _检查工具("prep_problem", s)
    文本 = (文本 or "").strip()
    if not 文本:
        raise 流程错误("E_TEXT_EMPTY", "题目不能是空的")

    if s["status"] == "ERROR":
        _转(s, "PREPARING")
    else:
        _转(s, "PREPARING")

    try:
        结果 = prep.prepare(文本)
    except prep.备课错误 as e:
        s["status"] = "ERROR"
        s["error"] = {"码": e.code, "提示": str(e)}
        _存(s)
        raise 流程错误(e.code, str(e))

    解剖 = 结果["备课"]
    解剖.update({
        "prep_id": _新ID("PR"),
        "problem_id": s["problem"].get("problem_id"),
        "version": 1,
        "locked": True,
        "prompt_version": "f2-v1",
        "model": "deepseek-flash" if not 结果["桩"] else "stub",
    })
    s["prep"] = 解剖
    s["problem"]["confirmed_text"] = 文本
    s["problem"]["text_hash"] = hashlib.sha256(文本.encode("utf-8")).hexdigest()[:16]
    _转(s, "READY")
    s["error"] = None
    _存(s)
    return {"session": audit.公开会话(s), "桩": 结果["桩"]}


def 开始(session_id):
    """S4 开场完成 → S5。"""
    s = _取(session_id)
    _转(s, "ANNOTATING")
    _存(s)
    return {"session": audit.公开会话(s)}


def _分句(s, i):
    for x in (s.get("prep") or {}).get("分句") or []:
        if x.get("i") == i:
            return x
    return None


def _条件(s):
    return [x for x in (s.get("prep") or {}).get("分句") or [] if x.get("type") == "条件"]


def _解析目标(s, 步骤, target_ref):
    target_ref = (target_ref or "").strip()
    if 步骤 == "S5":
        if not target_ref.startswith("sentence:"):
            raise 流程错误("E_STATE", "S5 的目标应为 sentence:<i>")
        try:
            i = int(target_ref.split(":", 1)[1])
        except ValueError:
            raise 流程错误("E_STATE", "目标编号不是整数")
        if not _分句(s, i):
            raise 流程错误("E_STATE", "没有第 %d 句" % i)
        return i
    if 步骤 == "S6":
        if not target_ref.startswith("condition:"):
            raise 流程错误("E_STATE", "S6 的目标应为 condition:<i>")
        try:
            i = int(target_ref.split(":", 1)[1])
        except ValueError:
            raise 流程错误("E_STATE", "目标编号不是整数")
        if not any(x.get("i") == i for x in _条件(s)):
            raise 流程错误("E_STATE", "第 %d 句不是条件句" % i)
        return i
    if 步骤 == "S7":
        if target_ref != "implicit":
            raise 流程错误("E_STATE", "S7 的目标应为 implicit")
        return "implicit"
    raise 流程错误("E_STATE", "步骤只能是 S5/S6/S7")


def _卡点(s, 步骤, 类型, 结果, 子类=None, 目标=None):
    s["checkpoints"].append({
        "event_id": _新ID("CK"),
        "session_id": s["session_id"],
        "step": 步骤,
        "type": 类型,
        "subtype": 子类,
        "result": 结果,
        "target_ref": 目标,
        "exposure": len((s.get("answers") or {}).get(步骤) or []),
        "attempt": len((s.get("answers") or {}).get(步骤) or []),
        "visibility": "student",   # 学生只看到聚合；证据不公开
        "rule_version": "v1",
        "model": (s.get("prep") or {}).get("model"),
        "created_at": _现在(),
    })


def 答题(session_id, 请求体):
    s = _取(session_id)
    _检查工具("judge_answer", s)

    步骤 = (请求体.get("step") or "").strip()
    session_state.检查步骤(s.get("status"), 步骤)
    目标 = _解析目标(s, 步骤, 请求体.get("target_ref"))
    can_not_say = bool(请求体.get("can_not_say"))
    卡住 = bool(请求体.get("stuck"))
    输入 = "" if 卡住 else (请求体.get("input") or "")
    if not 输入 and not can_not_say and not 卡住:
        raise 流程错误("E_TEXT_EMPTY", "这一句还没有回答")

    if 步骤 in ("S5", "S6"):
        已 = s["answers"][步骤]
        键 = str(目标)
        if 键 in 已:
            raise 流程错误("E_LIMIT", "这一句已经答过了")
        结果 = judge.判(s["prep"], 输入, 步骤) if not 卡住 else {
            "结果": "不判定", "依据": "40 秒没动，先记下来。", "来源": "超时",
        }
        已[键] = {"input": 输入, "verdict": 结果, "at": _现在(), "stuck": 卡住}
        if 卡住:
            s["stuck"].append({"step": 步骤, "target": 请求体.get("target_ref"), "at": _现在()})
        if 结果.get("结果") == "不一致" and judge.P0_已通过:
            _卡点(s, 步骤, "标注错" if 步骤 == "S5" else "定级错",
                  "fail", 目标=请求体.get("target_ref"))

        if 步骤 == "S5":
            if all(str(x.get("i")) in 已 for x in (s["prep"].get("分句") or [])):
                if _条件(s):
                    _转(s, "GRADING_CONDITIONS")
                else:
                    _转(s, "PROBING_IMPLICIT")
        else:
            if all(str(x.get("i")) in 已 for x in _条件(s)):
                _转(s, "PROBING_IMPLICIT")
    else:
        尝试 = s["answers"]["S7"]
        if len(尝试) >= 2:
            raise 流程错误("E_LIMIT", "S7 只追问一次")
        结果 = judge.判(s["prep"], 输入, "S7") if not can_not_say else {
            "结果": "不判定", "依据": "学生说「我说不出来」。", "来源": "自述",
        }
        尝试.append({"input": 输入, "can_not_say": can_not_say, "verdict": 结果, "at": _现在()})
        if can_not_say:
            s["stuck"].append({"step": "S7", "target": "implicit", "at": _现在()})

        if judge.P0_已通过:
            if len(尝试) == 1 and 结果.get("结果") != "一致":
                pass  # 允许一次追问
            elif 结果.get("结果") == "一致":
                if len(尝试) == 2:
                    _卡点(s, "S7", "隐含条件未说出", "pass", "推一把过了", "implicit")
            else:
                _卡点(s, "S7", "隐含条件未说出", "fail", "推一把也没过", "implicit")

        if can_not_say or len(尝试) >= 2 or 结果.get("结果") == "一致":
            _转(s, "CLOSING")

    _存(s)
    return {"verdict": 结果, "session": audit.公开会话(s)}


def 收束(session_id):
    s = _取(session_id)
    _检查工具("close_session", s)

    句数 = len((s.get("prep") or {}).get("分句") or [])
    标数 = len(s["answers"].get("S5") or {})
    级数 = len(s["answers"].get("S6") or {})
    想过 = bool(s["answers"].get("S7"))

    做了 = []
    if 句数:
        做了.append("你一句一句看了 %d 句" % 句数)
    if 标数:
        做了.append("亲手标了 %d 句" % 标数)
    if 级数:
        做了.append("给 %d 条条件定了级" % 级数)
    if 想过:
        做了.append("也想过藏起来的那句话")

    开始 = s.get("created_at")
    秒 = 0
    try:
        开始t = datetime.fromisoformat(开始)
        秒 = max(0, int((datetime.now().astimezone() - 开始t).total_seconds()))
    except (TypeError, ValueError):
        pass

    说明 = "首体验到这里结束。写解答、批改和变式题是下一次的事。"
    if not judge.P0_已通过:
        说明 += " 这次判定还没上线，所以我只提问、没有判对错；这次也没有写入卡点库。"

    s["summary"] = {
        "headline": "这道题你已经读明白了。",
        "did": 做了,
        "note": 说明,
        "duration_seconds": 秒,
    }
    _转(s, "CLOSED")
    _存(s)
    return {"session": audit.公开会话(s)}


def 丢弃(session_id):
    s = _取(session_id)
    if s.get("status") in session_state.终态:
        return {"session": audit.公开会话(s)}
    _转(s, "DISCARDED")
    _存(s)
    return {"session": audit.公开会话(s)}
