# -*- coding: utf-8 -*-
"""变式题质量校验：用真实模型对多道代表性错题生成变式，输出原文/变式/相似度指标供人工判定。

判定标准（人工）：
- 合格：情境/条件组织/设问角度至少两处实质变化，读起来是新题，考点一致，答案可核对
- 不合格：只改数字、只换名词、句式不变

相似度指标（辅助）：数字重合率 > 0.8 且二字节 Jaccard > 0.7 视为疑似"换数字"变式。
"""
import asyncio
import json
import os
import re
import sys
import time

BACKEND_DIR = os.environ.get("BACKEND_DIR", r"E:\AI-Educator\backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ai_client import AIClient  # noqa: E402
from config import settings  # noqa: E402
from llm import LLMGateway  # noqa: E402

# 本地 config 的 key 失效时，可用环境变量覆盖（与 spot_check_fixed_models.py 一致）
_env_key = os.environ.get("LLM_API_KEY", "").strip()
if _env_key:
    settings.LLM.api_key = _env_key
    print("[CFG] 使用 LLM_API_KEY 环境变量覆盖本地配置", flush=True)

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "variant_verify_output.json")

CASES = [
    ("高中数学-圆锥曲线", "已知椭圆 C: x²/a² + y²/b² = 1 (a>b>0) 的离心率为 √2/2，且过点 (1, √2/2)。(1) 求椭圆 C 的方程；(2) 设 F 为椭圆左焦点，过 F 的直线 l 与椭圆交于 A, B 两点，求 △AOB (O 为原点) 面积的最大值。", "椭圆的标准方程与直线和圆锥曲线的位置关系、三角形面积最值", "数学"),
    ("三角求值", "已知 tanα=2，求 (sinα+cosα)/(sinα-cosα) 的值", "同角三角函数的基本关系", "数学"),
    ("小学数学-分数应用", "小明看一本 120 页的故事书，第一天看了全书的 1/4，第二天看了全书的 1/3，还剩多少页没有看？", "分数应用题", "数学"),
    ("初中物理-摩擦力", "一个质量为 2 kg 的物体受到 10 N 的水平拉力，在粗糙水平面上做匀速直线运动，求物体受到的摩擦力大小和方向。", "二力平衡与摩擦力", "物理"),
    ("英语-时态", "He _____ (be) a teacher for ten years.（用所给词的适当形式填空）", "现在完成时", "英语"),
]


def numbers(text: str):
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def bigrams(text: str):
    text = re.sub(r"\s+", "", text)
    return set(text[i:i + 2] for i in range(len(text) - 1)) if len(text) >= 2 else {text}


def metrics(original: str, variant: str):
    nums_o, nums_v = numbers(original), numbers(variant)
    digit_overlap = len(nums_v & nums_o) / len(nums_v) if nums_v else 0.0
    bo, bv = bigrams(original), bigrams(variant)
    jaccard = len(bo & bv) / len(bo | bv) if bo | bv else 0.0
    return {"digit_overlap": round(digit_overlap, 2), "bigram_jaccard": round(jaccard, 2)}


async def main():
    client = AIClient(gateway=LLMGateway(settings.LLM, source="variant_verify"))
    results = []
    try:
        for name, q_text, kp, subject in CASES:
            t0 = time.time()
            print(f"[GEN] {name} ...", flush=True)
            try:
                variants = await client.generate_variant_questions(
                    question_text=q_text, knowledge_point=kp, count=3, subject=subject,
                    task_meta={"verify_case": name},
                )
                error = None
            except Exception as exc:  # noqa: BLE001
                variants, error = [], f"{type(exc).__name__}: {exc}"
            print(f"[{'OK' if variants else 'FAIL'}] {name} {round(time.time() - t0, 1)}s "
                  f"variants={len(variants)} {error or ''}", flush=True)
            scored = [
                {**v, **metrics(q_text, v.get("question_text", ""))}
                for v in variants if isinstance(v, dict)
            ]
            results.append({"case": name, "original": q_text, "knowledge_point": kp,
                            "subject": subject, "error": error, "variants": scored})
    finally:
        await client.gateway.aclose()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n输出已写入 {OUT_PATH}", flush=True)

    # 疑似"只改数字"的快速预警
    for r in results:
        for v in r["variants"]:
            if v["digit_overlap"] >= 0.8 and v["bigram_jaccard"] >= 0.7:
                print(f"[WARN] {r['case']} variant#{v.get('variant_number')} "
                      f"digit_overlap={v['digit_overlap']} jaccard={v['bigram_jaccard']} 疑似只改数字", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
