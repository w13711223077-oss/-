#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存储层 —— 追加式 JSONL
================================================================================

【为什么是「追加」而不是「改」】
  这个项目里，记录的唯一价值是「维度长期稳定」（§6·决策 4）。
  追加不改写，等于每一次写入都留痕；改了也看得出改过。
  顺带一个好处：追加式不需要数据库，一个文件就能跑，符合 v1 的「极薄」。

【三个股，对应文档里的三个说法】
  exercises.jsonl   每次练习一条   —— 含「本次是否一次通过」（§3.2·S12 续：所有人都记）
  beads.jsonl       卡点记录库     —— 四类卡点，每条一笔（§3.2·S12）
  wrong_items.jsonl 错题库         —— 做错的原题 ＋ 变式题（§3.2·S12）

  文档说 S12「往两个库各写一笔」；练习记录是承载它们的外壳，
  所以接口只暴露「写一次练习」，由这里拆成三股。

依赖：只用 Python 标准库。
"""

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

# 数据落在哪：默认 backend/data/，可以用环境变量挪走
_默认数据目录 = Path(__file__).resolve().parents[2] / "data"


def _数据目录():
    p = Path(os.environ.get("PEILIAN_DATA_DIR") or _默认数据目录)
    p.mkdir(parents=True, exist_ok=True)
    return p


练习库 = "exercises.jsonl"
卡点库 = "beads.jsonl"
错题库 = "wrong_items.jsonl"

_写锁 = threading.Lock()      # http.server 是多线程的，追加要串行


# ─────────────────────────────────────────────────────────────
# 底层：追加 / 读回
# ─────────────────────────────────────────────────────────────

def 追加(文件名, 记录):
    行 = json.dumps(记录, ensure_ascii=False)
    with _写锁:
        with open(_数据目录() / 文件名, "a", encoding="utf-8") as f:
            f.write(行 + "\n")
    return 记录


def 读全部(文件名):
    """坏行跳过（半个写坏的 JSON 不该让整个库读不出来）。"""
    p = _数据目录() / 文件名
    if not p.exists():
        return []
    出 = []
    for 行 in p.read_text(encoding="utf-8").splitlines():
        行 = 行.strip()
        if not 行:
            continue
        try:
            出.append(json.loads(行))
        except json.JSONDecodeError:
            continue
    return 出


def 新ID(前缀):
    return "%s-%s" % (前缀, uuid.uuid4().hex[:12])


def 现在():
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ─────────────────────────────────────────────────────────────
# 写一次练习（S12 落库）
# ─────────────────────────────────────────────────────────────

def 存练习(记录):
    """
    入参：一条「练习记录」（见 domain/schema.py）。
    出参：落库后的记录（补上了 练习ID / 结束时间）。

    这一步同时写三个股——文档说 S12 往两个库各写一笔，
    练习记录本身是第三个（它承载「本次是否一次通过」）。
    """
    记录 = dict(记录)
    记录.setdefault("练习ID", 新ID("EX"))
    记录["结束时间"] = 现在()
    # 注意：**不替客户端补 开始时间**。它没给就没有——
    # 编一个出来只会让「总时长」变成一个看起来有、其实是假的数字。

    # 总时长照常记录，但不是设计目标（§3.2·3.1）。
    # naive 和 aware 相减抛的是 TypeError，不是 ValueError，所以两个都要接。
    # 算出来是负的说明客户端时钟不对，那也不写——宁可缺一个数，不要写一个错的数。
    if 记录.get("开始时间"):
        try:
            t0 = datetime.fromisoformat(记录["开始时间"])
            t1 = datetime.fromisoformat(记录["结束时间"])
            秒 = int((t1 - t0).total_seconds())
            if 秒 >= 0:
                记录["总时长秒"] = 秒
        except (ValueError, TypeError):
            pass

    追加(练习库, 记录)

    # 卡点记录库：练习记录里的每一条卡点，单独存一笔
    for 卡点 in 记录.get("卡点") or []:
        追加(卡点库, dict(卡点, 练习ID=记录["练习ID"], 记录时间=记录["结束时间"]))

    # 错题库：做错的题，用于之后重做
    for 错题 in 记录.get("错题") or []:
        追加(错题库, dict(错题, 练习ID=记录["练习ID"], 记入时间=记录["结束时间"]))

    return 记录


# ─────────────────────────────────────────────────────────────
# 错题库：读回来（含「重做」这个动作）
# ─────────────────────────────────────────────────────────────

def 标记已重做(题ID):
    """追加一笔「重做」事件。不改写原来的错题项——追加式就不回头改。"""
    if not any(x.get("题ID") == 题ID for x in 读全部(错题库)):
        return False
    追加(错题库, {"_事件": "重做", "题ID": 题ID, "时间": 现在()})
    return True


def _错题库状态():
    """把 add / 重做 两类事件合并成「每道错题现在是什么状态」。"""
    表 = {}
    for 条 in 读全部(错题库):
        if 条.get("_事件") == "重做":
            表.setdefault(条["题ID"], {}).update(已重做=True, 重做时间=条.get("时间"))
        else:
            表.setdefault(条.get("题ID"), {}).update(条)
            表[条["题ID"]].setdefault("已重做", False)
    return 表


def 未清错题():
    return [v for v in _错题库状态().values() if not v.get("已重做")]


def 未清卡点统计():
    """
    「针对某一类卡点再练几道」靠这个筛（§3.2·S12）。
    只统计还没清掉的——但卡点没有「重做」这个概念，
    所以这里给的是【出现次数】和【最近一次】，交给前端/后续决定怎么用。
    """
    统计 = {}
    for 条 in 读全部(卡点库):
        类 = 条.get("类型")
        if not 类:
            continue
        格 = 统计.setdefault(类, {"次数": 0, "最近": None, "子类计数": {}})
        格["次数"] += 1
        格["最近"] = 条.get("记录时间") or 格["最近"]
        if 条.get("子类"):
            格["子类计数"][条["子类"]] = 格["子类计数"].get(条["子类"], 0) + 1
    return 统计


def 未清账目():
    """
    第九节 #2「重练的入口」——没有这个，「重练」就只是纸上的功能。

    注意「账」和「画像」的区别（这一点容易搞混）：
      · 未清错题 = **账**。它是可以清掉的：重做一遍就划掉。
      · 未清卡点 = **画像**，不是待办。§6·决策 4 说卡点记录唯一的价值是
        「维度长期稳定」——它是一张对照表，不是一个待办清单。
        所以它**永远不清零**，也不该拿它算「还有几件事没做」。
    """
    return {
        "有账": bool(未清错题()),
        "未清错题": 未清错题(),
        "未清卡点": 未清卡点统计(),
        "_说明": "错题可重做（做一次就清了）；卡点是画像不是待办，不清零。",
    }


def 清空():
    """只给测试用。生产里不该有「清空」这个动作。"""
    for 名 in (练习库, 卡点库, 错题库):
        p = _数据目录() / 名
        if p.exists():
            p.unlink()
