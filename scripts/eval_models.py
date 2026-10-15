"""
小规模模型对照实验（在 backend 容器内运行）。

用法：
    docker exec ai-teaching-backend python /app/eval_models.py /app/uploads/model_eval_homework.png

设计：
- 复用 ai_client 的真实 prompt（OCR / 批改 / 教案 / 变式），每个功能挑 2~3 个候选模型；
- 每个候选用独立 LLMGateway 实例，log_root 指到 logs/model_eval_20261015/api_runs，
  CallLogger 照常记 api_calls.jsonl（feature/model/usage/elapsed），便于用量统计；
- 批改实验统一使用 gpt-5.5 的 OCR 结果作为输入（保证输入一致，只比批改能力）；
- 结果汇总写 logs/model_eval_20261015/results.json，详细输出写 outputs/<feature>__<model>.txt。
"""
import asyncio
import dataclasses
import json
import os
import sys
import time
import traceback

sys.path.insert(0, "/app")

from config import settings            # noqa: E402
from llm import LLMGateway              # noqa: E402
from ai_client import AIClient          # noqa: E402

OUT_DIR = "logs/model_eval_20261015"
LOG_ROOT = os.path.join(OUT_DIR, "api_runs")

CANDIDATES = {
    # OCR 视觉：现用 gpt-5.5 基线 + 国产视觉旗舰 qwen3-vl-235b + gemini（若够好可全站统一模型）
    "ocr": ["gpt-5.5", "qwen3-vl-235b-a22b-instruct", "gemini-3.1-pro-preview"],
    # 批改：现用 gemini 基线 + deepseek 主力 + kimi（中文教育场景）
    "grade": ["gemini-3.1-pro-preview", "deepseek-v4.1-pro", "kimi-k2.6"],
    # 教案（长文写作）：gemini 基线 + claude（写作强项）+ kimi
    "lessonplan": ["gemini-3.1-pro-preview", "claude-4-sonnet", "kimi-k2.6"],
    # 变式（批量、成本敏感）：gemini 基线 + 便宜的 deepseek-v4.1-flash
    "variant": ["gemini-3.1-pro-preview", "deepseek-v4.1-flash"],
}

LESSON_TOPIC = "导数的几何意义"


def make_client(model: str):
    """构造一个所有 feature 都指向指定 model 的 AIClient，并截获每次调用的 usage/elapsed。"""
    cfg = dataclasses.replace(
        settings.LLM,
        models={"default": model},
        fallbacks={},
        log_root=LOG_ROOT,
        log_request_content=True,
    )
    gw = LLMGateway(cfg, source="model_eval")
    records = []
    orig_chat = gw.chat

    async def spy(messages, **kw):
        res = await orig_chat(messages, **kw)
        records.append({
            "feature": kw.get("feature"),
            "model": res.model,
            "usage": res.usage,
            "elapsed_seconds": round(res.elapsed_seconds, 2),
            "finish_reason": res.finish_reason,
        })
        return res

    gw.chat = spy
    return AIClient(gw), records


def save_output(feature: str, model: str, content) -> str:
    safe = model.replace("/", "_").replace(":", "_")
    path = os.path.join(OUT_DIR, "outputs", f"{feature}__{safe}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2))
    return path


async def run_one(feature: str, model: str, fn, results: list):
    print(f"[eval] {feature} -> {model} ...", flush=True)
    client, records = make_client(model)
    t0 = time.perf_counter()
    entry = {"feature": feature, "model": model}
    try:
        output = await fn(client)
        entry["ok"] = True
        entry["output_file"] = save_output(feature, model, output if isinstance(output, str) else output)
        if isinstance(output, dict):
            entry["output_is_error"] = bool(output.get("error"))
            if feature == "grade" and not output.get("error"):
                qs = output.get("questions") or []
                entry["grade_summary"] = {
                    "total_questions": len(qs),
                    "correct_count": sum(1 for q in qs if q.get("is_correct")),
                    "needs_review_count": sum(1 for q in qs if q.get("needs_review")),
                }
        elif isinstance(output, list):
            entry["variant_count"] = len(output)
            entry["output_is_error"] = len(output) == 0
        elif isinstance(output, str):
            entry["output_chars"] = len(output)
            if feature == "ocr":
                entry["output_is_error"] = len(output.strip()) < 20
            if feature == "lessonplan":
                entry["output_is_error"] = len(output.strip()) < 200
    except Exception as e:  # noqa: BLE001
        entry["ok"] = False
        entry["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc()
    entry["wall_seconds"] = round(time.perf_counter() - t0, 2)
    entry["calls"] = records
    entry["total_tokens"] = sum(r["usage"].get("total_tokens", 0) for r in records)
    results.append(entry)
    print(f"[eval] {feature} -> {model} done, ok={entry['ok']}, tokens={entry['total_tokens']}, {entry['wall_seconds']}s", flush=True)


async def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else "/app/uploads/model_eval_homework.png"
    os.makedirs(LOG_ROOT, exist_ok=True)
    results = []

    # 1) OCR：先跑 gpt-5.5 基线，其结果作为批改的统一输入
    ocr_texts = {}
    for model in CANDIDATES["ocr"]:
        holder = {}

        async def fn(c, h=holder):
            text = await c.ocr_image(image_path, task_meta={"eval": "ocr", "image": os.path.basename(image_path)})
            h["text"] = text
            return text

        await run_one("ocr", model, fn, results)
        if holder.get("text"):
            ocr_texts[model] = holder["text"]

    baseline_ocr = ocr_texts.get("gpt-5.5") or next(iter(ocr_texts.values()), "")
    if not baseline_ocr:
        print("[eval] OCR 全部失败，终止", flush=True)
        sys.exit(1)
    save_output("ocr", "__baseline_for_grade", baseline_ocr)

    # 2) 批改：统一输入 baseline_ocr，不带参考答案（模拟最常见场景）
    for model in CANDIDATES["grade"]:
        async def fn(c):
            return await c.grade_homework(baseline_ocr, reference_answer=None, subject="数学",
                                          task_meta={"eval": "grade"})
        await run_one("grade", model, fn, results)

    # 3) 教案：同一课题
    for model in CANDIDATES["lessonplan"]:
        async def fn(c):
            return await c.generate_lesson_plan(
                topic=LESSON_TOPIC, period="1 课时", student_level="中等",
                requirements="", question_bank_context="", task_meta={"eval": "lessonplan"})
        await run_one("lessonplan", model, fn, results)

    # 4) 变式：固定一道典型错题
    variant_source = "已知函数 f(x) = x^3 - 3x，求 f(x) 的单调区间。（学生常见错误：忘记定义域或导数符号判断错误）"
    for model in CANDIDATES["variant"]:
        async def fn(c):
            return await c.generate_variant_questions(
                question_text=variant_source, knowledge_point="利用导数研究函数的单调性",
                count=3, task_meta={"eval": "variant"})
        await run_one("variant", model, fn, results)

    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[eval] 全部完成，{len(results)} 条记录 -> {OUT_DIR}/results.json", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
