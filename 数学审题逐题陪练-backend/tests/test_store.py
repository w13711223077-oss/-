#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""存储层测试：三个股各写对没有、未清账目算对没有。"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta

from app.store import jsonl_store as 库


def _十二分钟前():
    return (datetime.now().astimezone() - timedelta(minutes=12)).isoformat(timespec="seconds")


def 一条练习(题ID="WI-1"):
    return {
        "练习ID": "EX-1",
        "题目原文": "七年七班计划组织学生去植物园研学。",
        "开始时间": _十二分钟前(),
        "本次一次通过": False,
        "卡点": [
            {"类型": "隐含条件未说出", "步骤": "S7", "子类": "推一把过了"},
            {"类型": "标注错", "步骤": "S5"},
        ],
        "错题": [
            {"题ID": 题ID, "题目原文": "七年七班…", "来源": "原题",
             "错在哪": [{"类型": "标注错", "步骤": "S5"}]},
        ],
    }


class 存储测试(unittest.TestCase):

    def setUp(self):
        self.临时 = tempfile.mkdtemp(prefix="peilian-test-")
        os.environ["PEILIAN_DATA_DIR"] = self.临时

    def tearDown(self):
        os.environ.pop("PEILIAN_DATA_DIR", None)
        shutil.rmtree(self.临时, ignore_errors=True)

    def test_写一次练习_三个股各落一笔(self):
        库.存练习(一条练习())
        self.assertEqual(len(库.读全部(库.练习库)), 1)
        self.assertEqual(len(库.读全部(库.卡点库)), 2)      # 两条卡点
        self.assertEqual(len(库.读全部(库.错题库)), 1)      # 一道错题

    def test_总时长自动算出来(self):
        记 = 库.存练习(一条练习())
        self.assertIsInstance(记.get("总时长秒"), int)
        self.assertGreaterEqual(记["总时长秒"], 0)

    def test_不给开始时间就不编_也不记总时长(self):
        # 编一个开始时间出来，只会让「总时长」变成一个看起来有、其实是假的数字
        记 = 一条练习()
        del 记["开始时间"]
        存 = 库.存练习(记)
        self.assertNotIn("开始时间", 存)
        self.assertNotIn("总时长秒", 存)

    def test_时间格式乱掉也不会炸(self):
        # 无时区的时间相减抛的是 TypeError —— 存储层两种异常都要接住
        记 = 一条练习()
        记["开始时间"] = "2026-10-01T19:40:00"      # 没时区
        存 = 库.存练习(记)                            # 不该抛
        self.assertNotIn("总时长秒", 存)

    def test_未清账目_一开始有账(self):
        库.存练习(一条练习())
        账 = 库.未清账目()
        self.assertEqual(len(账["未清错题"]), 1)
        self.assertFalse(账["未清错题"][0]["已重做"])
        self.assertIn("隐含条件未说出", 账["未清卡点"])
        self.assertEqual(账["未清卡点"]["隐含条件未说出"]["次数"], 1)

    def test_清了账_未清里就没有了(self):
        库.存练习(一条练习("WI-1"))
        self.assertTrue(库.标记已重做("WI-1"))
        self.assertEqual(len(库.未清错题()), 0)

    def test_标记不存在的题返回假(self):
        self.assertFalse(库.标记已重做("WI-不存在"))

    def test_重复练同一题_未清只算一次(self):
        库.存练习(一条练习("WI-1"))
        库.存练习(一条练习("WI-1"))
        状态 = 库._错题库状态()
        self.assertEqual(len(状态), 1)

    def test_坏行不影响读(self):
        p = 库._数据目录() / 库.错题库
        p.write_text('{"题ID": "WI-x", "已重做": false}\n'
                     '这是半行写坏的内容\n', encoding="utf-8")
        读 = 库.读全部(库.错题库)
        self.assertEqual(len(读), 1)


if __name__ == "__main__":
    unittest.main()
