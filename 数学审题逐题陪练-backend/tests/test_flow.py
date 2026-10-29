#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话状态机测试：S1—S8 的转移、守卫、可见性投影。
不测“判得准不准”（那是 P0）；只测流程与契约。
"""

import os
import shutil
import tempfile
import unittest

from app.engine import flow
from app.engine import audit


class 会话流程测试(unittest.TestCase):

    def setUp(self):
        self.临时 = tempfile.mkdtemp(prefix="peilian-flow-")
        os.environ["PEILIAN_DATA_DIR"] = self.临时
        os.environ["PEILIAN_STUB"] = "1"

    def tearDown(self):
        for k in ("PEILIAN_DATA_DIR", "PEILIAN_STUB"):
            os.environ.pop(k, None)
        shutil.rmtree(self.临时, ignore_errors=True)

    def _到S5(self):
        s = flow.新建()
        sid = s["session_id"]
        题 = ("七年七班计划组织学生去植物园研学。若每辆车坐 45 人，则有 10 人没有座位；"
              "若每辆车坐 50 人，则最后一辆车只坐了 15 人。问：一共有多少名学生？"
              "计划租多少辆车？（列方程解答，写出必要过程。）")
        r = flow.上传题目(sid, {"mode": "text", "text": 题})
        r = flow.确认题目(sid, r["text"])
        flow.开始(sid)
        return sid

    def test_创建是CREATED(self):
        s = flow.新建()
        self.assertEqual(s["status"], "CREATED")
        self.assertTrue(s["session_id"].startswith("S-"))

    def test_上传文本到CONFIRMING(self):
        s = flow.新建()
        r = flow.上传题目(s["session_id"], {"mode": "text", "text": "若每辆车坐 45 人，则有 10 人没有座位。"})
        self.assertEqual(r["session"]["status"], "CONFIRMING")
        self.assertTrue(r["text"])

    def test_确认后备课锁定且不泄漏答案(self):
        s = flow.新建()
        sid = s["session_id"]
        r = flow.上传题目(sid, {"mode": "text", "text": "若每辆车坐 45 人，则有 10 人没有座位。问：一共有多少名学生？"})
        r = flow.确认题目(sid, r["text"])
        self.assertEqual(r["session"]["status"], "READY")
        # 学生投影里不能出现分句类型/级别/隐含条件/答案
        文 = str(r["session"])
        for 禁 in ("分句", "implicit_set", "level", "type", "答案", "solution"):
            self.assertNotIn(禁, 文)
        # 内部存储有完整备课
        内部 = flow._取(sid)
        self.assertTrue(内部["prep"]["locked"])
        self.assertTrue(内部["prep"]["分句"])

    def test_未开场不能答(self):
        s = flow.新建()
        sid = s["session_id"]
        r = flow.上传题目(sid, {"mode": "text", "text": "若每辆车坐 45 人，则有 10 人没有座位。"})
        flow.确认题目(sid, r["text"])
        with self.assertRaises(flow.流程错误) as ctx:
            flow.答题(sid, {"step": "S5", "target_ref": "sentence:0", "input": "背景"})
        self.assertEqual(ctx.exception.code, "E_STATE")

    def test_完整走到CLOSED(self):
        sid = self._到S5()
        # S5
        while flow.公开(sid)["status"] == "ANNOTATING":
            nxt = flow.公开(sid)["progress"]["next"]
            flow.答题(sid, {"step": "S5", "target_ref": nxt["target_ref"], "input": "背景"})
        # S6
        while flow.公开(sid)["status"] == "GRADING_CONDITIONS":
            nxt = flow.公开(sid)["progress"]["next"]
            flow.答题(sid, {"step": "S6", "target_ref": nxt["target_ref"], "input": "直接"})
        # S7
        self.assertEqual(flow.公开(sid)["status"], "PROBING_IMPLICIT")
        flow.答题(sid, {"step": "S7", "target_ref": "implicit", "input": "总人数不变"})
        flow.答题(sid, {"step": "S7", "target_ref": "implicit", "input": "还是总人数不变"})
        self.assertEqual(flow.公开(sid)["status"], "CLOSING")
        r = flow.收束(sid)
        self.assertEqual(r["session"]["status"], "CLOSED")
        self.assertIn("headline", r["session"]["summary"])

    def test_同句重复答被拒(self):
        sid = self._到S5()
        nxt = flow.公开(sid)["progress"]["next"]
        flow.答题(sid, {"step": "S5", "target_ref": nxt["target_ref"], "input": "背景"})
        with self.assertRaises(flow.流程错误) as ctx:
            flow.答题(sid, {"step": "S5", "target_ref": nxt["target_ref"], "input": "条件"})
        self.assertEqual(ctx.exception.code, "E_LIMIT")

    def test_丢弃是终态(self):
        sid = self._到S5()
        r = flow.丢弃(sid)
        self.assertEqual(r["session"]["status"], "DISCARDED")
        with self.assertRaises(flow.流程错误) as ctx:
            flow.答题(sid, {"step": "S5", "target_ref": "sentence:0", "input": "背景"})
        self.assertEqual(ctx.exception.code, "E_STATE")

    def test_答案字段剥离(self):
        原 = {"type": "条件", "level": "间接", "text": "x", "answer": "42",
              "nested": {"solution": "..."}}
        净 = audit.剥答案(原)
        self.assertNotIn("answer", 净)
        self.assertNotIn("solution", 净["nested"])
        self.assertIn("text", 净)


if __name__ == "__main__":
    unittest.main()
