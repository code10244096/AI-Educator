"""任务聚合：班级待批改任务 + 后台任务（批改 / 教案）状态"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import current_user
from class_service import get_all_grading_tasks
from database import get_db
from models import ClassInfo, HomeworkAssignment, HomeworkSubmission, LessonPlan, User

router = APIRouter()


@router.get("/tasks/all")
async def get_all_tasks(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    """聚合当前教师所有班级的批改任务"""
    return {"items": await get_all_grading_tasks(db, teacher_id=user.id)}


@router.get("/tasks/jobs")
async def get_background_jobs(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db),
                              user: User = Depends(current_user)):
    """当前教师最近的后台任务（作业批改 + 教案生成），按创建时间倒序"""
    subs = (await db.execute(
        select(HomeworkSubmission)
        .where(HomeworkSubmission.teacher_id == user.id)
        .where(or_(
            HomeworkSubmission.finished_at.is_not(None),
            HomeworkSubmission.status.in_(["queued", "processing", "failed"]),
        ))
        .order_by(HomeworkSubmission.id.desc())
        .limit(limit)
    )).scalars().all()
    plans = (await db.execute(
        select(LessonPlan).where(LessonPlan.teacher_id == user.id).order_by(LessonPlan.id.desc()).limit(limit)
    )).scalars().all()

    assignment_ids = {s.assignment_id for s in subs if s.assignment_id}
    assignments = {}
    if assignment_ids:
        rows = (await db.execute(
            select(HomeworkAssignment.id, HomeworkAssignment.title, HomeworkAssignment.class_id, ClassInfo.class_name)
            .join(ClassInfo, ClassInfo.id == HomeworkAssignment.class_id, isouter=True)
            .where(HomeworkAssignment.id.in_(assignment_ids))
        )).all()
        assignments = {r.id: r for r in rows}

    items = []
    for s in subs:
        a = assignments.get(s.assignment_id)
        student = s.student_name or "未填写姓名"
        title = f"批改：{a.title} · {student}" if a else f"临时批改 · {student}"
        items.append({
            "job_type": "grader",
            "id": s.id,
            "title": title,
            "status": s.status,
            "progress_stage": s.progress_stage,
            "error_message": s.error_message,
            "score": s.score,
            "student_name": s.student_name,
            "member_id": s.member_id,
            "assignment_id": s.assignment_id if a else None,
            "assignment_title": a.title if a else None,
            "class_id": a.class_id if a else None,
            "class_name": a.class_name if a else None,
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
