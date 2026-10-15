# -*- coding: utf-8 -*-
"""
模型选型对照实验主脚本（在 ai-teaching-backend 容器内运行）。

用法：
    python run_eval.py --exp-dir /opt/ai-teaching/model_eval_20261015

- API key 只从环境变量 LLM_API_KEY 读取，绝不打印；
- 每个候选模型单独建 LLMGateway（source="model_eval"），日志落到
  <log_root>/<时间戳>_model_eval_key<后4位>_<runid>/api_calls.jsonl；
- fallbacks 显式置空，避免主模型失败后自动切备用污染对照；
- 每次调用的返回原文另存 outputs/{feature}__{case}__{model}.txt 供人工复核；
- 失败不中断，记入 results_index.jsonl 后继续。
"""
import argparse
import asyncio
import json
import os
import sys
import time
import traceback

# 容器内 backend 即 /app；本地调试时把 backend 目录加进 sys.path
BACKEND_DIR = os.environ.get("BACKEND_DIR", "/app")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ai_client import AIClient  # noqa: E402
from llm import LLMConfig, LLMGateway  # noqa: E402

BASE_URL = os.environ.get("LLM_BASE_URL", "https://yibuapi.com/v1")

VISION_MODELS = [
    "gpt-5.5",
    "qwen3-vl-plus",
    "qwen3-vl-235b-a22b-instruct",
    "gemini-2.5-flash",
    "gpt-4o",
]

GRADE_MODELS = [
    "gemini-3.1-pro-preview",
    "deepseek-v4.1-flash",
    "deepseek-v4.1-pro",
    "gpt-5.2",
    "qwen3-235b-a22b-instruct-2507",
    "glm-4.6",
]

TEXT_MODELS_LP_VARIANT = GRADE_MODELS[:5]  # lessonplan / variant 各测 5 个

OCR_IMAGES = [
    ("A", "homework_test.png"),
    ("B", "images/B_hard_handwriting.png"),
    ("C", "images/C_mixed_messy.png"),
]

GRADE_CASES = [
    (
        "grade-1",
        "导数基础小测\n1. f'(x) = 2x + 1\n2. 切线方程 y = 3x - 2\n3. 极小值点 x = 2, f(2) = 1",
        "1. f'(x)=2x+1；2. y=3x-2；3. 极小值点 x=1, f(1)=-2",
    ),
    (
        "grade-2",
        "1. x=2 或 x=3\n2. y=3x-2\n3. log2 8 = 4\n4. f'(x)=3x^2\n5. （未作答）",
        "1. x=2, x=3；2. 3x-y-2=0；3. 3；4. 3x^2；5. 1/2",
    ),
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
            print("FATAL: 环境变量 LLM_API_KEY 未设置", file=sys.stderr)
            sys.exit(2)
        self.api_key = api_key
        self.stats = {"calls": 0, "ok": 0, "fail": 0}

    def make_client(self, model: str) -> AIClient:
        cfg = LLMConfig(
            api_key=self.api_key,
            base_url=BASE_URL,
            models={"default": model},
            fallbacks={},  # 关键：禁止自动切备用，保证对照纯净
            timeout=600,
            max_retries=1,
            log_root=self.log_root,
            log_request_content=True,
        )
        return AIClient(gateway=LLMGateway(cfg, source="model_eval"))

    def record(self, entry: dict):
        with open(self.index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save_output(self, feature: str, case: str, model: str, content) -> str:
        fname = f"{feature}__{case}__{safe_name(model)}.txt"
        path = os.path.join(self.outputs_dir, fname)
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return fname

    async def call(self, feature: str, case: str, model: str, coro_factory):
        """统一包裹一次调用：计时、捕获异常、存原文、记索引。"""
        entry = {"feature": feature, "case": case, "model": model, "ts": time.time()}
        self.stats["calls"] += 1
        try:
            result = await coro_factory()
            entry["ok"] = True
            entry["output_file"] = self.save_output(feature, case, model, result)
            entry["output_len"] = os.path.getsize(
                os.path.join(self.outputs_dir, entry["output_file"]))
            self.stats["ok"] += 1
        except Exception as e:  # noqa: BLE001
            entry["ok"] = False
            entry["error"] = f"{type(e).__name__}: {e}"[:500]
            self.stats["fail"] += 1
            print(f"[FAIL] {feature}/{case}/{model}: {entry['error']}", flush=True)
        self.record(entry)
        print(f"[{'OK' if entry['ok'] else 'ERR'}] {feature:10s} {case:8s} {model}", flush=True)

    async def run_smoke(self):
        """冒烟：1 次 OCR 调用，验证网关/日志/图片链路。"""
        model = "gpt-4o"
        client = self.make_client(model)
        img = os.path.join(self.exp_dir, "homework_test.png")
        await self.call("ocr", "smoke-A", model,
                        lambda: client.ocr_image(img, task_meta={"eval_case": "smoke"}))
        await client.gateway.aclose()
        print(json.dumps(self.stats, ensure_ascii=False))

    async def run(self):
        # ---------- OCR：视觉模型 × 3 图 ----------
        for model in VISION_MODELS:
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

        # ---------- grade：文本模型 × 2 用例 ----------
        for model in GRADE_MODELS:
            client = self.make_client(model)
            for case, ocr_text, ref in GRADE_CASES:
                await self.call("grade", case, model,
                                lambda o=ocr_text, r=ref, c=case: client.grade_homework(
                                    o, r, subject="数学", task_meta={"eval_case": c}))
            await client.gateway.aclose()

        # ---------- lessonplan：文本模型 × 1 用例 ----------
        lp_case, topic, period, level = LESSONPLAN_CASE
        for model in TEXT_MODELS_LP_VARIANT:
            client = self.make_client(model)
            await self.call("lessonplan", lp_case, model,
                            lambda: client.generate_lesson_plan(
                                topic, period=period, student_level=level,
                                task_meta={"eval_case": lp_case}))
            await client.gateway.aclose()

        # ---------- variant：文本模型 × 1 用例 ----------
        v_case, q_text, kp, count = VARIANT_CASE
        for model in TEXT_MODELS_LP_VARIANT:
            client = self.make_client(model)
            await self.call("variant", v_case, model,
                            lambda: client.generate_variant_questions(
                                q_text, kp, count=count, task_meta={"eval_case": v_case}))
            await client.gateway.aclose()

        print(json.dumps(self.stats, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-dir", required=True, help="实验目录（含图片与 outputs/）")
    ap.add_argument("--log-root", default="/opt/ai-teaching/logs/model_eval_20261015")
    ap.add_argument("--smoke", action="store_true", help="只跑 1 次 OCR 冒烟测试")
    args = ap.parse_args()
    os.makedirs(args.log_root, exist_ok=True)
    runner = Runner(args.exp_dir, args.log_root)
    try:
        asyncio.run(runner.run_smoke() if args.smoke else runner.run())
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
