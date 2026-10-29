#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 判定可靠性测试 —— 对比工具

拿 p0_judge.py 的输出跟人工标注对照，算出四个数字：

  ① 句子类型判定准确率
  ② 条件句级别判定准确率
  ③ 【误判正例率】—— 学生说对了、模型判成错的   ← 红线，必须为 0
  ④ 说不准率（unclear）—— 单列，不算错，但太多说明系统不会判

用法：
  python p0_compare.py
  python p0_compare.py --annotations sample_annotation.json --model out/model_output.json
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 线宽（中文要按 2 格算，这里统一用中英混排的近似做法）
W = 62


def rule(ch="─"):
    return ch * W


def pct(a, b):
    return f"{a / b * 100:.1f}%" if b else "—"


def load(ann_path, out_path):
    ann = json.loads(Path(ann_path).read_text(encoding="utf-8"))
    out = json.loads(Path(out_path).read_text(encoding="utf-8"))
    truth = {p["id"]: p for p in ann["problems"]}
    got = {r["id"]: r for r in out["results"]}
    return ann, out, truth, got


def main():
    ap = argparse.ArgumentParser(description="P0 判定可靠性测试 · 对比工具")
    ap.add_argument("--annotations", default=str(HERE / "sample_annotation.json"))
    ap.add_argument("--model", default=str(HERE / "out" / "model_output.json"))
    ap.add_argument("--report", default=str(HERE / "out" / "P0_报告.txt"))
    args = ap.parse_args()

    if not Path(args.model).exists():
        sys.exit(f"找不到模型输出：{args.model}\n先跑：python p0_judge.py --baseline")
    if not Path(args.annotations).exists():
        sys.exit(f"找不到标注文件：{args.annotations}")

    ann, out, truth, got = load(args.annotations, args.model)

    L = []
    A = L.append

    A(rule("═"))
    A("  P0 判定可靠性测试 · 报告")
    A(rule("═"))
    A(f"  标注文件：{Path(args.annotations).name}")
    A(f"  模型输出：{Path(args.model).name}")
    A(f"  模式：{'基线（未调模型，本报告仅证明管道通）' if out.get('mode') == 'baseline' else '真跑 · ' + str(out.get('model'))}")
    A(f"  题数：{len(truth)}")
    A("")

    # ── ① 句子类型 ──────────────────────────────────────────
    type_ok = type_bad = 0
    type_conf = Counter()          # (真, 判) → 次数
    type_miss = defaultdict(list)  # 真类型 → 判错的例子
    for pid, p in truth.items():
        r = got.get(pid)
        if not r or not r.get("skeleton"):
            continue
        model_sents = {s["i"]: s for s in r["skeleton"].get("sentences", [])}
        for s in p["sentences"]:
            m = model_sents.get(s["i"])
            if not m:
                continue
            t, g = s["type"], m.get("type")
            if t == g:
                type_ok += 1
            else:
                type_bad += 1
                type_conf[(t, g)] += 1
                type_miss[t].append(f"{pid} 第{s['i']+1}句")

    A(rule())
    A("  ① 句子类型判定（背景 / 条件 / 问题 / 指令）")
    A(rule())
    A(f"     准确率：{pct(type_ok, type_ok + type_bad)}   （对 {type_ok} / 错 {type_bad}）")
    if type_conf:
        A("     错在哪：")
        for (t, g), n in type_conf.most_common():
            A(f"       真值「{t}」被判成「{g}」× {n}   {'、'.join(type_miss[t][:3])}")
    else:
        A("     没有判错的句子。")
    A("")

    # ── ② 条件句级别 ────────────────────────────────────────
    lvl_ok = lvl_bad = 0
    lvl_conf = Counter()
    for pid, p in truth.items():
        r = got.get(pid)
        if not r or not r.get("skeleton"):
            continue
        model_sents = {s["i"]: s for s in r["skeleton"].get("sentences", [])}
        for s in p["sentences"]:
            if s["type"] != "条件" or not s.get("level"):
                continue
            m = model_sents.get(s["i"])
            if not m:
                continue
            if s["level"] == m.get("level"):
                lvl_ok += 1
            else:
                lvl_bad += 1
                lvl_conf[(s["level"], m.get("level"))] += 1

    A(rule())
    A("  ② 条件句级别判定（直接 / 间接 / 隐含）")
    A(rule())
    A(f"     准确率：{pct(lvl_ok, lvl_ok + lvl_bad)}   （对 {lvl_ok} / 错 {lvl_bad}）")
    if lvl_conf:
        A("     错在哪：")
        for (t, g), n in lvl_conf.most_common():
            A(f"       真值「{t}」被判成「{g}」× {n}")
    else:
        A("     没有判错的条件句。")
    A("")

    # ── ③ / ④ 误判正例率 —— 红线 ───────────────────────────
    n_correct = n_wrong = 0
    fp = fn = unclear = 0
    fp_list, fn_list, un_list = [], [], []
    for pid, p in truth.items():
        r = got.get(pid)
        if not r:
            continue
        model_cases = {c["case_id"]: c for c in r.get("cases", [])}
        for c in p.get("adjudication_cases", []):
            m = model_cases.get(c["case_id"])
            if not m:
                continue
            t, v = c["truth"], m.get("verdict")
            if t == "correct":
                n_correct += 1
            elif t == "wrong":
                n_wrong += 1
            if v == "unclear":
                unclear += 1
                un_list.append(c["case_id"])
            elif t == "correct" and v == "wrong":
                fp += 1
                fp_list.append((c["case_id"], c["student_says"], m.get("reason", "")))
            elif t == "wrong" and v == "correct":
                fn += 1
                fn_list.append((c["case_id"], c["student_says"], m.get("reason", "")))

    A(rule("═"))
    A("  ③ 误判正例率  ← 这是红线")
    A(rule("═"))
    A(f"     学生说对了、模型判成错的：{fp} / {n_correct}  →  {pct(fp, n_correct)}")
    if fp:
        A("")
        A("     ⚠️  红线已破。具体是哪几条：")
        for cid, said, why in fp_list:
            A(f"       {cid}  学生说：「{said}」")
            A(f"              模型理由：{why}")
        A("")
        A("     结论：判定不能直接上线。按 02-SWOT ST-2，把条件句三级降级为「引导性提问」，")
        A("           产品形态要改，而不是硬着头皮写代码。")
    else:
        A("     ✅ 红线未破。")
    A("")

    A(rule())
    A("  ④ 其他两个数字（同样要看，但不是红线）")
    A(rule())
    A(f"     误判负例率（学生说错了、模型判成对）：{fn} / {n_wrong}  →  {pct(fn, n_wrong)}")
    if fn:
        for cid, said, why in fn_list:
            A(f"       {cid}  学生说：「{said}」→ 模型理由：{why}")
    A(f"     说不准率（模型自己判 unclear）：{unclear}  →  {pct(unclear, n_correct + n_wrong)}")
    if un_list:
        A(f"       用例：{'、'.join(un_list)}")
    A("")

    # ── 判读 ────────────────────────────────────────────────
    A(rule("═"))
    A("  怎么读这份报告")
    A(rule("═"))
    A("  ① 句子类型准确率低  →  F4 逐句标注不能自动判对错，只能给提示")
    A("  ② 条件句级别准确率低 →  F5 条件定级要降级，这是产品靶心，降级代价最大")
    A("  ③ 误判正例率 > 0    →  【不能上线】学生会被教错，这是唯一一条不能越过的线")
    A("  ④ 说不准率太高      →  说明系统不敢判，产品会变得没有反馈（也是失败）")
    A("")
    A("  如果 ① ② 的数字明显低于 90%，先别改产品——")
    A("  先看是不是提示词没写清楚（p0_judge.py 顶部的 SYSTEM_PROMPT）。")
    A(rule("═"))

    report = "\n".join(L)
    print(report)

    out_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    summary = {
        "题数": len(truth),
        "模式": out.get("mode"),
        "句子类型准确率": round(type_ok / (type_ok + type_bad), 4) if (type_ok + type_bad) else None,
        "条件级别准确率": round(lvl_ok / (lvl_ok + lvl_bad), 4) if (lvl_ok + lvl_bad) else None,
        "误判正例率": round(fp / n_correct, 4) if n_correct else None,
        "误判负例率": round(fn / n_wrong, 4) if n_wrong else None,
        "说不准率": round(unclear / (n_correct + n_wrong), 4) if (n_correct + n_wrong) else None,
        "红线通过": fp == 0,
    }
    (out_path.parent / "P0_摘要.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✓ 报告已写出：{out_path}")
    return 0 if fp == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
