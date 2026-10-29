#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首体验两个契约的测试：F2 备课（/api/v1/prep）与 F3 判定（/api/v1/judge）。

这里不测「判得准不准」——那是 P0 的事。
这里只测三件事：
  1. 契约形状对不对；
  2. Gate 0 之前 F3 是否老老实实返回「不判定」；
  3. 路由有没有接上。
"""

import json
import os
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from app.api import session
from app.domain import schema
from app.main import 处理器

样题 = (
    "七年七班计划组织学生去植物园研学。"
    "若每辆车坐 45 人，则有 10 人没有座位；"
    "若每辆车坐 50 人，则最后一辆车只坐了 15 人。"
    "问：一共有多少名学生？计划租多少辆车？"
    "（列方程解答，写出必要过程。）"
)


def _开桩():
    os.environ["PEILIAN_STUB"] = "1"


def _关桩():
    os.environ.pop("PEILIAN_STUB", None)


class 备课与判定测试(unittest.TestCase):

    def setUp(self):
        _开桩()

    def tearDown(self):
        _关桩()

    # ── F2 ──────────────────────────────────────────────────
    def test_备课缺题目原文(self):
        状态, 体 = session.备课({}, {})
        self.assertEqual(状态, 400)

    def test_桩备课形状合契约(self):
        状态, 体 = session.备课({"题目原文": 样题}, {})
        self.assertEqual(状态, 200)
        self.assertTrue(体["桩"])
        解剖 = 体["备课"]
        self.assertEqual(schema.校验("备课解剖", 解剖), [])
        for n, 分句 in enumerate(解剖["分句"]):
            self.assertEqual(schema.校验("分句", 分句, "$[%d]" % n), [])
        self.assertGreaterEqual(len(解剖["分句"]), 4)
        self.assertTrue(解剖["不确定项"])
        类型 = {x["type"] for x in 解剖["分句"]}
        self.assertIn("条件", 类型)
        self.assertIn("问题", 类型)
        self.assertIn("指令", 类型)

    def test_解析备课拒绝非JSON(self):
        错误 = session._解析备课("这不是 JSON", 样题)
        self.assertIsInstance(错误, str)
        self.assertIn("JSON", 错误)

    # ── F3 ──────────────────────────────────────────────────
    def test_判定拒绝未知步骤(self):
        状态, 体 = session.判定({"步骤": "S8", "学生输入": "背景", "备课解剖": {}}, {})
        self.assertEqual(状态, 400)

    def test_判定要求备课解剖(self):
        状态, 体 = session.判定({"步骤": "S5", "学生输入": "背景"}, {})
        self.assertEqual(状态, 400)

    def test_判定在Gate0前固定不判定(self):
        _, 备课体 = session.备课({"题目原文": 样题}, {})
        状态, 体 = session.判定({
            "备课解剖": 备课体["备课"],
            "学生输入": "背景",
            "步骤": "S5",
        }, {})
        self.assertEqual(状态, 200)
        self.assertEqual(体["结果"], "不判定")
        self.assertEqual(体["来源"], "未上线")


class 首体验接口测试(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _开桩()
        cls.服 = ThreadingHTTPServer(("127.0.0.1", 0), 处理器)
        cls.服.daemon_threads = True
        cls.端口 = cls.服.server_address[1]
        cls.线程 = threading.Thread(target=cls.服.serve_forever, daemon=True)
        cls.线程.start()

    @classmethod
    def tearDownClass(cls):
        cls.服.shutdown()
        cls.服.server_close()
        _关桩()

    def _调(self, 路径, 体):
        数据 = json.dumps(体, ensure_ascii=False).encode("utf-8")
        请求 = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.端口, 路径),
            data=数据,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(请求, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    def test_prep与judge走HTTP(self):
        状态, 备 = self._调("/api/v1/prep", {"题目原文": 样题})
        self.assertEqual(状态, 200)
        状态, 判 = self._调("/api/v1/judge", {
            "备课解剖": 备["备课"],
            "学生输入": "条件",
            "步骤": "S5",
        })
        self.assertEqual(状态, 200)
        self.assertEqual(判["结果"], "不判定")


if __name__ == "__main__":
    unittest.main()
