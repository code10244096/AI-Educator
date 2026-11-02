# -*- coding: utf-8 -*-
"""
2026-11-02 固定三模型质量抽检（新 key sk-...y8Ni，在容器内运行）。

只测固定选型在各自功能位上的表现，另加交叉对照：
  lessonplan: gemini-3.1-pro-preview（主）、deepseek-v4.1-flash（备）
  grade:      gemini-3.1-pro-preview（主）、deepseek-v4.1-flash（备）
  variant:    deepseek-v4.1-flash（主）、gemini-3.1-pro-preview（备）
  ocr:        gpt-5.5（主）、deepseek-v4.1-flash（备）× 图 A/B/C
原文落 <exp_dir>/outputs/，调用日志走 LLMGateway 标准日志（source="model_eval"）。
"""
import asyncio
import json
import os
import sys
import time

BACKEND_DIR = os.environ.get("BACKEND_DIR", "/app")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ai_client import AIClient  # noqa: E402
from llm import LLMConfig, LLMGateway  # noqa: E402

BASE_URL = os.environ.get("LLM_BASE_URL", "https://yibuapi.com/v1")

GEMINI = "gemini-3.1-pro-preview"
DSFLASH = "deepseek-v4.1-flash"
GPT55 = "gpt-5.5"

OCR_IMAGES = [
    ("A", "homework_test.png"),
    ("B", "images/B_hard_handwriting.png"),
    ("C", "images/C_mixed_messy.png"),
]

GRADE_CASES = [
    ("grade-1",
     "导数基础小测\n1. f'(x) = 2x + 1\n2. 切线方程 y = 3x - 2\n3. 极小值点 x = 2, f(2) = 1",
     "1. f'(x)=2x+1；2. y=3x-2；3. 极小值点 x=1, f(1)=-2"),
    ("grade-2",
     "1. x=2 或 x=3\n2. y=3x-2\n3. log2 8 = 4\n4. f'(x)=3x^2\n5. （未作答）",
     "1. x=2, x=3；2. 3x-y-2=0；3. 3；4. 3x^2；5. 1/2"),
]

LESSONPLAN_CASE = ("lp-1", "导数的几何意义", "1 课时", "中等")
VARIANT_CASE = ("var-1", "已知 tanα=2，求 (sinα+cosα)/(sinα-cosα) 的值", "同角三角函数关系", 3)


def safe_name(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


class Runner:
    def __init__(self, exp_dir: str, log_root: str):
        self.exp_dir = exp_dir
        self.log_root = log_root
        self.outputs_dir = os.path.join(exp_dir, "outputs")
        os.makedirs(self.outputs_dir, exist_ok=True)
        self.index_path = os.path.join(exp_dir, "results_index.jsonl")
        api_key = os.environ.get("LLM_API_KEY", "").strip()
        if not api_key:
            print("FATAL: LLM_API_KEY 未设置", file=sys.stderr)
            sys.exit(2)
        self.api_key = api_key
        self.stats = {"calls": 0, "ok": 0, "fail": 0}

    def make_client(self, model: str) -> AIClient:
        cfg = LLMConfig(
            api_key=self.api_key,
            base_url=BASE_URL,
            models={"default": model},
            fallbacks={},
            timeout=600,
            max_retries=1,
            log_root=self.log_root,
            log_request_content=True,
        )
        return AIClient(gateway=LLMGateway(cfg, source="model_eval"))

    def record(self, entry: dict):
        with open(self.index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save_output(self, feature, case, model, content) -> str:
        fname = f"{feature}__{case}__{safe_name(model)}.txt"
        path = os.path.join(self.outputs_dir, fname)
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return fname

    async def call(self, feature, case, model, coro_factory):
        entry = {"feature": feature, "case": case, "model": model, "ts": time.time()}
        self.stats["calls"] += 1
        t0 = time.perf_counter()
        try:
            result = await coro_factory()
            entry["ok"] = True
            entry["secs"] = round(time.perf_counter() - t0, 1)
            entry["output_file"] = self.save_output(feature, case, model, result)
            entry["output_len"] = os.path.getsize(os.path.join(self.outputs_dir, entry["output_file"]))
            self.stats["ok"] += 1
        except Exception as e:  # noqa: BLE001
            entry["ok"] = False
            entry["secs"] = round(time.perf_counter() - t0, 1)
            entry["error"] = f"{type(e).__name__}: {e}"[:500]
            self.stats["fail"] += 1
            print(f"[FAIL] {feature}/{case}/{model}: {entry['error']}", flush=True)
        self.record(entry)
        print(f"[{'OK' if entry['ok'] else 'ERR'}] {feature:10s} {case:8s} {model} {entry.get('secs')}s", flush=True)

    async def run(self):
        # lessonplan ×2 模型
        lp_case, topic, period, level = LESSONPLAN_CASE
        for model in (GEMINI, DSFLASH):
            client = self.make_client(model)
            await self.call("lessonplan", lp_case, model,
                            lambda: client.generate_lesson_plan(
                                topic, period=period, student_level=level,
                                task_meta={"eval_case": lp_case}))
            await client.gateway.aclose()

        # grade ×2 模型 ×2 用例
        for model in (GEMINI, DSFLASH):
            client = self.make_client(model)
            for case, ocr_text, ref in GRADE_CASES:
                await self.call("grade", case, model,
                                lambda o=ocr_text, r=ref, c=case: client.grade_homework(
                                    o, r, subject="数学", task_meta={"eval_case": c}))
            await client.gateway.aclose()

        # variant ×2 模型
        v_case, q_text, kp, count = VARIANT_CASE
        for model in (DSFLASH, GEMINI):
            client = self.make_client(model)
            await self.call("variant", v_case, model,
                            lambda: client.generate_variant_questions(
                                q_text, kp, count=count, task_meta={"eval_case": v_case}))
            await client.gateway.aclose()

        # ocr ×2 模型 ×3 图
        for model in (GPT55, DSFLASH):
            client = self.make_client(model)
            for case, rel in OCR_IMAGES:
                img = os.path.join(self.exp_dir, rel)
                if not os.path.exists(img):
                    self.record({"feature": "ocr", "case": case, "model": model,
                                 "ok": False, "error": f"image missing: {rel}"})
                    continue
                await self.call("ocr", case, model,
                                lambda img=img: client.ocr_image(img, task_meta={"eval_case": f"ocr-{os.path.basename(img)}"}))
            await client.gateway.aclose()

        print("STATS " + json.dumps(self.stats, ensure_ascii=False), flush=True)


def main():
    exp_dir = os.environ.get("EXP_DIR", "/app/data/model_eval_20261102")
    log_root = os.environ.get("EVAL_LOG_ROOT", "/app/logs/model_eval_20261102")
    os.makedirs(exp_dir, exist_ok=True)
    # 图片复用 10 月的实验目录
    src = "/app/data/model_eval_20261015"
    for rel in ["homework_test.png", "images/B_hard_handwriting.png", "images/C_mixed_messy.png"]:
        dst = os.path.join(exp_dir, rel)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                import shutil
                shutil.copy(os.path.join(src, rel), dst)
            except OSError as e:
                print(f"[WARN] copy {rel}: {e}", flush=True)
    runner = Runner(exp_dir, log_root)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
