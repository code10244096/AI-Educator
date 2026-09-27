"""大模型调用层：LLMGateway 负责调用，CallLogger 负责逐次记录用量。"""

import os
from pathlib import Path

from .gateway import LLMConfig, LLMError, LLMGateway, LLMResult

REPO_ROOT = Path(__file__).resolve().parents[2]

# 只用环境变量部署（没有 config.json）时的默认网关与分功能模型（2026-09 实测选型，见 config.example.json）
DEFAULT_BASE_URL = "https://yibuapi.com/v1"
DEFAULT_MODELS = {
    "default": "gpt-6-astra",
    "ocr": "gpt-6-astra",
    "grade": "gemini-3.1-pro-preview",
    "variant": "gpt-6-astra",
    "lessonplan": "gemini-3.1-pro-preview",
}
DEFAULT_FALLBACKS = {
    "ocr": ["gpt-5.5"],
    "grade": ["gpt-6-astra"],
    "variant": ["deepseek-v4-pro"],
    "lessonplan": ["deepseek-v4-pro"],
}
FEATURES = ("ocr", "grade", "variant", "lessonplan")


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def load_llm_config(raw: dict, legacy_ai: dict) -> LLMConfig:
    """
    读取 config.json 的 "llm" 段；没有时回退到旧的 "ai" 段；两者都没有时用内置默认值。
    环境变量优先：LLM_API_KEY、LLM_BASE_URL、LLM_MODEL（默认模型）、LLM_MODEL_OCR / _GRADE / _VARIANT / _LESSONPLAN、
    LLM_FALLBACK_<功能>（逗号分隔）、LLM_TIMEOUT、LLM_LOG_REQUEST_CONTENT；日志目录 API_OUTPUT_ROOT。
    """
    fallbacks = {}
    if raw:
        models = dict(raw.get("models") or {})
        models.setdefault("default", raw.get("model") or "gpt-6-astra")
        api_key = raw.get("api_key", "")
        base_url = raw.get("base_url", DEFAULT_BASE_URL)
        fallbacks = {k: [m for m in v if m] for k, v in (raw.get("fallbacks") or {}).items()}
    elif legacy_ai:
        models = {
            "default": legacy_ai.get("grader_model", "gpt-4"),
            "ocr": legacy_ai.get("ocr_model", ""),
            "grade": legacy_ai.get("grader_model", ""),
            "variant": legacy_ai.get("grader_model", ""),
            "lessonplan": legacy_ai.get("lessonplan_model", ""),
        }
        api_key = legacy_ai.get("api_key", "")
        base_url = legacy_ai.get("base_url", "https://api.openai.com/v1")
        raw = {}
    else:
        models = dict(DEFAULT_MODELS)
        api_key = ""
        base_url = DEFAULT_BASE_URL
        fallbacks = {k: list(v) for k, v in DEFAULT_FALLBACKS.items()}
        raw = {}

    # 环境变量覆盖
    if _env("LLM_BASE_URL"):
        base_url = _env("LLM_BASE_URL")
    if _env("LLM_MODEL"):
        models["default"] = _env("LLM_MODEL")
    for feature in FEATURES:
        model = _env(f"LLM_MODEL_{feature.upper()}")
        if model:
            models[feature] = model
        fb = os.getenv(f"LLM_FALLBACK_{feature.upper()}")
        if fb is not None:
            fallbacks[feature] = [m.strip() for m in fb.split(",") if m.strip()]
    timeout = float(_env("LLM_TIMEOUT") or raw.get("timeout", 600))
    log_content_env = _env("LLM_LOG_REQUEST_CONTENT").lower()
    log_request_content = (log_content_env in ("1", "true", "yes", "on")) if log_content_env else \
        bool(raw.get("log_request_content", True))

    log_root = os.getenv("API_OUTPUT_ROOT") or raw.get("log_root") or "api_runs"
    if not os.path.isabs(log_root):
        log_root = str(REPO_ROOT / log_root)

    return LLMConfig(
        api_key=os.getenv("LLM_API_KEY") or api_key,
        base_url=base_url,
        models={k: v for k, v in models.items() if v},
        timeout=timeout,
        max_retries=int(raw.get("max_retries", 1)),
        proxy_url=raw.get("proxy_url", "") if raw.get("use_proxy") else "",
        verify_ssl=bool(raw.get("verify_ssl", True)),
        log_root=log_root,
        log_request_content=log_request_content,
        extra_body=dict(raw.get("extra_body") or {}),
        fallbacks=fallbacks,
    )


__all__ = ["LLMConfig", "LLMError", "LLMGateway", "LLMResult", "load_llm_config", "REPO_ROOT"]
