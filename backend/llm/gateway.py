"""
统一的大模型调用网关（OpenAI 兼容接口，默认接 yibuapi.com）。

- 基于 openai.AsyncOpenAI，不阻塞 FastAPI 事件循环；
- 每次调用（成功或失败）都经 CallLogger 记一行日志，供 api_yibu_sumarize.py 统计；
- 按 feature（ocr / grade / lessonplan / variant ...）选择模型，便于分功能统计 token。
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import openai

from .call_logger import CallLogger, sanitize_messages, zero_usage


class LLMError(Exception):
    """模型调用失败（网络、鉴权、额度、超时等）。"""


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    models: Dict[str, str]
    timeout: float = 600.0
    max_retries: int = 1
    proxy_url: str = ""
    verify_ssl: bool = True
    log_root: str = "api_runs"
    log_request_content: bool = True
    extra_body: Dict[str, Any] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith(("your_", "sk-xxxx"))

    fallbacks: Dict[str, List[str]] = field(default_factory=dict)

    def model_for(self, feature: str) -> str:
        return self.models.get(feature) or self.models["default"]

    def model_chain(self, feature: str) -> List[str]:
        """主模型 + 备用模型（去重，保持顺序）。"""
        chain = [self.model_for(feature), *self.fallbacks.get(feature, [])]
        return list(dict.fromkeys(m for m in chain if m))


@dataclass
class LLMResult:
    content: str
    model: str
    usage: Dict[str, int]
    elapsed_seconds: float
    call_id: str
    finish_reason: Optional[str] = None


def extract_usage(response: Any) -> Dict[str, int]:
    """兼容 prompt/completion 与 input/output 两种 usage 字段。"""
    usage = getattr(response, "usage", None)
    rec = zero_usage()
    if usage is None:
        return rec

    prompt = getattr(usage, "prompt_tokens", None)
    if prompt is None:
        prompt = getattr(usage, "input_tokens", 0)
    completion = getattr(usage, "completion_tokens", None)
    if completion is None:
        completion = getattr(usage, "output_tokens", 0)
    total = getattr(usage, "total_tokens", None)
    if total is None:
        total = (prompt or 0) + (completion or 0)

    rec["prompt_tokens"] = int(prompt or 0)
    rec["completion_tokens"] = int(completion or 0)
    rec["total_tokens"] = int(total or 0)
    details = getattr(usage, "completion_tokens_details", None)
    if details is not None:
        rec["reasoning_tokens"] = int(getattr(details, "reasoning_tokens", 0) or 0)
    return rec


def _describe_error(e: Exception) -> str:
    if isinstance(e, openai.APITimeoutError):
        return "AI 模型响应超时，请重试或减少生成内容要求"
    if isinstance(e, openai.APIConnectionError):
        return "无法连接到 AI 模型服务，请检查网络或代理设置"
    if isinstance(e, openai.APIStatusError):
        return f"AI 模型请求失败：{e.status_code} - {str(e.message)[:200]}"
    return f"AI 模型调用失败：{type(e).__name__}: {e}"


class LLMGateway:
    def __init__(self, config: LLMConfig, source: str = "backend"):
        self.config = config
        self.logger = CallLogger(config.log_root, config.api_key, config.base_url, source=source)
        self._client: Optional[openai.AsyncOpenAI] = None

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def _get_client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            http_client = None
            if self.config.proxy_url or not self.config.verify_ssl:
                http_client = httpx.AsyncClient(
                    proxy=self.config.proxy_url or None,
                    verify=self.config.verify_ssl,
                    timeout=self.config.timeout,
                )
            self._client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
                http_client=http_client,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        feature: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        task_meta: Optional[Dict[str, Any]] = None,
    ) -> LLMResult:
        """
        调用 chat.completions。未指定 model 时按 feature 的主模型 → 备用模型依次尝试，
        每次尝试都单独记日志（失败的尝试也计入统计）；全部失败抛最后一个 LLMError。
        """
        if not self.enabled:
            raise LLMError("未配置有效的 AI API Key")

        chain = [model] if model else self.config.model_chain(feature)
        last_error: Optional[LLMError] = None
        for attempt, candidate in enumerate(chain):
            meta = dict(task_meta or {})
            if attempt:
                meta.update(attempt=attempt + 1, fallback_from=chain[0])
            try:
                return await self._chat_once(
                    messages, feature=feature, model=candidate, temperature=temperature,
                    max_tokens=max_tokens, task_meta=meta,
                )
            except LLMError as e:
                last_error = e
                if attempt + 1 < len(chain):
                    print(f"[llm] {feature} 调用 {candidate} 失败，改用 {chain[attempt + 1]}：{e}")
        raise last_error

    async def _chat_once(
        self,
        messages: List[Dict[str, Any]],
        *,
        feature: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        task_meta: Dict[str, Any],
    ) -> LLMResult:
        call_id = str(uuid.uuid4())
        task_id = f"{feature}-{call_id[:8]}"

        params: Dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if self.config.extra_body:
            params["extra_body"] = self.config.extra_body

        log_request = {**params, "messages": sanitize_messages(messages, self.config.log_request_content)}

        start = time.perf_counter()
        try:
            response = await self._get_client().chat.completions.create(**params)
        except Exception as e:  # noqa: BLE001
            elapsed = time.perf_counter() - start
            await self.logger.log_call(
                call_id=call_id, task_id=task_id, feature=feature, model=model,
                request=log_request, task_meta=task_meta or {}, success=False,
                elapsed=elapsed, usage=zero_usage(), content="", finish_reason=None,
                response_id=None, error={"type": type(e).__name__, "message": str(e)[:2000]},
            )
            raise LLMError(_describe_error(e)) from e

        elapsed = time.perf_counter() - start
        choice = response.choices[0] if response.choices else None
        content = (choice.message.content if choice and choice.message else "") or ""
        finish_reason = getattr(choice, "finish_reason", None)
        usage = extract_usage(response)

        await self.logger.log_call(
            call_id=call_id, task_id=task_id, feature=feature, model=model,
            request=log_request, task_meta=task_meta or {}, success=True,
            elapsed=elapsed, usage=usage,
            content=content if self.config.log_request_content else f"<{len(content)} chars>",
            finish_reason=finish_reason, response_id=getattr(response, "id", None), error=None,
        )
        return LLMResult(content=content, model=model, usage=usage, elapsed_seconds=elapsed,
                         call_id=call_id, finish_reason=finish_reason)
