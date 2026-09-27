"""班级管理：班级 / 学生 / 作业 CRUD 与统计"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

import class_service as cs
from auth import current_user
from database import get_db
from file_utils import get_extension
from models import HomeworkAssignment, HomeworkSubmission, User

router = APIRouter()


class ClassCreate(BaseModel):
    name: str
    subject: Optional[str] = "数学"
    grade: Optional[str] = "高三"


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None


class MemberCreate(BaseModel):
    name: str
    gender: Optional[str] = None
    student_no: Optional[str] = None


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    student_no: Optional[str] = None


class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    reference_answer: Optional[str] = ""
    subject: Optional[str] = None
    assign_date: Optional[str] = None
    deadline: Optional[str] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reference_answer: Optional[str] = None
    subject: Optional[str] = None
    assign_date: Optional[str] = None
    deadline: Optional[str] = None


async def _call(coro):
    """把服务层异常映射为 HTTP 状态码"""
    try:
        return await coro
    except cs.ClassNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except cs.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except cs.InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except cs.DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ==================== 班级 ====================

@router.get("/class/list")
async def list_classes(db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取班级列表"""
    return {"items": await cs.get_class_list(db, teacher_id=user.id)}


@router.post("/class")
async def create_class(body: ClassCreate, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """新建班级"""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="班级名称不能为空")
    return await cs.create_class(db, name[:100], body.subject, body.grade, teacher_id=user.id)


@router.get("/class/stats")
async def get_class_stats(class_slug: Optional[str] = None, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取班级统计信息（支持按班级筛选）"""
    empty = {"total_students": 0, "average_wrong_count": 0, "common_wrong_questions": []}
    query = (
        select(HomeworkSubmission)
        .where(HomeworkSubmission.grading_status == "已批改")
        .where(HomeworkSubmission.teacher_id == user.id)
    )
    if class_slug:
        cls = await _call(cs.get_class_record(db, class_slug, teacher_id=user.id))
        assignment_ids = [
            row[0] for row in (await db.execute(
                select(HomeworkAssignment.id).where(HomeworkAssignment.class_id == cls.id)
            )).all()
        ]
        if not assignment_ids:
            return empty
        query = query.where(HomeworkSubmission.assignment_id.in_(assignment_ids))

    submissions = [s for s in (await db.execute(query)).scalars().all() if cs.is_scored(s)]
    if not submissions:
        return empty

    total_students = len({s.member_id or s.student_name for s in submissions if s.member_id or s.student_name})
    total_wrong = sum(s.wrong_count or 0 for s in submissions)
    avg_wrong = total_wrong / len(submissions) if submissions else 0

    wrong_questions = {}
    for sub in submissions:
        try:
            grading = json.loads(sub.grading_result) if sub.grading_result else {}
        except (TypeError, ValueError):
            grading = {}
        for q in grading.get("questions", []) or []:
            if not q.get("is_correct", True):
                q_text = (q.get("question_text", "") or "")[:50]
                wrong_questions[q_text] = wrong_questions.get(q_text, 0) + 1

    common_wrong = sorted(wrong_questions.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "total_students": total_students,
        "average_wrong_count": round(avg_wrong, 1),
        "common_wrong_questions": [{"question": q, "count": c} for q, c in common_wrong],
    }


@router.get("/class/{class_slug}")
async def get_class_detail(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """班级详情"""
    return await _call(cs.get_class_detail(db, class_slug, teacher_id=user.id))


@router.put("/class/{class_slug}")
async def update_class(class_slug: str, body: ClassUpdate, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """编辑班级（名称 / 学科 / 年级）"""
    updates = body.model_dump(exclude_none=True)
    if "name" in updates:
        updates["name"] = updates["name"].strip()[:100]
        if not updates["name"]:
            raise HTTPException(status_code=400, detail="班级名称不能为空")
    return await _call(cs.update_class(db, class_slug, updates, teacher_id=user.id))


@router.delete("/class/{class_slug}")
async def delete_class(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """删除班级（连同学生、作业、作业提交）"""
    return await _call(cs.delete_class(db, class_slug, teacher_id=user.id))


# ==================== 学生 ====================

@router.get("/class/{class_slug}/members")
async def list_members(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """班级学生列表（含平均分、排名等作业统计）"""
    return {"items": await _call(cs.list_members(db, class_slug, teacher_id=user.id))}


@router.post("/class/{class_slug}/members")
async def add_member(class_slug: str, body: MemberCreate, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """添加学生"""
    return await _call(cs.add_member(db, class_slug, body.name, body.gender, body.student_no, teacher_id=user.id))


@router.post("/class/{class_slug}/members/import")
async def import_members(
    class_slug: str,
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    批量导入学生：上传 .txt / .csv 文件或直接提交文本，
    每行一个学生，格式「姓名[,性别][,学号]」。
    """
    content = text or ""
    if file is not None and file.filename:
        if get_extension(file.filename) not in ("txt", "csv"):
            raise HTTPException(status_code=400, detail="仅支持 .txt / .csv 格式的名单文件")
        raw = await file.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise HTTPException(status_code=413, detail="名单文件不能超过 1MB")
        for enc in ("utf-8-sig", "gbk"):
            try:
                content = content + "\n" + raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    if not content.strip():
        raise HTTPException(status_code=400, detail="请提供学生名单文本或文件")
    return await _call(cs.import_members(db, class_slug, content, teacher_id=user.id))


@router.put("/class/{class_slug}/members/{member_id}")
async def update_member(class_slug: str, member_id: int, body: MemberUpdate, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """编辑学生信息（改名会同步该班级作业提交记录上的姓名）"""
    return await _call(cs.update_member(db, class_slug, member_id, body.model_dump(exclude_none=True), teacher_id=user.id))


@router.delete("/class/{class_slug}/members/{member_id}")
async def delete_member(class_slug: str, member_id: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """移除学生（其历史提交记录保留）"""
    return await _call(cs.delete_member(db, class_slug, member_id, teacher_id=user.id))


# ==================== 作业 ====================

@router.get("/class/{class_slug}/homework")
async def list_class_homework(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取班级作业列表"""
    return {"items": await _call(cs.get_homework_list(db, class_slug, teacher_id=user.id))}


@router.post("/class/{class_slug}/homework")
async def create_class_homework(class_slug: str, body: AssignmentCreate, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """布置作业（可附参考答案，批改时自动使用）"""
    return await _call(cs.create_assignment(db, class_slug, body.model_dump(), teacher_id=user.id))


@router.get("/class/{class_slug}/homework-stats")
async def class_homework_stats(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取班级作业看板统计"""
    return await _call(cs.get_homework_stats(db, class_slug, teacher_id=user.id))


@router.get("/class/{class_slug}/grading-tasks")
async def class_grading_tasks(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取班级待批改任务"""
    return {"items": await _call(cs.get_grading_tasks(db, class_slug, teacher_id=user.id))}


@router.get("/class/{class_slug}/alert-students")
async def class_alert_students(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取预警学生"""
    return {"items": await _call(cs.get_alert_students(db, class_slug, teacher_id=user.id))}


@router.get("/class/{class_slug}/score-archive")
async def class_score_archive(class_slug: str, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """成绩档案：每份已批改作业的成绩统计"""
    return {"items": await _call(cs.get_score_archive(db, class_slug, teacher_id=user.id))}


@router.get("/class/{class_slug}/homework/{homework_id}")
async def get_class_homework_detail(class_slug: str, homework_id: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取班级作业详情"""
    homework = await _call(cs.get_homework_by_id(db, class_slug, homework_id, teacher_id=user.id))
    if not homework:
        raise HTTPException(status_code=404, detail="作业不存在")
    return homework


@router.put("/class/{class_slug}/homework/{homework_id}")
async def update_class_homework(
    class_slug: str, homework_id: int, body: AssignmentUpdate, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """编辑作业"""
    homework = await _call(cs.update_assignment(db, class_slug, homework_id, body.model_dump(exclude_none=True), teacher_id=user.id))
    if not homework:
        raise HTTPException(status_code=404, detail="作业不存在")
    return homework


@router.delete("/class/{class_slug}/homework/{homework_id}")
async def delete_class_homework(class_slug: str, homework_id: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """删除作业（连同所有提交记录）"""
    result = await _call(cs.delete_assignment(db, class_slug, homework_id, teacher_id=user.id))
    if not result:
        raise HTTPException(status_code=404, detail="作业不存在")
    return result


@router.get("/class/{class_slug}/homework/{homework_id}/submissions")
async def list_homework_submissions(class_slug: str, homework_id: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """获取作业学生提交列表"""
    return {"items": await _call(cs.get_student_submissions(db, class_slug, homework_id, teacher_id=user.id))}


@router.get("/class/{class_slug}/homework/{homework_id}/analysis")
async def homework_analysis(class_slug: str, homework_id: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """作业逐题正确率分析"""
    result = await _call(cs.get_homework_analysis(db, class_slug, homework_id, teacher_id=user.id))
    if result is None:
        raise HTTPException(status_code=404, detail="作业不存在")
    return result


@router.delete("/class/{class_slug}/homework/{homework_id}/submissions/pending")
async def delete_pending_submissions(class_slug: str, homework_id: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """批量删除待批改的作业提交记录"""
    assignment = await _call(cs.get_assignment_record(db, class_slug, homework_id, teacher_id=user.id))
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    result = await db.execute(
        delete(HomeworkSubmission)
        .where(HomeworkSubmission.assignment_id == assignment.id)
        .where(HomeworkSubmission.grading_status == "待批改")
    )
    await cs.update_assignment_status(db, assignment.id)
    await db.commit()
    return {
        "message": f"成功删除 {result.rowcount} 条待批改作业记录",
        "deleted_count": result.rowcount,
    }


@router.delete("/class/{class_slug}/homework/{homework_id}/submissions/keep-first/{keep_count}")
async def keep_first_n_submissions(
    class_slug: str, homework_id: int, keep_count: int, db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """保留前N条学生提交记录，删除其余所有记录"""
    assignment = await _call(cs.get_assignment_record(db, class_slug, homework_id, teacher_id=user.id))
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    keep_ids = [
        row[0] for row in (await db.execute(
            select(HomeworkSubmission.id)
            .where(HomeworkSubmission.assignment_id == assignment.id)
            .order_by(HomeworkSubmission.id)
            .limit(max(keep_count, 0))
        )).all()
    ]
    result = await db.execute(
        delete(HomeworkSubmission)
        .where(HomeworkSubmission.assignment_id == assignment.id)
        .where(HomeworkSubmission.id.not_in(keep_ids if keep_ids else [-1]))
    )
    await cs.update_assignment_status(db, assignment.id)
    await db.commit()
    return {
        "message": f"成功保留前 {keep_count} 条记录，删除 {result.rowcount} 条记录",
        "deleted_count": result.rowcount,
        "kept_count": keep_count,
    }
