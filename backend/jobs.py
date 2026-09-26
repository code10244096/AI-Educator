"""
后台任务：作业批改（OCR + AI 批改）与教案生成。

真实模型单次调用需要 20-60 秒，多图批改可能要数分钟，因此接口只负责落库并立即返回，
实际工作在 asyncio 后台任务中进行（每个任务使用独立的数据库会话），前端轮询状态接口。
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import select

from ai_client import ai_client
from database import AsyncSessionLocal
from file_utils import OCR_CONCURRENCY, FileParseError, extract_text, get_extension
from llm import LLMError
from models import HomeworkAssignment, HomeworkSubmission, LessonPlan

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

def normalize_grading_result(result: dict) -> dict:
    """补全 score / wrong_count 等字段，保证前端展示与统计一致"""
    if not isinstance(result, dict):
        return {"error": "批改结果格式异常", "raw_result": str(result)}
    questions = result.get("questions")
    if isinstance(questions, list) and questions:
        total = len(questions)
        correct = sum(1 for q in questions if isinstance(q, dict) and q.get("is_correct"))
        result.setdefault("total_questions", total)
        result.setdefault("correct_count", correct)
        result.setdefault("wrong_count", total - correct)
        if result.get("score") is None:
            result["score"] = round(correct / total * 100) if total else 0
    for key in ("score", "wrong_count", "correct_count", "total_questions"):
        value = result.get(key)
        if isinstance(value, str):
            try:
                result[key] = float(value) if "." in value else int(value)
            except ValueError:
                result[key] = 0
    return result


# ==================== 作业批改 ====================

async def _set_stage(submission_id: int, stage: str) -> None:
    async with AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, submission_id)
        if sub and sub.status == "processing":
            sub.progress_stage = stage
            await db.commit()


async def _fail_submission(submission_id: int, message: str) -> None:
    from class_service import update_assignment_status

    async with AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, submission_id)
        if not sub:
            return
        sub.status = "failed"
        sub.grading_status = "待批改"
        sub.progress_stage = "批改失败"
        sub.error_message = message
        sub.finished_at = _now()
        if sub.assignment_id:
            await update_assignment_status(db, sub.assignment_id)
        await db.commit()


async def run_grading_job(submission_id: int, preset_text: Optional[str] = None) -> None:
    """后台执行：逐文件提取文本（图片并发 OCR）→ AI 批改 → 保存结果并同步错题本"""
    try:
        await _run_grading_job(submission_id, preset_text)
    except LLMError as e:
        await _fail_submission(submission_id, str(e))
    except FileParseError as e:
        await _fail_submission(submission_id, str(e))
    except asyncio.CancelledError:
        await _fail_submission(submission_id, INTERRUPTED_MESSAGE)
        raise
    except Exception as e:  # noqa: BLE001
        await _fail_submission(submission_id, f"批改出错：{type(e).__name__}: {e}")


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
                    task_meta={"submission_id": submission_id, "file_index": idx},
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

    # 2) AI 批改
    await _set_stage(submission_id, "批改中")
    grading_result = await ai_client.grade_homework(
        ocr_result=full_text,
        reference_answer=reference_answer,
        subject=subject,
        task_meta={"submission_id": submission_id},
    )
    grading_result = normalize_grading_result(grading_result)
    if grading_result.get("error"):
        async with AsyncSessionLocal() as db:
            sub = await db.get(HomeworkSubmission, submission_id)
            if sub:
                sub.grading_result = json.dumps(grading_result, ensure_ascii=False)
                await db.commit()
        raise FileParseError(f"{grading_result['error']}，请重试")

    # 3) 保存
    async with AsyncSessionLocal() as db:
        sub = await db.get(HomeworkSubmission, submission_id)
        if not sub:
            return
        sub.ocr_result = full_text
        sub.grading_result = json.dumps(grading_result, ensure_ascii=False)
        sub.wrong_count = grading_result.get("wrong_count", 0)
        sub.score = grading_result.get("score", 0)
        sub.status = "completed"
        sub.grading_status = "已批改"
        sub.progress_stage = "批改完成"
        sub.error_message = None
        sub.finished_at = _now()
        await db.flush()
        await sync_wrong_questions(db, grading_result, sub.student_name, subject, submission_id=sub.id)
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
            sub.grading_status = "待批改"
            sub.progress_stage = "批改失败"
            sub.error_message = INTERRUPTED_MESSAGE
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
