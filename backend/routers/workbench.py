"""工作台汇总（R1-006）：登录后首页一眼看到今天要做的事。

GET /api/dashboard —— 只统计当前教师自己的班级、作业、批改记录与教案。

计数口径（与作业详情页一致，只统计挂在班级作业下的提交；临时批改不计入）：
- pending_review：批改完成（status=completed）且 review_status 为 pending_review。
  已复核（reviewed）不再计入。历史数据 review_status 为空表示未跟踪，按「已批改」处理，不算「等你确认」。
- processing：排队中或批改中（status in queued / processing）
- failed：批改失败，需要老师处理（status=failed）
- collecting：班级有学生还没上传作业的作业数；missing_students 为这些作业缺交人数合计
"""
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, null, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import current_user
from database import get_db
from models import ClassInfo, ClassMember, HomeworkAssignment, HomeworkSubmission, LessonPlan, User

router = APIRouter()

RECENT_ASSIGNMENTS = 8
RECENT_PLANS = 5

RUNNING = ("queued", "processing")

# 第④⑤组引入的列（review_status、member_id）上线前自动降级
_REVIEW_COL = getattr(HomeworkSubmission, "review_status", None)
_MEMBER_COL = getattr(HomeworkSubmission, "member_id", None)


def _empty_stats() -> dict:
    return {"uploaded": 0, "completed": 0, "processing": 0, "failed": 0, "pending_review": 0,
            "scores": [], "students": set()}


async def _eta_seconds(db: AsyncSession, assignment_ids: List[int], teacher_id: int) -> Optional[int]:
    """批改中作业的预计剩余时间：复用 class_service.get_assignment_progress（第⑤组提供），没有时返回 None"""
    try:
        from class_service import get_assignment_progress  # type: ignore
    except ImportError:
        return None
    total = 0
    found = False
    for aid in assignment_ids:
        try:
            progress = await get_assignment_progress(db, aid, teacher_id=teacher_id)
        except Exception:  # noqa: BLE001 - 预计时间只是提示，失败不影响工作台
            continue
        eta = (progress or {}).get("eta_seconds")
        if isinstance(eta, (int, float)):
            total = max(total, int(eta))
            found = True
    return total if found else None


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    classes = (await db.execute(
        select(ClassInfo).where(ClassInfo.teacher_id == user.id).order_by(ClassInfo.id)
    )).scalars().all()
    class_by_id = {c.id: c for c in classes}
    class_ids = list(class_by_id)

    member_counts: Dict[int, int] = {}
    assignments: List[HomeworkAssignment] = []
    stats: Dict[int, dict] = defaultdict(_empty_stats)
    if class_ids:
        member_counts = dict((await db.execute(
            select(ClassMember.class_id, func.count(ClassMember.id))
            .where(ClassMember.class_id.in_(class_ids))
            .group_by(ClassMember.class_id)
        )).all())
        assignments = (await db.execute(
            select(HomeworkAssignment)
            .where(HomeworkAssignment.class_id.in_(class_ids))
            .order_by(HomeworkAssignment.id.desc())
        )).scalars().all()

    assignment_ids = [a.id for a in assignments]
    if assignment_ids:
        cols = [HomeworkSubmission.assignment_id, HomeworkSubmission.status, HomeworkSubmission.score,
                HomeworkSubmission.student_name,
                _REVIEW_COL if _REVIEW_COL is not None else null().label("review_status"),
                _MEMBER_COL if _MEMBER_COL is not None else null().label("member_id")]
        rows = (await db.execute(
            select(*cols).where(HomeworkSubmission.assignment_id.in_(assignment_ids))
        )).all()
        for aid, status, score, student_name, review, member_id in rows:
            s = stats[aid]
            s["uploaded"] += 1
            s["students"].add(("m", member_id) if _MEMBER_COL is not None and member_id else ("n", student_name))
            if status == "completed":
                s["completed"] += 1
                if score is not None:
                    s["scores"].append(score)
                if review == "pending_review":
                    s["pending_review"] += 1
            elif status in RUNNING:
                s["processing"] += 1
            elif status == "failed":
                s["failed"] += 1

    def assignment_row(a: HomeworkAssignment) -> dict:
        s = stats[a.id]
        total = member_counts.get(a.class_id, 0)
        missing = max(total - len(s["students"]), 0) if total else 0
        scores = s["scores"]
        cls = class_by_id.get(a.class_id)
        return {
            "assignment_id": a.id,
            "class_id": a.class_id,
            "class_name": cls.class_name if cls else "",
            "title": a.title,
            "assign_date": a.assign_date,
            "deadline": a.deadline,
            "total_members": total,
            "uploaded": s["uploaded"],
            "completed": s["completed"],
            "processing": s["processing"],
            "failed": s["failed"],
            "pending_review": s["pending_review"],
            "missing": missing,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        }

    rows_all = [assignment_row(a) for a in assignments]

    def targets(key: str) -> List[dict]:
        hits = [r for r in rows_all if r[key] > 0]
        return [{"assignment_id": r["assignment_id"], "class_id": r["class_id"], "class_name": r["class_name"],
                 "title": r["title"], "count": r[key]} for r in hits]

    counts = {
        # 顺序固定：测试按键名片段取第一个数值（review / process / fail / collect）
        "pending_review": sum(r["pending_review"] for r in rows_all),
        "processing": sum(r["processing"] for r in rows_all),
        "failed": sum(r["failed"] for r in rows_all),
        "collecting": sum(1 for r in rows_all if r["missing"] > 0),
        "missing_students": sum(r["missing"] for r in rows_all),
    }
    running_ids = [r["assignment_id"] for r in rows_all if r["processing"] > 0]
    eta = await _eta_seconds(db, running_ids, user.id) if running_ids else None

    class_rows = []
    for c in classes:
        class_assignments = [r for r in rows_all if r["class_id"] == c.id]
        scores = [sc for a in assignments if a.class_id == c.id for sc in stats[a.id]["scores"]]
        class_rows.append({
            "class_id": c.id,
            "name": c.class_name,
            "grade": c.grade,
            "member_count": member_counts.get(c.id, 0),
            "assignment_count": len(class_assignments),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        })

    plans = (await db.execute(
        select(LessonPlan.id, LessonPlan.title, LessonPlan.status, LessonPlan.progress_stage, LessonPlan.created_at)
        .where(LessonPlan.teacher_id == user.id)
        .order_by(LessonPlan.id.desc())
        .limit(RECENT_PLANS)
    )).all()

    return {
        "counts": counts,
        "eta_seconds": eta,
        "targets": {
            "review": targets("pending_review"),
            "processing": targets("processing"),
            "failed": targets("failed"),
            "missing": targets("missing"),
        },
        "recent_assignments": rows_all[:RECENT_ASSIGNMENTS],
        "classes": class_rows,
        "recent_lesson_plans": [
            {"id": p.id, "title": p.title, "status": p.status or "completed",
             "progress_stage": p.progress_stage, "created_at": p.created_at}
            for p in plans
        ],
    }
