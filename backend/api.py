from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import json
import os
from datetime import datetime
import aiofiles

from database import get_db, init_db
from models import (
    HomeworkAssignment, HomeworkSubmission, WrongQuestion,
    LessonPlan, User, ClassInfo
)
from ai_client import ai_client
from config import settings

router = APIRouter()


def ensure_upload_dir():
    """确保上传目录存在"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post("/grader/upload")
async def upload_homework(
    files: List[UploadFile] = File(...),
    reference_answer: Optional[str] = Form(None),
    subject: str = Form("数学"),
    db: AsyncSession = Depends(get_db)
):
    """上传作业图片并批改"""
    ensure_upload_dir()
    
    # 保存上传的图片
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_paths = []
    
    for idx, file in enumerate(files):
        filename = f"{timestamp}_{idx}_{file.filename}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        
        async with aiofiles.open(filepath, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        
        image_paths.append(filepath)
    
    # OCR 识别所有图片
    ocr_results = []
    for image_path in image_paths:
        try:
            ocr_text = await ai_client.ocr_image(image_path)
            ocr_results.append(ocr_text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR 识别失败：{str(e)}")
    
    # 合并 OCR 结果
    full_ocr_result = "\n\n".join(ocr_results)
    
    # 批改作业
    grading_result = await ai_client.grade_homework(
        ocr_result=full_ocr_result,
        reference_answer=reference_answer,
        subject=subject
    )
    
    # 创建作业提交记录
    submission = HomeworkSubmission(
        image_paths=json.dumps(image_paths),
        ocr_result=full_ocr_result,
        grading_result=json.dumps(grading_result, ensure_ascii=False),
        wrong_count=grading_result.get("wrong_count", 0),
        score=grading_result.get("score", 0),
        status="completed"
    )
    
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    
    return {
        "submission_id": submission.id,
        "ocr_result": full_ocr_result,
        "grading_result": grading_result,
        "image_count": len(image_paths)
    }


@router.get("/grader/{submission_id}")
async def get_grading_result(submission_id: int, db: AsyncSession = Depends(get_db)):
    """获取批改结果"""
    result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    
    return {
        "id": submission.id,
        "ocr_result": submission.ocr_result,
        "grading_result": json.loads(submission.grading_result),
        "wrong_count": submission.wrong_count,
        "score": submission.score,
        "status": submission.status,
        "created_at": submission.created_at
    }


@router.post("/notebook/upload")
async def upload_wrong_question(
    file: UploadFile = File(...),
    knowledge_point: str = Form(...),
    subject: str = Form("数学"),
    db: AsyncSession = Depends(get_db)
):
    """录入错题"""
    ensure_upload_dir()
    
    # 保存图片
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    
    async with aiofiles.open(filepath, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # OCR 识别
    try:
        ocr_result = await ai_client.ocr_image(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 识别失败：{str(e)}")
    
    # 解析题目和答案（简单分割）
    # 实际应用中应该用更智能的方式
    question_text = ocr_result.split("答案")[0] if "答案" in ocr_result else ocr_result
    user_answer = ""
    correct_answer = ""
    
    if "答案" in ocr_result:
        parts = ocr_result.split("答案")
        if len(parts) > 1:
            correct_answer = parts[1]
    
    # 生成变式题
    try:
        variant_questions = await ai_client.generate_variant_questions(
            question_text=question_text,
            knowledge_point=knowledge_point,
            count=3
        )
    except:
        variant_questions = []
    
    # 创建错题记录
    wrong_question = WrongQuestion(
        user_id=1,  # TODO: 从登录用户获取
        question_text=question_text,
        user_answer=user_answer,
        correct_answer=correct_answer,
        knowledge_point=knowledge_point,
        subject=subject,
        variant_questions=json.dumps(variant_questions, ensure_ascii=False),
        image_path=filepath
    )
    
    db.add(wrong_question)
    await db.commit()
    await db.refresh(wrong_question)
    
    return {
        "id": wrong_question.id,
        "question_text": question_text,
        "knowledge_point": knowledge_point,
        "variant_questions": variant_questions,
        "image_path": filepath
    }


@router.get("/notebook/list")
async def get_wrong_questions(
    knowledge_point: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """获取错题列表"""
    query = select(WrongQuestion)
    
    if knowledge_point:
        query = query.where(WrongQuestion.knowledge_point.like(f"%{knowledge_point}%"))
    if subject:
        query = query.where(WrongQuestion.subject == subject)
    
    query = query.order_by(WrongQuestion.error_date.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    questions = result.scalars().all()
    
    return [
        {
            "id": q.id,
            "question_text": q.question_text,
            "user_answer": q.user_answer,
            "correct_answer": q.correct_answer,
            "knowledge_point": q.knowledge_point,
            "subject": q.subject,
            "error_date": q.error_date,
            "is_mastered": q.is_mastered,
            "variant_questions": json.loads(q.variant_questions) if q.variant_questions else []
        }
        for q in questions
    ]


@router.post("/notebook/{question_id}/mastered")
async def mark_as_mastered(question_id: int, db: AsyncSession = Depends(get_db)):
    """标记为已掌握"""
    result = await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == question_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="错题不存在")
    
    question.is_mastered = True
    await db.commit()
    
    return {"message": "已标记为已掌握"}


@router.post("/lessonplan/generate")
async def generate_lesson_plan(
    title: str = Form(...),
    period: str = Form("1 课时"),
    student_level: str = Form("中等"),
    requirements: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """生成教案"""
    try:
        content = await ai_client.generate_lesson_plan(
            topic=title,
            period=period,
            student_level=student_level,
            requirements=requirements
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"教案生成失败：{str(e)}")
    
    # 保存教案
    lesson_plan = LessonPlan(
        teacher_id=1,  # TODO: 从登录用户获取
        title=title,
        period=period,
        student_level=student_level,
        requirements=requirements,
        content=content
    )
    
    db.add(lesson_plan)
    await db.commit()
    await db.refresh(lesson_plan)
    
    return {
        "id": lesson_plan.id,
        "title": lesson_plan.title,
        "content": content,
        "created_at": lesson_plan.created_at
    }


@router.get("/lessonplan/{plan_id}")
async def get_lesson_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """获取教案详情"""
    result = await db.execute(
        select(LessonPlan).where(LessonPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="教案不存在")
    
    return {
        "id": plan.id,
        "title": plan.title,
        "period": plan.period,
        "student_level": plan.student_level,
        "requirements": plan.requirements,
        "content": plan.content,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at
    }


@router.get("/class/stats")
async def get_class_stats(db: AsyncSession = Depends(get_db)):
    """获取班级统计信息"""
    # 获取所有作业提交
    result = await db.execute(select(HomeworkSubmission))
    submissions = result.scalars().all()
    
    if not submissions:
        return {
            "total_students": 0,
            "average_wrong_count": 0,
            "common_wrong_questions": []
        }
    
    # 计算统计信息
    total_students = len(set(s.user_id for s in submissions))
    total_wrong = sum(s.wrong_count or 0 for s in submissions)
    avg_wrong = total_wrong / len(submissions) if submissions else 0
    
    # 统计高频错题（简化版本）
    wrong_questions = {}
    for sub in submissions:
        grading = json.loads(sub.批改_result) if sub.批改_result else {}
        questions = grading.get("questions", [])
        for q in questions:
            if not q.get("is_correct", True):
                q_text = q.get("question_text", "")[:50]
                wrong_questions[q_text] = wrong_questions.get(q_text, 0) + 1
    
    # 排序取前 5
    common_wrong = sorted(
        wrong_questions.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    return {
        "total_students": total_students,
        "average_wrong_count": round(avg_wrong, 1),
        "common_wrong_questions": [
            {"question": q, "count": c}
            for q, c in common_wrong
        ]
    }


@router.on_event("startup")
async def startup_event():
    """启动时初始化数据库"""
    await init_db()
