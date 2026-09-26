"""错题本：录入错题、列表、标记掌握、变式题"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_client import ai_client
from database import get_db
from file_utils import FileParseError, extract_text, save_upload, validate_upload
from llm import LLMError
from models import WrongQuestion

router = APIRouter()


def _question_to_dict(q: WrongQuestion) -> dict:
    try:
        variants = json.loads(q.variant_questions) if q.variant_questions else []
    except (TypeError, ValueError):
        variants = []
    return {
        "id": q.id,
        "question_text": q.question_text,
        "user_answer": q.user_answer,
        "correct_answer": q.correct_answer,
        "knowledge_point": q.knowledge_point,
        "subject": q.subject,
        "error_date": q.error_date,
        "is_mastered": q.is_mastered,
        "variant_questions": variants,
        "student_name": q.student_name,
        "submission_id": q.submission_id,
        "source": q.source or "manual",
        "has_image": bool(q.image_path),
    }


@router.post("/notebook/upload")
async def upload_wrong_question(
    file: UploadFile = File(...),
    knowledge_point: str = Form(...),
    subject: str = Form("数学"),
    db: AsyncSession = Depends(get_db),
):
    """录入错题 - 支持图片、PDF、Word、TXT、MD 格式（图片会调用 AI 识别，并生成变式题）"""
    try:
        ext = validate_upload(file)
    except HTTPException:
        return {
            "error": "这个文件格式我不太认识呢，试试图片、PDF、Word、Markdown 或 TXT 文件吧~",
            "error_type": "invalid_format",
            "questions": [],
        }
    saved = await save_upload(file, ext)
    filepath = saved["path"]

    try:
        text_content = await extract_text(filepath, ext, task_meta={"feature_source": "notebook"})
    except LLMError:
        raise
    except FileParseError as e:
        return {"error": f"解析遇到了一点小麻烦：{e}", "error_type": "parse_failed", "questions": []}
    except Exception as e:  # noqa: BLE001
        return {"error": f"解析遇到了一点小麻烦：{e}", "error_type": "parse_failed", "questions": []}

    if not text_content or len(text_content.strip()) < 10:
        return {
            "error": "哎呀，这个文件好像有点'害羞'，什么都没解析出来呢~ 换个文件试试看？",
            "error_type": "empty",
            "questions": [],
        }

    question_text = text_content.split("答案")[0] if "答案" in text_content else text_content
    correct_answer = ""
    if "答案" in text_content:
        parts = text_content.split("答案", 1)
        if len(parts) > 1:
            correct_answer = parts[1].lstrip("：: \n")

    try:
        variant_questions = await ai_client.generate_variant_questions(
            question_text=question_text, knowledge_point=knowledge_point, count=3,
        )
    except Exception:  # noqa: BLE001  变式题失败不影响错题录入
        variant_questions = []

    wrong_question = WrongQuestion(
        user_id=1,
        question_text=question_text,
        user_answer="",
        correct_answer=correct_answer,
        knowledge_point=knowledge_point,
        subject=subject,
        variant_questions=json.dumps(variant_questions, ensure_ascii=False),
        image_path=filepath,
        source="manual",
    )
    db.add(wrong_question)
    await db.commit()
    await db.refresh(wrong_question)

    item = _question_to_dict(wrong_question)
    return {
        "id": wrong_question.id,
        "questions": [{**item, "image_path": filepath}],
        "knowledge_point": knowledge_point,
        "variant_questions": variant_questions,
        "image_path": filepath,
    }


@router.get("/notebook/list")
async def get_wrong_questions(
    knowledge_point: Optional[str] = None,
    subject: Optional[str] = None,
    is_mastered: Optional[bool] = None,
    student_name: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取错题列表（返回数组，按录入时间倒序）"""
    query = select(WrongQuestion)
    if knowledge_point:
        query = query.where(WrongQuestion.knowledge_point.like(f"%{knowledge_point}%"))
    if subject:
        query = query.where(WrongQuestion.subject == subject)
    if is_mastered is not None:
        query = query.where(WrongQuestion.is_mastered == is_mastered)
    if student_name:
        query = query.where(WrongQuestion.student_name == student_name)
    if source:
        query = query.where(WrongQuestion.source == source)
    query = query.order_by(WrongQuestion.error_date.desc(), WrongQuestion.id.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return [_question_to_dict(q) for q in result.scalars().all()]


@router.get("/notebook/stats")
async def get_notebook_stats(subject: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """错题本统计：总数 / 已掌握 / 知识点分布"""
    base = select(WrongQuestion)
    if subject:
        base = base.where(WrongQuestion.subject == subject)
    sub = base.subquery()
    total = await db.scalar(select(func.count()).select_from(sub)) or 0
    mastered = await db.scalar(
        select(func.count()).select_from(sub).where(sub.c.is_mastered.is_(True))
    ) or 0
    rows = (await db.execute(
        select(sub.c.knowledge_point, func.count()).group_by(sub.c.knowledge_point).order_by(func.count().desc())
    )).all()
    return {
        "total": total,
        "mastered": mastered,
        "unmastered": total - mastered,
        "knowledge_points": [{"name": kp or "未分类", "count": c} for kp, c in rows],
    }


async def _get_question(db: AsyncSession, question_id: int) -> WrongQuestion:
    q = await db.get(WrongQuestion, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="错题不存在")
    return q


@router.post("/notebook/{question_id}/mastered")
async def mark_as_mastered(question_id: int, db: AsyncSession = Depends(get_db)):
    """标记为已掌握"""
    q = await _get_question(db, question_id)
    q.is_mastered = True
    await db.commit()
    return {"message": "已标记为已掌握"}


@router.post("/notebook/{question_id}/unmastered")
async def mark_as_unmastered(question_id: int, db: AsyncSession = Depends(get_db)):
    """取消已掌握标记"""
    q = await _get_question(db, question_id)
    q.is_mastered = False
    await db.commit()
    return {"message": "已取消掌握标记"}


@router.post("/notebook/{question_id}/variants")
async def generate_variants(question_id: int, count: int = Form(3), db: AsyncSession = Depends(get_db)):
    """为错题（重新）生成变式题（同步调用 AI，约 20-60 秒）"""
    q = await _get_question(db, question_id)
    count = max(1, min(count, 5))
    variants = await ai_client.generate_variant_questions(
        question_text=q.question_text, knowledge_point=q.knowledge_point or "", count=count,
    )
    if not variants:
        raise HTTPException(status_code=502, detail="AI 未返回有效的变式题，请重试")
    q.variant_questions = json.dumps(variants, ensure_ascii=False)
    await db.commit()
    return {"id": q.id, "variant_questions": variants}


@router.delete("/notebook/{question_id}")
async def delete_wrong_question(question_id: int, db: AsyncSession = Depends(get_db)):
    """删除错题"""
    q = await _get_question(db, question_id)
    await db.delete(q)
    await db.commit()
    return {"message": "错题已删除", "id": question_id}
