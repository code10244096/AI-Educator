"""
第二轮补跑：第一轮中网关报 model_not_found / 无渠道的型号，换替补型号重跑。

- ocr:        qwen3-vl-plus          （替补 qwen3-vl-235b-a22b-instruct，404）
- grade:      deepseek-v4-pro        （替补 deepseek-v4.1-pro，503 无渠道）
- lessonplan: doubao-seed-2-1-pro    （替补 claude-4-sonnet，503 无渠道）

用法：docker exec ai-teaching-backend python /app/eval_models_round2.py
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")

import eval_models as R1  # noqa: E402

OUT_DIR = R1.OUT_DIR
BASELINE_OCR_FILE = os.path.join(OUT_DIR, "outputs", "ocr____baseline_for_grade.txt")
IMAGE = "/app/uploads/model_eval_homework.png"

ROUND2 = {
    "ocr": ["qwen3-vl-plus"],
    "grade": ["deepseek-v4-pro"],
    "lessonplan": ["doubao-seed-2-1-pro"],
}


async def main():
    import json
    results = []

    with open(BASELINE_OCR_FILE, encoding="utf-8") as f:
        baseline_ocr = f.read()

    for model in ROUND2["ocr"]:
        async def fn(c):
            return await c.ocr_image(IMAGE, task_meta={"eval": "ocr", "round": 2})
        await R1.run_one("ocr", model, fn, results)

    for model in ROUND2["grade"]:
        async def fn(c):
            return await c.grade_homework(baseline_ocr, reference_answer=None, subject="数学",
                                          task_meta={"eval": "grade", "round": 2})
        await R1.run_one("grade", model, fn, results)

    for model in ROUND2["lessonplan"]:
        async def fn(c):
            return await c.generate_lesson_plan(
                topic=R1.LESSON_TOPIC, period="1 课时", student_level="中等",
                requirements="", question_bank_context="", task_meta={"eval": "lessonplan", "round": 2})
        await R1.run_one("lessonplan", model, fn, results)

    out = os.path.join(OUT_DIR, "results_round2.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[eval-r2] 完成 {len(results)} 条 -> {out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
