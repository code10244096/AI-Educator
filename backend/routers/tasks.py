"""任务聚合：班级待批改任务 + 后台任务（批改 / 教案）状态"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from class_service import get_all_grading_tasks
from database import get_db
from models import HomeworkSubmission, LessonPlan

router = APIRouter()


@router.get("/tasks/all")
async def get_all_tasks(db: AsyncSession = Depends(get_db)):
    """聚合所有班级的批改任务（供我的任务页使用）"""
    return {"items": await get_all_grading_tasks(db)}


@router.get("/tasks/jobs")
async def get_background_jobs(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    """最近的后台任务（作业批改 + 教案生成），按创建时间倒序"""
    subs = (await db.execute(
        select(HomeworkSubmission)
        .where(or_(
            HomeworkSubmission.finished_at.is_not(None),
            HomeworkSubmission.status.in_(["processing", "failed"]),
        ))
        .order_by(HomeworkSubmission.id.desc())
        .limit(limit)
    )).scalars().all()
    plans = (await db.execute(
        select(LessonPlan).order_by(LessonPlan.id.desc()).limit(limit)
    )).scalars().all()

    items = []
    for s in subs:
        items.append({
            "job_type": "grader",
            "id": s.id,
            "title": f"作业批改 - {s.student_name}" if s.student_name else f"作业批改 #{s.id}",
            "status": s.status,
            "progress_stage": s.progress_stage,
            "error_message": s.error_message,
            "score": s.score,
            "created_at": s.created_at,
        })
    for p in plans:
        items.append({
            "job_type": "lessonplan",
            "id": p.id,
            "title": f"生成《{p.title}》教案",
            "status": p.status or "completed",
            "progress_stage": p.progress_stage,
            "error_message": p.error_message,
            "created_at": p.created_at,
        })
    items.sort(key=lambda x: str(x["created_at"] or ""), reverse=True)
    return {"items": items[:limit]}
