"""
后台任务：作业批改（OCR + AI 批改）与教案生成。

真实模型单次调用需要 20-60 秒，多图批改可能要数分钟，因此接口只负责落库并立即返回，
实际工作在 asyncio 后台任务中进行（每个任务使用独立的数据库会话），前端轮询状态接口。
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import delete, select

from ai_client import ai_client
from database import AsyncSessionLocal
from file_utils import OCR_CONCURRENCY, FileParseError, extract_text, get_extension
from llm import LLMError
from models import HomeworkAssignment, HomeworkSubmission, LessonPlan

logger = logging.getLogger("aiedu.jobs")


class GradingFailed(Exception):
    """批改判定为失败（识别不到题目、结果无法解析等）：message 给老师看，detail 只写日志"""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


# 保存后台任务的强引用，避免被垃圾回收
_background_tasks: Set[asyncio.Task] = set()

INTERRUPTED_MESSAGE = "服务重启导致任务中断，请重新提交"


def spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def running_job_count() -> int:
    return len(_background_tasks)


async def wait_all_jobs(timeout: Optional[float] = None) -> None:
    """等待当前所有后台任务结束（测试/关闭时使用）"""
    if _background_tasks:
        await asyncio.wait(list(_background_tasks), timeout=timeout)


def _now() -> datetime:
    """与 SQLite CURRENT_TIMESTAMP 一致：不带时区的 UTC 时间"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ==================== 批改结果规范化 ====================

# 老师能看懂的失败原因（技术细节只写服务器日志）
MSG_NO_QUESTIONS = "未识别到题目，请检查照片是否清晰、是否拍到答题区域"
MSG_AI_UNAVAILABLE = "AI 服务暂时不可用，请稍后重试"
MSG_BAD_RESULT = "AI 批改结果无法解析，请重新批改"
MSG_UNEXPECTED = "批改出错了，请重新批改；如果反复失败请联系管理员"

_UNREADABLE_MARKS = re.compile(r"[［\[]\s*无法辨认\s*[］\]]|【文件\d+：[^】]*】")


def effective_text_length(text: str) -> int:
    """识别文本的有效字符数：去掉空白、“无法辨认”标记与多文件分隔标题"""
    cleaned = _UNREADABLE_MARKS.sub("", text or "")
    return len(re.sub(r"\s+", "", cleaned))


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "对", "正确", "是")
    return bool(value)


def compute_score(questions: list) -> Dict[str, float]:
    """统一计分口径（Q6）：score = 正确题数 / 总题数 × 100，保留 1 位小数；不采用模型自报的分数"""
    total = len(questions)
    correct = sum(1 for q in questions if q.get("is_correct"))
    score = round(correct / total * 100, 1) if total else 0
    return {"total_questions": total, "correct_count": correct, "wrong_count": total - correct, "score": score}


def normalize_grading_result(result: dict) -> dict:
    """
    规范化模型返回的批改结果：逐题补齐 is_correct / needs_review / reference_issue，
    并由后端按逐题判定重新计算 total_questions / correct_count / wrong_count / score。
    """
    if not isinstance(result, dict):
        return {"error": "批改结果格式异常", "raw_result": str(result)}
    questions = result.get("questions")
    if not isinstance(questions, list):
        questions = []
    cleaned = []
    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        q = dict(q)
        q["question_number"] = q.get("question_number") if q.get("question_number") not in (None, "") else idx + 1
        q["is_correct"] = _as_bool(q.get("is_correct"))
        q["needs_review"] = _as_bool(q.get("needs_review"))
        issue = q.get("reference_issue")
        q["reference_issue"] = issue.strip() if isinstance(issue, str) and issue.strip() and \
            issue.strip().lower() not in ("null", "none", "无") else None
        cleaned.append(q)
    result["questions"] = cleaned
    result.update(compute_score(cleaned))
    result["needs_review"] = any(q["needs_review"] for q in cleaned)
    return result


# ==================== 作业批改 ====================

async def _set_stage(submission_id: int, stage: str) -> None:
    async with AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, submission_id)
        if sub and sub.status == "processing":
            sub.progress_stage = stage
            await db.commit()


async def _fail_submission(submission_id: int, message: str) -> None:
    """标记失败：不写分数、不同步错题、不计入任何统计（R1-008）；失败原因是老师能看懂的中文"""
    from class_service import update_assignment_status
    from models import WrongQuestion

    async with AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, submission_id)
        if not sub:
            return
        sub.status = "failed"
        sub.grading_status = "批改失败"
        sub.progress_stage = "批改失败"
        sub.error_message = message
        sub.score = None
        sub.wrong_count = None
        sub.review_status = None
        sub.needs_review = False
        sub.teacher_modified = False
        sub.finished_at = _now()
        await db.execute(
            delete(WrongQuestion)
            .where(WrongQuestion.submission_id == submission_id)
            .where(WrongQuestion.source.in_(["grading", "teacher"]))
        )
        if sub.assignment_id:
            await update_assignment_status(db, sub.assignment_id)
        await db.commit()


async def run_grading_job(submission_id: int, preset_text: Optional[str] = None) -> None:
    """后台执行：逐文件提取文本（图片并发 OCR）→ AI 批改 → 保存结果并同步错题本"""
    try:
        await _run_grading_job(submission_id, preset_text)
    except LLMError as e:
        logger.warning("批改 %s 模型调用失败：%s", submission_id, e)
        await _fail_submission(submission_id, MSG_AI_UNAVAILABLE)
    except GradingFailed as e:
        logger.info("批改 %s 判定失败：%s", submission_id, e.detail or e.message)
        await _fail_submission(submission_id, e.message)
    except FileParseError as e:
        await _fail_submission(submission_id, str(e))
    except asyncio.CancelledError:
        await _fail_submission(submission_id, INTERRUPTED_MESSAGE)
        raise
    except Exception:  # noqa: BLE001
        logger.exception("批改 %s 出现未预期的错误", submission_id)
        await _fail_submission(submission_id, MSG_UNEXPECTED)


async def _run_grading_job(submission_id: int, preset_text: Optional[str] = None) -> None:
    from class_service import sync_wrong_questions, update_assignment_status

    async with AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, submission_id)
        if not sub:
            return
        file_paths: List[str] = json.loads(sub.image_paths or "[]")
        names: List[str] = json.loads(sub.original_filenames or "[]") or [os.path.basename(p) for p in file_paths]
        reference_answer = sub.reference_answer
        subject = sub.subject or "数学"
        teacher_id = sub.teacher_id
        if not reference_answer and sub.assignment_id:
            assignment = await db.get(HomeworkAssignment, sub.assignment_id)
            if assignment and assignment.reference_answer:
                reference_answer = assignment.reference_answer

    # 1) 识别 / 提取文本
    if preset_text:
        full_text = preset_text
    else:
        total = len(file_paths)
        done = 0
        sem = asyncio.Semaphore(OCR_CONCURRENCY)
        await _set_stage(submission_id, f"识别中 0/{total}")

        async def _one(idx: int, path: str) -> str:
            nonlocal done
            display = names[idx] if idx < len(names) else os.path.basename(path)
            try:
                text = await extract_text(
                    path, get_extension(path), semaphore=sem,
                    task_meta={"submission_id": submission_id, "file_index": idx, "teacher_id": teacher_id},
                )
            except FileParseError as e:
                text = f"[文件解析失败：{display}，{e}]"
            done += 1
            await _set_stage(submission_id, f"识别中 {done}/{total}")
            return text

        texts = await asyncio.gather(*[_one(i, p) for i, p in enumerate(file_paths)])
        useful = [t for t in texts if t and t.strip() and not t.startswith("[文件解析失败")]
        if not useful:
            failed = [t for t in texts if t.startswith("[文件解析失败")]
            raise FileParseError(failed[0][1:-1] if failed else "未能从上传的文件中识别出任何内容")
        if total > 1:
            full_text = "\n\n".join(
                f"【文件{i + 1}：{names[i] if i < len(names) else ''}】\n{t}" for i, t in enumerate(texts)
            )
        else:
            full_text = texts[0]

        async with AsyncSessionLocal() as db:
            sub = await db.get(HomeworkSubmission, submission_id)
            if sub:
                sub.ocr_result = full_text
                await db.commit()

    # 识别不到内容：直接判失败，不浪费一次批改调用
    if effective_text_length(full_text) < 10:
        raise GradingFailed(MSG_NO_QUESTIONS, f"识别文本有效字符不足 10 个：{full_text[:50]!r}")

    # 2) AI 批改
    await _set_stage(submission_id, "批改中")
    grading_result = await ai_client.grade_homework(
        ocr_result=full_text,
        reference_answer=reference_answer,
        subject=subject,
        task_meta={"submission_id": submission_id, "teacher_id": teacher_id},
    )
    if not isinstance(grading_result, dict) or grading_result.get("error"):
        raw = grading_result.get("raw_result") if isinstance(grading_result, dict) else grading_result
        raise GradingFailed(MSG_BAD_RESULT, f"批改结果解析失败：{str(raw)[:300]!r}")
    grading_result = normalize_grading_result(grading_result)
    if not grading_result.get("questions"):
        raise GradingFailed(MSG_NO_QUESTIONS, "批改结果没有任何题目")

    # 3) 保存
    async with AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, submission_id)
        if not sub:
            return
        sub.ocr_result = full_text
        sub.grading_result = json.dumps(grading_result, ensure_ascii=False)
        sub.wrong_count = grading_result["wrong_count"]
        sub.score = grading_result["score"]
        sub.status = "completed"
        sub.grading_status = "已批改"
        sub.progress_stage = "批改完成"
        sub.error_message = None
        sub.finished_at = _now()
        # 新结果：待老师复核，之前的改判记录随旧结果一起作废
        sub.review_status = "pending_review"
        sub.reviewed_at = None
        sub.needs_review = bool(grading_result.get("needs_review"))
        sub.teacher_modified = False
        sub.teacher_modified_at = None
        await db.flush()
        await sync_wrong_questions(db, grading_result, sub.student_name, subject,
                                   submission_id=sub.id, teacher_id=sub.teacher_id, member_id=sub.member_id)
        if sub.assignment_id:
            await update_assignment_status(db, sub.assignment_id)
        await db.commit()


# ==================== 教案生成 ====================

async def _fail_plan(plan_id: int, message: str) -> None:
    async with AsyncSessionLocal() as db:
        plan = await db.get(LessonPlan, plan_id)
        if plan:
            plan.status = "failed"
            plan.progress_stage = "生成失败"
            plan.error_message = message
            await db.commit()


async def _set_plan_stage(plan_id: int, stage: str) -> None:
    async with AsyncSessionLocal() as db:
        plan = await db.get(LessonPlan, plan_id)
        if plan and plan.status == "processing":
            plan.progress_stage = stage
            await db.commit()


async def run_lesson_plan_job(plan_id: int) -> None:
    try:
        await _run_lesson_plan_job(plan_id)
    except LLMError as e:
        await _fail_plan(plan_id, str(e))
    except asyncio.CancelledError:
        await _fail_plan(plan_id, INTERRUPTED_MESSAGE)
        raise
    except Exception as e:  # noqa: BLE001
        await _fail_plan(plan_id, f"教案生成失败：{type(e).__name__}: {e}")


async def retrieve_question_context(db, title: str) -> Dict:
    """从题库检索相关题目作为 RAG 上下文（失败不影响生成）"""
    try:
        from rag_retriever import QuestionRetriever

        retriever = QuestionRetriever()
        related = await retriever.keyword_search(
            db=db, keyword=title, subject="数学", education_level="高中", limit=8,
        )
        return {"context": retriever.format_for_rag(related), "count": len(related or [])}
    except Exception as e:  # noqa: BLE001
        print(f"题库检索失败: {e}")
        return {"context": "", "count": 0}


async def _run_lesson_plan_job(plan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        plan = await db.get(LessonPlan, plan_id)
        if not plan:
            return
        title, period, level, requirements = plan.title, plan.period, plan.student_level, plan.requirements or ""
        teacher_id = plan.teacher_id

    await _set_plan_stage(plan_id, "检索题库中")
    async with AsyncSessionLocal() as db:
        rag = await retrieve_question_context(db, title)

    await _set_plan_stage(plan_id, "AI 生成中")
    content = await ai_client.generate_lesson_plan(
        topic=title,
        period=period or "1 课时",
        student_level=level or "中等",
        requirements=requirements,
        question_bank_context=rag["context"],
        task_meta={"plan_id": plan_id, "teacher_id": teacher_id},
    )
    if not content or not content.strip():
        raise LLMError("AI 返回了空的教案内容，请重试")

    async with AsyncSessionLocal() as db:
        plan = await db.get(LessonPlan, plan_id)
        if not plan:
            return
        plan.content = content
        plan.status = "completed"
        plan.progress_stage = "生成完成"
        plan.error_message = None
        plan.retrieved_questions_count = rag["count"]
        await db.commit()


# ==================== 启动恢复 ====================

async def recover_interrupted_jobs() -> int:
    """服务启动时，把上次运行中断的任务标记为失败（它们不会再有后台协程推进）"""
    count = 0
    async with AsyncSessionLocal() as db:
        subs = (await db.execute(
            select(HomeworkSubmission).where(HomeworkSubmission.status == "processing")
        )).scalars().all()
        for sub in subs:
            sub.status = "failed"
            sub.grading_status = "批改失败"
            sub.progress_stage = "批改失败"
            sub.error_message = INTERRUPTED_MESSAGE
            sub.score = None
            sub.wrong_count = None
            count += 1
        plans = (await db.execute(
            select(LessonPlan).where(LessonPlan.status == "processing")
        )).scalars().all()
        for plan in plans:
            plan.status = "failed"
            plan.progress_stage = "生成失败"
            plan.error_message = INTERRUPTED_MESSAGE
            count += 1
        await db.commit()
    return count
