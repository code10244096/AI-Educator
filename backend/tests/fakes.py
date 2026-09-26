"""Test doubles shared by the pytest suite and the subprocess runner.

FakeGateway mimics llm.LLMGateway.chat() so tests can assert which features
were called with what messages, and can force failures, without network.
"""
import copy
import json
import uuid
from typing import Any, Dict, List, Optional

from llm import LLMError, LLMResult

FAKE_WRONG_MARKER = "FAKE_WRONG_QUESTION_MARKER"

DEFAULT_GRADE = {
    "total_questions": 3,
    "correct_count": 2,
    "wrong_count": 1,
    "score": 67,
    "questions": [
        {"question_number": 1, "question_text": "1+1=?", "student_answer": "2",
         "correct_answer": "2", "is_correct": True, "explanation": "ok"},
        {"question_number": 2, "question_text": f"{FAKE_WRONG_MARKER} 2+2=?", "student_answer": "5",
         "correct_answer": "4", "is_correct": False, "explanation": "wrong"},
        {"question_number": 3, "question_text": "3+3=?", "student_answer": "6",
         "correct_answer": "6", "is_correct": True, "explanation": "ok"},
    ],
}

DEFAULT_OCR = "### 1. 填空题\n1+1=?\n\n**学生答案**：2\n"
DEFAULT_VARIANTS = [
    {"variant_number": 1, "question_text": "变式1", "answer": "1", "difficulty": "easy"},
]
DEFAULT_LESSONPLAN = "# 测试教案\n\n## 教学目标\n- fake lesson plan content\n"


class FakeGateway:
    """Drop-in replacement for LLMGateway (only the surface AIClient uses)."""

    enabled = True

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.fail_features: set = set()
        self.fail_message = "fake upstream failure (quota exhausted)"
        self.responses: Dict[str, str] = {}
        self.grade_result: Dict[str, Any] = copy.deepcopy(DEFAULT_GRADE)
        self.config = None
        self.delay = 0.0  # seconds to sleep per call (lets tests observe "processing")

    def features(self) -> List[str]:
        return [c["feature"] for c in self.calls]

    def _content_for(self, feature: str) -> str:
        if feature in self.responses:
            return self.responses[feature]
        if feature == "ocr":
            return DEFAULT_OCR
        if feature in ("grade", "seed_grade"):
            return "```json\n" + json.dumps(self.grade_result, ensure_ascii=False) + "\n```"
        if feature == "variant":
            return json.dumps(DEFAULT_VARIANTS, ensure_ascii=False)
        if feature == "lessonplan":
            return DEFAULT_LESSONPLAN
        return "ok"

    async def chat(self, messages, *, feature: str, model: Optional[str] = None,
                   temperature: float = 0.7, max_tokens: Optional[int] = None,
                   task_meta: Optional[Dict[str, Any]] = None, **kwargs) -> LLMResult:
        self.calls.append({"feature": feature, "messages": copy.deepcopy(messages),
                           "task_meta": dict(task_meta or {}), "kwargs": kwargs})
        if self.delay:
            import asyncio
            await asyncio.sleep(self.delay)
        if feature in self.fail_features or "*" in self.fail_features:
            raise LLMError(self.fail_message)
        content = self._content_for(feature)
        return LLMResult(
            content=content, model="fake-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "reasoning_tokens": 0},
            elapsed_seconds=0.001, call_id=str(uuid.uuid4()), finish_reason="stop",
        )

    async def aclose(self) -> None:  # pragma: no cover
        return None


def prompt_text(call: Dict[str, Any]) -> str:
    """Flatten a recorded call's messages to text for assertions."""
    out = []
    for m in call["messages"]:
        c = m.get("content")
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            for part in c:
                if part.get("type") == "text":
                    out.append(part.get("text", ""))
                elif part.get("type") == "image_url":
                    out.append("[image_url:" + (part.get("image_url") or {}).get("url", "")[:40] + "]")
    return "\n".join(out)


def install_gateway(gateway) -> tuple:
    """Swap the global ai_client's gateway; returns the previous state for restore."""
    import ai_client as ai_mod
    client = ai_mod.ai_client
    prev = (client.gateway, getattr(client, "is_debug_mode", None))
    client.gateway = gateway
    if hasattr(client, "is_debug_mode"):
        client.is_debug_mode = not getattr(gateway, "enabled", True)
    return prev


def restore_gateway(prev: tuple) -> None:
    import ai_client as ai_mod
    client = ai_mod.ai_client
    client.gateway = prev[0]
    if prev[1] is not None:
        client.is_debug_mode = prev[1]
