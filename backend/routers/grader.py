"""作业批改：上传 → 后台 OCR + AI 批改 → 轮询结果"""
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import current_user
from class_service import class_slug, sync_wrong_questions, update_assignment_status  # noqa: F401
from config import settings
from database import get_db
from file_utils import IMAGE_EXTENSIONS, get_extension, save_uploads
from homework_dataset import DATASET_DIR, get_dataset_file_path, get_dataset_homework, list_dataset_homeworks
from jobs import run_grading_job, spawn
from models import ClassInfo, ClassMember, HomeworkAssignment, HomeworkSubmission, User, WrongQuestion

router = APIRouter()


def _loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


_EMPTY_CONTEXT = {"assignment_title": None, "class_id": None, "class_name": None, "class_slug": None,
                  "homework_id": None}


async def _assignment_context(db: AsyncSession, assignment_id: Optional[int]) -> dict:
    """批改记录所属的班级与作业（作业统一用主键；前端路由 /class/{class_id}/homework/{assignment_id}）"""
    if not assignment_id:
        return dict(_EMPTY_CONTEXT)
    a = await db.get(HomeworkAssignment, assignment_id)
    if not a:
        return dict(_EMPTY_CONTEXT)
    cls = await db.get(ClassInfo, a.class_id) if a.class_id else None
    return {
        "assignment_title": a.title,
        "class_id": a.class_id,
        "class_name": cls.class_name if cls else None,
        "class_slug": class_slug(a.class_id) if a.class_id else None,
        "homework_id": a.id,
    }


def _image_count(paths) -> int:
    """真正的图片张数（txt / md / docx / pdf 不算图片）"""
    return sum(1 for p in paths if get_extension(p) in IMAGE_EXTENSIONS)


def _submission_summary(sub: HomeworkSubmission) -> dict:
    names = _loads(sub.original_filenames, [])
    paths = _loads(sub.image_paths, [])
    return {
        "id": sub.id,
        "submission_id": sub.id,
        "assignment_id": sub.assignment_id,
        "student_name": sub.student_name,
        "subject": sub.subject,
        "status": sub.status,
        "grading_status": sub.grading_status,
        "progress_stage": sub.progress_stage,
        "error_message": sub.error_message,
        "score": sub.score,
        "wrong_count": sub.wrong_count,
        "file_names": names or [os.path.basename(p) for p in paths],
        "file_count": sub.file_count or len(paths),
        "image_count": _image_count(paths),
        "member_id": sub.member_id,
        "submit_time": sub.submit_time,
        "created_at": sub.created_at,
        "finished_at": sub.finished_at,
        "review_status": sub.review_status,
        "reviewed_at": sub.reviewed_at,
        "needs_review": bool(sub.needs_review),
        "teacher_modified": bool(sub.teacher_modified),
        "teacher_modified_at": sub.teacher_modified_at,
    }


async def _submission_detail(db: AsyncSession, sub: HomeworkSubmission) -> dict:
    return {
        **_submission_summary(sub),
        **(await _assignment_context(db, sub.assignment_id)),
        "ocr_result": sub.ocr_result,
        "grading_result": _loads(sub.grading_result, {}),
        "reference_answer": sub.reference_answer,
    }


async def _get_submission(db: AsyncSession, submission_id: int, teacher_id: int) -> HomeworkSubmission:
    """取当前教师的提交记录；不存在或属于其他教师一律 404（不暴露是否存在）"""
    sub = await db.get(HomeworkSubmission, submission_id)
    if not sub or sub.teacher_id != teacher_id:
        raise HTTPException(status_code=404, detail="提交记录不存在")
    return sub


def _mark_processing(sub: HomeworkSubmission) -> None:
    sub.status = "processing"
    sub.grading_status = "批改中"
    sub.progress_stage = "排队中"
    sub.error_message = None
    sub.finished_at = None


async def _prepare_submission(
    db: AsyncSession,
    *,
    submission_id: Optional[int],
    assignment_id: Optional[int],
    student_name: Optional[str],
    teacher_id: int,
    member_id: Optional[int] = None,
) -> Tuple[Optional[HomeworkSubmission], Optional[ClassMember]]:
    """
    校验参数，找到要复用的提交记录与对应学生：
    - member_id（推荐）：必须属于该作业所在班级；复用该学生在这次作业下的提交；
    - 只有 student_name：班里恰好一个同名学生时关联该学生；有同名学生时要求用 member_id 指定；
    - submission_id：覆盖重批指定的提交。
    """
    assignment = None
    if assignment_id:
        assignment = await db.get(HomeworkAssignment, assignment_id)
        if not assignment or assignment.teacher_id != teacher_id:
            raise HTTPException(status_code=404, detail="作业不存在")

    member = None
    if member_id:
        if not assignment:
            raise HTTPException(status_code=400, detail="请先选择作业，再指定学生")
        member = await db.get(ClassMember, member_id)
        if not member or member.class_id != assignment.class_id:
            raise HTTPException(status_code=400, detail="该学生不在这个作业所属的班级里")
    elif assignment and student_name:
        same = (await db.execute(
            select(ClassMember)
            .where(ClassMember.class_id == assignment.class_id, ClassMember.name == student_name)
        )).scalars().all()
        if len(same) > 1:
            raise HTTPException(status_code=400, detail=f"班里有 {len(same)} 名“{student_name}”，请按学号选择学生")
        member = same[0] if same else None

    sub = None
    if submission_id:
        sub = await _get_submission(db, submission_id, teacher_id)
    elif assignment and member:
        sub = (await db.execute(
            select(HomeworkSubmission)
            .where(HomeworkSubmission.assignment_id == assignment.id)
            .where(HomeworkSubmission.member_id == member.id)
            .order_by(HomeworkSubmission.id.desc())
            .limit(1)
        )).scalar_one_or_none()
        if sub is None:
            # 历史记录还没有关联学生：姓名在班里唯一时接管它
            sub = (await db.execute(
                select(HomeworkSubmission)
                .where(HomeworkSubmission.assignment_id == assignment.id)
                .where(HomeworkSubmission.member_id.is_(None))
                .where(HomeworkSubmission.student_name == member.name)
                .order_by(HomeworkSubmission.id.desc())
                .limit(1)
            )).scalar_one_or_none()
            if sub is not None:
                same_count = await db.scalar(
                    select(func.count(ClassMember.id))
                    .where(ClassMember.class_id == assignment.class_id, ClassMember.name == member.name)
                )
                if same_count != 1:
                    sub = None
    elif assignment and student_name:
        sub = (await db.execute(
            select(HomeworkSubmission)
            .where(HomeworkSubmission.assignment_id == assignment.id)
            .where(HomeworkSubmission.member_id.is_(None))
            .where(HomeworkSubmission.student_name == student_name)
            .order_by(HomeworkSubmission.id.desc())
            .limit(1)
        )).scalar_one_or_none()

    if sub and sub.status in ("processing", "queued"):
        raise HTTPException(status_code=409, detail="该作业正在批改中，请等待完成后再提交")
    return sub, member


async def _legacy_response(db: AsyncSession, sub: HomeworkSubmission, extra: Optional[dict] = None) -> dict:
    """与旧版同步接口兼容的返回结构（附带新的状态字段）"""
    await db.refresh(sub)
    data = {
        "submission_id": sub.id,
        "assignment_id": sub.assignment_id,
        "student_name": sub.student_name,
        "status": sub.status,
        "grading_status": sub.grading_status,
        "progress_stage": sub.progress_stage,
        "error_message": sub.error_message,
        "ocr_result": sub.ocr_result if sub.status == "completed" else None,
        "grading_result": _loads(sub.grading_result, None) if sub.status == "completed" else None,
        "image_count": _image_count(_loads(sub.image_paths, [])),
    }
    if extra:
        data.update(extra)
    return data


async def _run_or_spawn(db: AsyncSession, sub: HomeworkSubmission, wait: bool,
                        preset_text: Optional[str] = None, extra: Optional[dict] = None) -> dict:
    sub_id = sub.id
    teacher_id = sub.teacher_id
    if wait:
        await run_grading_job(sub_id, preset_text)
        db.expire_all()
        sub = await _get_submission(db, sub_id, teacher_id)
        if sub.status == "failed":
            raise HTTPException(status_code=502, detail=sub.error_message or "批改失败")
        return await _legacy_response(db, sub, extra)
    spawn(run_grading_job(sub_id, preset_text))
    return await _legacy_response(db, sub, extra)


@router.post("/grader/upload")
async def upload_homework(
    files: List[UploadFile] = File(...),
    reference_answer: Optional[str] = Form(None),
    subject: str = Form("数学"),
    assignment_id: Optional[int] = Form(None),
    submission_id: Optional[int] = Form(None),
    student_name: Optional[str] = Form(None),
    member_id: Optional[int] = Form(None),
    wait: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    上传作业文件并创建批改任务（支持图片、PDF、Word、TXT、MD）。
    默认立即返回 status=processing，前端轮询 GET /grader/{submission_id}；
    传 wait=true 时同步等待批改完成（兼容旧行为，仅建议测试使用）。
    """
    student_name = (student_name or "").strip()[:50] or None
    sub, member = await _prepare_submission(
        db, submission_id=submission_id, assignment_id=assignment_id, student_name=student_name,
        teacher_id=user.id, member_id=member_id,
    )
    if member is not None:
        student_name = member.name
    saved = await save_uploads(files)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    if sub is None:
        sub = HomeworkSubmission(
            assignment_id=assignment_id,
            teacher_id=user.id,
            member_id=member.id if member else None,
            student_name=student_name,
            is_test_data=False,
            submit_time=now_str,
        )
        db.add(sub)
    else:
        if assignment_id and not sub.assignment_id:
            sub.assignment_id = assignment_id
        if member is not None:
            sub.member_id = member.id
        if student_name:
            sub.student_name = student_name
        # 重新上传 / 重批：提交时间更新为本次上传时间（R1-005）
        sub.submit_time = now_str
        sub.is_test_data = False
        sub.dataset_file_id = None

    sub.image_paths = json.dumps([f["path"] for f in saved], ensure_ascii=False)
    sub.original_filenames = json.dumps([f["original_name"] for f in saved], ensure_ascii=False)
    sub.file_count = len(saved)
    sub.subject = subject or "数学"
    sub.reference_answer = reference_answer or None
    sub.ocr_result = None
    _mark_processing(sub)
    await db.flush()
    if sub.assignment_id:
        await update_assignment_status(db, sub.assignment_id)
    await db.commit()

    return await _run_or_spawn(db, sub, wait)


@router.get("/grader/submissions")
async def list_grading_submissions(
    status: Optional[str] = None,
    assignment_id: Optional[int] = None,
    student_name: Optional[str] = None,
    include_seed: bool = False,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """批改记录列表（默认只列出真正提交过批改任务的记录，不含演示种子数据）"""
    query = select(HomeworkSubmission).where(HomeworkSubmission.teacher_id == user.id)
    if not include_seed:
        query = query.where(or_(
            HomeworkSubmission.finished_at.is_not(None),
            HomeworkSubmission.status.in_(["processing", "failed"]),
        ))
    if status:
        query = query.where(HomeworkSubmission.status == status)
    if assignment_id:
        query = query.where(HomeworkSubmission.assignment_id == assignment_id)
    if student_name:
        query = query.where(HomeworkSubmission.student_name.like(f"%{student_name}%"))

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.execute(
        query.order_by(HomeworkSubmission.id.desc()).offset(offset).limit(limit)
    )).scalars().all()
    items = []
    for sub in rows:
        items.append({**_submission_summary(sub), **(await _assignment_context(db, sub.assignment_id))})
    return {"items": items, "total": total or 0}


@router.get("/grader/{submission_id}")
async def get_grading_result(submission_id: int, db: AsyncSession = Depends(get_db),
                             user: User = Depends(current_user)):
    """获取批改结果 / 批改任务状态（status: processing / completed / failed / pending）"""
    sub = await _get_submission(db, submission_id, user.id)
    return await _submission_detail(db, sub)


@router.post("/grader/{submission_id}/retry")
async def retry_grading(submission_id: int, wait: bool = Form(False), db: AsyncSession = Depends(get_db),
                        user: User = Depends(current_user)):
    """使用已保存的文件重新批改（适用于失败或需要重批的记录）"""
    sub = await _get_submission(db, submission_id, user.id)
    if sub.status == "processing":
        raise HTTPException(status_code=409, detail="该作业正在批改中")

    preset_text = None
    paths = _loads(sub.image_paths, [])
    if sub.is_test_data and sub.dataset_file_id:
        data = get_dataset_homework(file_id=sub.dataset_file_id)
        if not data:
            raise HTTPException(status_code=404, detail="测试作业不存在")
        preset_text = data["full_content"]
        if not sub.reference_answer:
            sub.reference_answer = data["reference_answer"]
    elif not paths or not all(os.path.isfile(p) for p in paths):
        raise HTTPException(status_code=400, detail="该记录没有可重新批改的文件，请重新上传")

    _mark_processing(sub)
    if sub.assignment_id:
        await update_assignment_status(db, sub.assignment_id)
    await db.commit()
    return await _run_or_spawn(db, sub, wait, preset_text)


@router.delete("/grader/{submission_id}")
async def delete_grading_submission(submission_id: int, db: AsyncSession = Depends(get_db),
                                    user: User = Depends(current_user)):
    """删除批改记录（同时删除由它同步到错题本的错题）"""
    sub = await _get_submission(db, submission_id, user.id)
    if sub.status == "processing":
        raise HTTPException(status_code=409, detail="该作业正在批改中，完成后才能删除")
    assignment_id = sub.assignment_id
    await db.execute(
        delete(WrongQuestion)
        .where(WrongQuestion.submission_id == sub.id)
        .where(WrongQuestion.source == "grading")
    )
    await db.delete(sub)
    await db.flush()
    if assignment_id:
        await update_assignment_status(db, assignment_id)
    await db.commit()
    return {"message": "批改记录已删除", "id": submission_id}


class QuestionJudgement(BaseModel):
    is_correct: Optional[bool] = None
    teacher_comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    review_status: str = "reviewed"


def _require_completed(sub: HomeworkSubmission) -> dict:
    if sub.status != "completed":
        raise HTTPException(status_code=409, detail="这份作业还没有批改完成，暂时不能改判或复核")
    result = _loads(sub.grading_result, {})
    if not isinstance(result, dict) or not result.get("questions"):
        raise HTTPException(status_code=409, detail="这份批改结果没有逐题信息，无法改判")
    return result


@router.patch("/grader/{submission_id}/questions/{question_number}")
async def judge_question(
    submission_id: int,
    question_number: str,
    body: QuestionJudgement,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    老师逐题改判（R1-008）：修改某题对错和/或老师批注；后端按逐题判定重新计算得分，
    同步错题本（判错→加入，判对→移除），记录 teacher_modified 与修改时间。
    """
    from class_service import sync_rejudged_question
    from jobs import compute_score

    sub = await _get_submission(db, submission_id, user.id)
    result = _require_completed(sub)
    questions = result["questions"]
    target = next((q for q in questions if str(q.get("question_number")) == str(question_number)), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"第 {question_number} 题不存在")
    if body.is_correct is None and body.teacher_comment is None:
        raise HTTPException(status_code=400, detail="请提供改判结果或批注")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    verdict_changed = False
    if body.is_correct is not None and bool(body.is_correct) != bool(target.get("is_correct")):
        if "ai_is_correct" not in target:
            target["ai_is_correct"] = bool(target.get("is_correct"))
        target["is_correct"] = bool(body.is_correct)
        target["teacher_modified"] = target["is_correct"] != target["ai_is_correct"]
        verdict_changed = True
    if body.teacher_comment is not None:
        comment = body.teacher_comment.strip()[:1000]
        target["teacher_comment"] = comment or None

    result.update(compute_score(questions))
    result["teacher_modified_count"] = sum(1 for q in questions if q.get("teacher_modified"))
    sub.grading_result = json.dumps(result, ensure_ascii=False)
    sub.score = result["score"]
    sub.wrong_count = result["wrong_count"]
    if verdict_changed:
        sub.teacher_modified = result["teacher_modified_count"] > 0
        sub.teacher_modified_at = now
        await sync_rejudged_question(db, sub, target)
    await db.flush()
    if sub.assignment_id:
        await update_assignment_status(db, sub.assignment_id)
    await db.commit()
    await db.refresh(sub)
    return await _submission_detail(db, sub)


@router.post("/grader/{submission_id}/review")
async def set_review_status(
    submission_id: int,
    body: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """标记复核状态：reviewed（已复核）/ pending_review（改回待复核）"""
    if body.review_status not in ("reviewed", "pending_review"):
        raise HTTPException(status_code=400, detail="复核状态只能是 reviewed 或 pending_review")
    sub = await _get_submission(db, submission_id, user.id)
    _require_completed(sub)
    sub.review_status = body.review_status
    sub.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None) if body.review_status == "reviewed" else None
    await db.commit()
    await db.refresh(sub)
    return await _submission_detail(db, sub)


@router.get("/grader/{submission_id}/files/{index}")
async def get_submission_file(submission_id: int, index: int, db: AsyncSession = Depends(get_db),
                              user: User = Depends(current_user)):
    """下载/预览提交的原始文件（只能由所属教师下载）"""
    sub = await _get_submission(db, submission_id, user.id)
    paths = _loads(sub.image_paths, [])
    if index < 0 or index >= len(paths):
        raise HTTPException(status_code=404, detail="文件不存在")
    path = os.path.realpath(paths[index])
    allowed_roots = [os.path.realpath(settings.UPLOAD_DIR), os.path.realpath(DATASET_DIR)]
    if not any(path.startswith(root + os.sep) or path == root for root in allowed_roots):
        raise HTTPException(status_code=403, detail="无权访问该文件")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文件已被删除")
    names = _loads(sub.original_filenames, [])
    filename = names[index] if index < len(names) else os.path.basename(path)
    return FileResponse(path, filename=filename)


# ==================== 开发用测试集（仅非生产环境注册，见 api.py） ====================

dataset_router = APIRouter()


@dataset_router.get("/homework/dataset")
async def get_homework_dataset_list():
    """获取 dataset 测试集作业列表"""
    items = list_dataset_homeworks()
    return {"items": items, "total": len(items)}


@dataset_router.get("/homework/dataset/{file_id}")
async def get_homework_dataset_detail(file_id: int):
    """获取 dataset 测试集作业详情（含学生作答与参考答案）"""
    data = get_dataset_homework(file_id=file_id)
    if not data:
        raise HTTPException(status_code=404, detail="测试作业不存在")
    return data


@dataset_router.post("/grader/upload-dataset/{file_id}")
async def upload_dataset_homework(
    file_id: int,
    subject: str = Form("数学"),
    assignment_id: Optional[int] = Form(None),
    submission_id: Optional[int] = Form(None),
    student_name: Optional[str] = Form(None),
    class_slug_value: Optional[str] = Form(None, alias="class_slug"),
    homework_id: Optional[int] = Form(None),
    wait: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """使用 dataset 测试集文件批改（后台任务；wait=true 时同步等待）"""
    from class_service import get_assignment_record

    data = get_dataset_homework(file_id=file_id)
    if not data:
        raise HTTPException(status_code=404, detail="测试作业不存在")
    filepath = get_dataset_file_path(data["filename"])
    if not filepath:
        raise HTTPException(status_code=404, detail="测试文件不存在")

    reference_answer = data["reference_answer"]
    if not assignment_id and class_slug_value and homework_id:
        try:
            assignment = await get_assignment_record(db, class_slug_value, homework_id, teacher_id=user.id)
        except ValueError:
            assignment = None
        if assignment:
            assignment_id = assignment.id
            if not reference_answer:
                reference_answer = assignment.reference_answer

    student_name = (student_name or "").strip() or None
    sub, member = await _prepare_submission(
        db, submission_id=submission_id, assignment_id=assignment_id, student_name=student_name,
        teacher_id=user.id,
    )
    if sub is None:
        sub = HomeworkSubmission(
            assignment_id=assignment_id,
            teacher_id=user.id,
            member_id=member.id if member else None,
            student_name=student_name or data["title"],
            submit_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        db.add(sub)
    else:
        if assignment_id and not sub.assignment_id:
            sub.assignment_id = assignment_id
        sub.student_name = student_name or sub.student_name or data["title"]

    sub.dataset_file_id = file_id
    sub.is_test_data = True
    sub.image_paths = json.dumps([filepath], ensure_ascii=False)
    sub.original_filenames = json.dumps([data["filename"]], ensure_ascii=False)
    sub.file_count = 1
    sub.subject = subject or "数学"
    sub.reference_answer = reference_answer or None
    sub.ocr_result = data["full_content"]
    _mark_processing(sub)
    await db.flush()
    if sub.assignment_id:
        await update_assignment_status(db, sub.assignment_id)
    await db.commit()

    return await _run_or_spawn(
        db, sub, wait, preset_text=data["full_content"],
        extra={"dataset_title": data["title"], "dataset_filename": data["filename"]},
    )
