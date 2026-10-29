#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话端点 HTTP 测试：POST /sessions → problem → confirm → start → answer → close。
用桩模式，不联网。
"""

import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from app.main import 处理器

样题 = (
    "七年七班计划组织学生去植物园研学。"
    "若每辆车坐 45 人，则有 10 人没有座位；"
    "若每辆车坐 50 人，则最后一辆车只坐了 15 人。"
    "问：一共有多少名学生？计划租多少辆车？"
    "（列方程解答，写出必要过程。）"
)


class 会话接口测试(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.临时 = tempfile.mkdtemp(prefix="peilian-sessions-")
        os.environ["PEILIAN_DATA_DIR"] = cls.临时
        os.environ["PEILIAN_STUB"] = "1"
        cls.服 = ThreadingHTTPServer(("127.0.0.1", 0), 处理器)
        cls.服.daemon_threads = True
        cls.端口 = cls.服.server_address[1]
        cls.线程 = threading.Thread(target=cls.服.serve_forever, daemon=True)
        cls.线程.start()

    @classmethod
    def tearDownClass(cls):
        cls.服.shutdown()
        cls.服.server_close()
        for k in ("PEILIAN_DATA_DIR", "PEILIAN_STUB"):
            os.environ.pop(k, None)
        shutil.rmtree(cls.临时, ignore_errors=True)

    def _调(self, 方法, 路径, 体=None):
        数据 = json.dumps(体, ensure_ascii=False).encode("utf-8") if 体 is not None else None
        请求 = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.端口, 路径),
            data=数据,
            headers={"Content-Type": "application/json"} if 数据 else {},
            method=方法,
        )
        try:
            with urllib.request.urlopen(请求, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def _新会话(self):
        状态, 体 = self._调("POST", "/api/v1/sessions", {})
        self.assertEqual(状态, 201)
        return 体["session_id"]

    def test_完整S1到S8(self):
        sid = self._新会话()
        状态, 体 = self._调("POST", "/api/v1/sessions/%s/problem" % sid,
                            {"mode": "text", "text": 样题})
        self.assertEqual(状态, 200)
        self.assertEqual(体["session"]["status"], "CONFIRMING")

        状态, 体 = self._调("POST", "/api/v1/sessions/%s/confirm" % sid, {"text": 样题})
        self.assertEqual(状态, 200)
        self.assertEqual(体["session"]["status"], "READY")
        self.assertNotIn("分句", json.dumps(体, ensure_ascii=False))

        状态, 体 = self._调("POST", "/api/v1/sessions/%s/start" % sid, {})
        self.assertEqual(状态, 200)
        self.assertEqual(体["session"]["status"], "ANNOTATING")
        self.assertEqual(体["session"]["progress"]["next"]["step"], "S5")

        # S5
        while True:
            状态, 体 = self._调("GET", "/api/v1/sessions/%s" % sid)
            if 体["status"] != "ANNOTATING":
                break
            nxt = 体["progress"]["next"]
            状态, 答 = self._调("POST", "/api/v1/sessions/%s/answer" % sid,
                                {"step": "S5", "target_ref": nxt["target_ref"], "input": "背景"})
            self.assertEqual(状态, 200)
            self.assertEqual(答["verdict"]["结果"], "不判定")

        # S6
        while True:
            状态, 体 = self._调("GET", "/api/v1/sessions/%s" % sid)
            if 体["status"] != "GRADING_CONDITIONS":
                break
            nxt = 体["progress"]["next"]
            状态, 答 = self._调("POST", "/api/v1/sessions/%s/answer" % sid,
                                {"step": "S6", "target_ref": nxt["target_ref"], "input": "直接"})
            self.assertEqual(状态, 200)

        # S7
        状态, 体 = self._调("GET", "/api/v1/sessions/%s" % sid)
        self.assertEqual(体["status"], "PROBING_IMPLICIT")
        状态, 答 = self._调("POST", "/api/v1/sessions/%s/answer" % sid,
                            {"step": "S7", "target_ref": "implicit", "input": "总人数不变"})
        self.assertEqual(状态, 200)
        状态, 答 = self._调("POST", "/api/v1/sessions/%s/answer" % sid,
                            {"step": "S7", "target_ref": "implicit", "input": "还是总人数不变"})
        self.assertEqual(状态, 200)
        self.assertEqual(答["session"]["status"], "CLOSING")

        状态, 体 = self._调("POST", "/api/v1/sessions/%s/close" % sid, {})
        self.assertEqual(状态, 200)
        self.assertEqual(体["session"]["status"], "CLOSED")
        self.assertIn("headline", 体["session"]["summary"])

    def test_未知会话404(self):
        状态, 体 = self._调("GET", "/api/v1/sessions/S-nope")
        self.assertEqual(状态, 404)
        self.assertEqual(体["码"], "E_NOT_FOUND")

    def test_错误步骤400(self):
        sid = self._新会话()
        状态, 体 = self._调("POST", "/api/v1/sessions/%s/answer" % sid,
                            {"step": "S5", "target_ref": "sentence:0", "input": "背景"})
        self.assertEqual(状态, 400)
        self.assertEqual(体["码"], "E_STATE")

    def test_重复答409(self):
        sid = self._新会话()
        self._调("POST", "/api/v1/sessions/%s/problem" % sid, {"mode": "text", "text": 样题})
        self._调("POST", "/api/v1/sessions/%s/confirm" % sid, {"text": 样题})
        self._调("POST", "/api/v1/sessions/%s/start" % sid, {})
        状态, 体 = self._调("GET", "/api/v1/sessions/%s" % sid)
        nxt = 体["progress"]["next"]
        self._调("POST", "/api/v1/sessions/%s/answer" % sid,
                 {"step": "S5", "target_ref": nxt["target_ref"], "input": "背景"})
        状态, 体 = self._调("POST", "/api/v1/sessions/%s/answer" % sid,
                            {"step": "S5", "target_ref": nxt["target_ref"], "input": "条件"})
        self.assertEqual(状态, 409)
        self.assertEqual(体["码"], "E_LIMIT")


if __name__ == "__main__":
    unittest.main()
