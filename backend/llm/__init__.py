"""大模型调用层：LLMGateway 负责调用，CallLogger 负责逐次记录用量。"""

import os
from pathlib import Path

from .gateway import LLMConfig, LLMError, LLMGateway, LLMResult

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_llm_config(raw: dict, legacy_ai: dict) -> LLMConfig:
    """
    读取 config.json 的 "llm" 段；没有时回退到旧的 "ai" 段。
    API Key 可用环境变量 LLM_API_KEY 覆盖，日志目录可用 API_OUTPUT_ROOT 覆盖。
    """
    if raw:
        models = dict(raw.get("models") or {})
        models.setdefault("default", raw.get("model") or "gpt-6-astra")
        api_key = raw.get("api_key", "")
        base_url = raw.get("base_url", "https://yibuapi.com/v1")
    else:
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

    log_root = os.getenv("API_OUTPUT_ROOT") or raw.get("log_root") or "api_runs"
    if not os.path.isabs(log_root):
        log_root = str(REPO_ROOT / log_root)

    return LLMConfig(
        api_key=os.getenv("LLM_API_KEY") or api_key,
        base_url=base_url,
        models={k: v for k, v in models.items() if v},
        timeout=float(raw.get("timeout", 600)),
        max_retries=int(raw.get("max_retries", 1)),
        proxy_url=raw.get("proxy_url", "") if raw.get("use_proxy") else "",
        verify_ssl=bool(raw.get("verify_ssl", True)),
        log_root=log_root,
        log_request_content=bool(raw.get("log_request_content", True)),
        extra_body=dict(raw.get("extra_body") or {}),
        fallbacks={k: [m for m in v if m] for k, v in (raw.get("fallbacks") or {}).items()},
    )


__all__ = ["LLMConfig", "LLMError", "LLMGateway", "LLMResult", "load_llm_config", "REPO_ROOT"]
