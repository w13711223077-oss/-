#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据契约测试。

重点不是「能跑」，是**它拦得住**——
照 P0 那边的规矩：一个永远不会失败的检查，等于没有检查。
"""

import unittest

from app.domain import schema


def 一条合法练习():
    return {
        "练习ID": "EX-test",
        "题目原文": "七年七班计划组织学生去植物园研学。若每辆车坐 45 人，则有 10 人没有座位。",
        "开始时间": "2026-10-01T19:40:00+08:00",
        "结束时间": "2026-10-01T19:52:00+08:00",
        "本次一次通过": False,
        "卡点": [
            {"类型": "隐含条件未说出", "步骤": "S7", "子类": "推一把也没过",
             "依据": "追问一次后仍说不出"},
            {"类型": "标注错", "步骤": "S5"},
        ],
        "错题": [
            {"题ID": "WI-1", "题目原文": "…", "来源": "原题",
             "错在哪": [{"类型": "标注错", "步骤": "S5"}]},
        ],
    }


class 契约测试(unittest.TestCase):

    def test_合法记录能通过(self):
        self.assertEqual(schema.校验练习记录(一条合法练习()), [])

    def test_缺必填要报出来(self):
        记 = 一条合法练习()
        del 记["本次一次通过"]
        错 = schema.校验练习记录(记)
        self.assertTrue(any("本次一次通过" in e for e in 错), 错)

    def test_卡点类型只能四类(self):
        记 = 一条合法练习()
        记["卡点"] = [{"类型": "粗心", "步骤": "S5"}]     # 「粗心」不在四类里
        错 = schema.校验练习记录(记)
        self.assertTrue(any("卡点[0].类型" in e for e in 错), 错)

    def test_子类只属于隐含条件未说出(self):
        记 = 一条合法练习()
        记["卡点"] = [{"类型": "标注错", "步骤": "S5", "子类": "推一把过了"}]
        错 = schema.校验练习记录(记)
        self.assertTrue(any("子类" in e for e in 错), 错)

    def test_步骤要和卡点类型对得上(self):
        记 = 一条合法练习()
        记["卡点"] = [{"类型": "变式题未通过", "步骤": "S5"}]   # 变式题只可能是 S11
        错 = schema.校验练习记录(记)
        self.assertTrue(any("步骤" in e for e in 错), 错)

    def test_条件句必须有级别(self):
        错 = schema.校验("分句", {"i": 0, "text": "…", "type": "条件"})
        self.assertTrue(any("level" in e for e in 错), 错)

    def test_练习ID可以不填_服务端会生成(self):
        记 = 一条合法练习()
        del 记["练习ID"]
        self.assertEqual(schema.校验练习记录(记), [])

    def test_无时区的时间要拦住(self):
        # 不带时区的时间在存储层相减会抛 TypeError（不是 ValueError），
        # 所以在契约这一层就拦掉，别让它变成 500。
        记 = 一条合法练习()
        记["开始时间"] = "2026-10-01T19:40:00"          # 没时区
        错 = schema.校验练习记录(记)
        self.assertTrue(any("开始时间" in e for e in 错), 错)
        self.assertTrue(any("格式不对" in e for e in 错), 错)

    def test_时间戳不是时间也要拦住(self):
        记 = 一条合法练习()
        记["开始时间"] = "昨天下午"
        错 = schema.校验练习记录(记)
        self.assertTrue(any("开始时间" in e for e in 错), 错)

    def test_时间戳正常能过(self):
        self.assertTrue(schema.时间戳("2026-10-01T19:40:00+08:00"))
        self.assertFalse(schema.时间戳("2026-10-01T19:40:00"))
        self.assertFalse(schema.时间戳(12345))
        self.assertFalse(schema.时间戳(None))

    def test_非条件句不该有级别(self):
        错 = schema.校验("分句", {"i": 0, "text": "…", "type": "背景", "level": "直接"})
        self.assertTrue(any("level" in e for e in 错), 错)

    def test_值照文档原话_没有被改过(self):
        self.assertEqual(list(schema.句子类型), ["背景", "条件", "问题", "指令"])
        self.assertEqual(list(schema.条件级别), ["直接", "间接", "隐含"])
        self.assertEqual(list(schema.判定结果), ["一致", "不一致", "不判定"])
        self.assertEqual(list(schema.卡点类型),
                         ["标注错", "定级错", "隐含条件未说出", "变式题未通过"])
        self.assertEqual(list(schema.隐含条件子类), ["推一把过了", "推一把也没过"])
        self.assertEqual(schema.流程步骤[0], "S0")
        self.assertEqual(schema.流程步骤[-1], "S12")

    def test_口径能导出(self):
        口 = schema.口径()
        self.assertIn("卡点类型", 口)
        self.assertIn("规格", 口)


if __name__ == "__main__":
    unittest.main()
