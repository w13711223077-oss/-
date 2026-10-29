#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 判定可靠性测试 —— 判定工具

作用：拿标注好的题目去问模型，看它判得对不对。
      这一步对应产品里的 F2 备课 + F3 判定。

两种模式：
  --baseline   不调 API。把标注当作"模型输出"复制一份，用来验证整条管道通不通。
               先跑这个，确认文件和脚本没问题，再去调真的模型。
  默认（真跑）  读 DEEPSEEK_API_KEY 环境变量，逐题调模型。

用法：
  python p0_judge.py --baseline
  set DEEPSEEK_API_KEY=sk-xxx && python p0_judge.py
  python p0_judge.py --model deepseek-flash

只依赖 Python 标准库，不用装任何东西。
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ─────────────────────────────────────────────────────────────
# 提示词：这里定的就是产品里 F2 备课 / F3 判定的口径。
# 改这里 = 改产品行为，所以要谨慎。
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个初中七年级应用题的审题教练。你的任务是把一道题解剖清楚，供后续判定学生使用。

【四类句子】每句话必须归入且只归入以下一类：
- 背景：交代情境，不含数量关系、不提要求
- 条件：给出数量、关系或事实依据
- 问题：提出要回答什么
- 指令：规定答题方式（如"列方程解答""保留两位小数"）

【条件句三级】只对"条件"类句子判级：
- 直接：数字或关系直接给出，拿来就能用
- 间接：要转一步才能用（如"还剩5棵"→多的数量）
- 隐含：没写在字面上，要从常识、概念或前后状态推出来

【隐含条件】列出这道题藏着的、字面上没有的关系。可能有多个。
注意：隐含条件往往有不止一个说法，判断时看意思，不要只对字面。

【不确定】如果你对某一项没有把握，就在该项的 confidence 里写 "低"。
不要为了显得确定而硬判。

严格输出 JSON，格式：
{
  "sentences": [{"i": 0, "type": "背景|条件|问题|指令", "level": "直接|间接|隐含 或 null", "confidence": "高|中|低"}],
  "implicit": ["隐含条件1", "隐含条件2"]
}
"""

JUDGE_PROMPT = """下面是这道题的标准解剖，以及一个学生说出的"隐含条件"。

【题目】
{text}

【标准解剖】
{skeleton}

【学生说的是】
{student_says}

请判断：学生说出的这个内容，作为"这道题藏着的隐含条件"，是否成立？

判定规则（重要）：
- 看【意思】是否成立，不要对字面措辞。
- 换一种说法、用口语表达、多带了别的意思，只要核心成立，就算对。
- 如果学生说的是算出来的结果（不是题目里藏着的条件），算不对。
- 如果你拿不准，就判 "unclear"，不要硬判。

严格输出 JSON：
{{"verdict": "correct|wrong|unclear", "reason": "一句话理由"}}
"""


def api_call(base_url, api_key, model, messages, retries=2):
    """调 OpenAI 兼容接口。失败重试。"""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
        },
    )

    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = json.loads(r.read().decode("utf-8"))
            return json.loads(payload["choices"][0]["message"]["content"])
        except Exception as e:                      # noqa: BLE001
            last = e
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"调用失败（已重试 {retries} 次）：{last}")


def skeleton_of(problem):
    """把标准解剖压成一段给模型看的文字。"""
    lines = []
    for s in problem["sentences"]:
        t = s["type"]
        if s.get("level"):
            t += f"({s['level']})"
        lines.append(f"  [{s['i']}] {t}：{s['text']}")
    imp = "；".join(problem.get("implicit", [])) or "（无）"
    return "句子：\n" + "\n".join(lines) + "\n隐含条件：\n  " + imp


def judge_one(problem, api_key, base_url, model):
    """对一道题：先解剖，再逐条判学生的说法。"""
    out = {"id": problem["id"], "skeleton": None, "cases": []}

    sk = api_call(base_url, api_key, model, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "请解剖这道题：\n\n" + problem["text"]},
    ])
    out["skeleton"] = sk

    sk_text = skeleton_of(problem)
    for case in problem.get("adjudication_cases", []):
        try:
            v = api_call(base_url, api_key, model, [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": JUDGE_PROMPT.format(
                    text=problem["text"],
                    skeleton=sk_text,
                    student_says=case["student_says"])},
            ])
        except Exception as e:                      # noqa: BLE001
            v = {"verdict": "error", "reason": str(e)}
        out["cases"].append({
            "case_id": case["case_id"],
            "student_says": case["student_says"],
            "verdict": v.get("verdict", "error"),
            "reason": v.get("reason", ""),
        })
    return out


def baseline(problems):
    """不调模型：把标注复制成'模型输出'，证明管道通。"""
    out = []
    for p in problems:
        out.append({
            "id": p["id"],
            "skeleton": {
                "sentences": [
                    {"i": s["i"], "type": s["type"],
                     "level": s.get("level"), "confidence": "高"}
                    for s in p["sentences"]
                ],
                "implicit": p.get("implicit", []),
            },
            "cases": [
                {"case_id": c["case_id"], "student_says": c["student_says"],
                 "verdict": c["truth"], "reason": "（基线模式：直接采用标注）"}
                for c in p.get("adjudication_cases", [])
            ],
        })
    return out


def main():
    ap = argparse.ArgumentParser(description="P0 判定可靠性测试 · 判定工具")
    ap.add_argument("--annotations", default=str(HERE / "sample_annotation.json"),
                    help="标注文件（标准答案）")
    ap.add_argument("--out", default=str(HERE / "out" / "model_output.json"),
                    help="模型输出写到哪")
    ap.add_argument("--baseline", action="store_true",
                    help="不调 API，只验证管道")
    ap.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"))
    ap.add_argument("--base-url", default=os.environ.get(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    args = ap.parse_args()

    ann_path = Path(args.annotations)
    if not ann_path.exists():
        sys.exit(f"找不到标注文件：{ann_path}")

    data = json.loads(ann_path.read_text(encoding="utf-8"))
    problems = data["problems"]
    print(f"读入标注：{ann_path.name} —— {len(problems)} 道题，"
          f"{sum(len(p.get('adjudication_cases', [])) for p in problems)} 个判定用例")

    if args.baseline:
        print("模式：基线（不调 API，只验证管道是否通）")
        result = baseline(problems)
    else:
        key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not key:
            sys.exit("没有找到 DEEPSEEK_API_KEY 环境变量。\n"
                     "  要么设置它，要么先跑 --baseline 验证管道：\n"
                     "    set DEEPSEEK_API_KEY=sk-xxxx   （Windows）\n"
                     "    export DEEPSEEK_API_KEY=sk-xxxx （macOS/Linux）")
        print(f"模式：真跑 —— model={args.model}  base_url={args.base_url}")
        result = []
        for i, p in enumerate(problems, 1):
            print(f"  [{i}/{len(problems)}] {p['id']} {p['title']} ...", flush=True)
            try:
                result.append(judge_one(p, key, args.base_url, args.model))
            except Exception as e:                  # noqa: BLE001
                print(f"      ✗ {e}")
                result.append({"id": p["id"], "skeleton": None, "cases": [],
                               "error": str(e)})

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"source": ann_path.name, "mode": "baseline" if args.baseline else "api",
                    "model": None if args.baseline else args.model,
                    "results": result},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\n✓ 已写出：{out_path}")
    print("  下一步：python p0_compare.py")


if __name__ == "__main__":
    main()
