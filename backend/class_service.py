"""班级作业管理服务：班级/学生/作业 CRUD、种子数据、统计与任务聚合"""
import json
import re
from typing import Dict, List, Optional

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import ClassInfo, ClassMember, HomeworkAssignment, HomeworkSubmission, User, WrongQuestion
from homework_dataset import list_dataset_homeworks, get_dataset_homework

# 兼容旧代码：历史上固定的三个班级 slug
CLASS_SLUGS = {1: "class1", 2: "class2", 3: "class3"}
SLUG_TO_ID = {v: k for k, v in CLASS_SLUGS.items()}

PASS_SCORE = 60


class ClassNotFoundError(ValueError):
    """班级不存在（继承 ValueError 以兼容旧的 except ValueError -> 404 逻辑）"""


class InvalidInputError(Exception):
    """参数校验失败（-> 400）"""


class DuplicateError(Exception):
    """重复数据（-> 409）"""


class NotFoundError(Exception):
    """班级内的资源不存在（-> 404）"""

STUDENT_NAMES = [
    "张三", "李四", "王五", "赵六", "孙七", "周八", "吴九", "郑十",
    "陈一", "刘二", "杨三", "黄四", "林五", "何六", "高七", "马八",
    "罗九", "梁十", "宋一", "唐二", "许三", "韩四", "冯五", "邓六",
    "曹七", "彭八", "曾九", "萧十", "田一", "董二", "袁三", "潘四",
    "于五", "蒋六", "蔡七", "余八", "杜九", "叶十", "程一", "苏二",
    "魏三", "吕四", "丁五", "任六", "沈七",
]

DATASET_HOMEWORK_META = [
    {"id": 10, "title": "高考数学作业集10", "date": "2024-01-18", "status": "待批改", "submitted": 38, "avgScore": 0},
    {"id": 9, "title": "高考数学作业集9", "date": "2024-01-15", "status": "已批改", "submitted": 42, "avgScore": 90},
    {"id": 8, "title": "高考数学作业集8", "date": "2024-01-12", "status": "已批改", "submitted": 45, "avgScore": 85},
    {"id": 7, "title": "高考数学作业集7", "date": "2024-01-10", "status": "已批改", "submitted": 44, "avgScore": 78},
    {"id": 6, "title": "高考数学作业集6", "date": "2024-01-08", "status": "已批改", "submitted": 43, "avgScore": 82},
    {"id": 5, "title": "高考数学作业集5", "date": "2024-01-05", "status": "已批改", "submitted": 45, "avgScore": 88},
    {"id": 4, "title": "高考数学作业集4", "date": "2024-01-03", "status": "已批改", "submitted": 45, "avgScore": 86},
    {"id": 3, "title": "高考数学作业集3", "date": "2024-01-01", "status": "已批改", "submitted": 44, "avgScore": 80},
    {"id": 2, "title": "高考数学作业集2", "date": "2023-12-28", "status": "已批改", "submitted": 45, "avgScore": 84},
    {"id": 1, "title": "高考数学作业集1", "date": "2023-12-25", "status": "已批改", "submitted": 45, "avgScore": 87},
]

CLASS2_HOMEWORK = [
    {"id": 1, "title": "函数与导数综合", "date": "2024-01-14", "deadline": "2024-01-15", "submitted": 40, "total": 42, "avgScore": 76.3, "status": "已批改", "description": "函数性质与导数应用综合练习"},
    {"id": 2, "title": "解析几何专项", "date": "2024-01-10", "deadline": "2024-01-11", "submitted": 38, "total": 42, "avgScore": 0, "status": "待批改", "description": "直线、圆与圆锥曲线综合"},
]

CLASS3_HOMEWORK = [
    {"id": 1, "title": "不等式证明练习", "date": "2024-01-13", "deadline": "2024-01-14", "submitted": 35, "total": 40, "avgScore": 74.5, "status": "已批改", "description": "基本不等式与证明方法训练"},
]


# ==================== 班级标识 ====================

def class_slug(class_id: int) -> str:
    return f"class{class_id}"


def resolve_class_id(class_slug_or_id) -> int:
    """把 'class3' / '3' 解析为班级 ID（不校验是否存在）"""
    value = str(class_slug_or_id).strip()
    match = re.fullmatch(r"(?:class)?(\d+)", value)
    if not match:
        raise ClassNotFoundError("班级不存在")
    return int(match.group(1))


async def get_class_record(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> ClassInfo:
    """按 ID（或旧的 classN 写法）取当前教师的班级；不存在或不属于该教师时一律抛 ClassNotFoundError（-> 404）"""
    class_id = resolve_class_id(class_slug_value)
    cls = await db.get(ClassInfo, class_id)
    if not cls or cls.teacher_id != teacher_id:
        raise ClassNotFoundError("班级不存在")
    return cls


async def _class_members(db: AsyncSession, class_id: int) -> List[ClassMember]:
    result = await db.execute(
        select(ClassMember)
        .where(ClassMember.class_id == class_id)
        .order_by(ClassMember.order_index, ClassMember.id)
    )
    return list(result.scalars().all())


async def _member_count(db: AsyncSession, class_id: int) -> int:
    return await db.scalar(
        select(func.count(ClassMember.id)).where(ClassMember.class_id == class_id)
    ) or 0


# ==================== 种子数据 ====================

async def seed_initial_data(db: AsyncSession) -> None:
    """
    初始化演示用的班级、学生与作业数据（仅首次、幂等）。
    只要库里已有用户或班级就跳过，因此用户删光班级后重启也不会被重新灌入。
    种子数据全部是静态的，不调用 AI。
    """
    from config import settings

    # 演示数据只在开发环境显式开启 SEED_DEMO_DATA=true 时播种；生产强制关闭（R1-005 / L-S08）
    if not settings.SEED_DEMO_DATA:
        return
    has_user = (await db.execute(select(User.id).limit(1))).first()
    has_class = (await db.execute(select(ClassInfo.id).limit(1))).first()
    if has_user or has_class:
        return

    teacher = User(
        username="teacher",
        email="teacher@school.edu",
        password_hash="hashed",
        role="teacher",
    )
    db.add(teacher)
    await db.flush()

    classes_config = [
        {"name": "高三1班", "students": 45, "slug_id": 1},
        {"name": "高三2班", "students": 42, "slug_id": 2},
        {"name": "高三3班", "students": 40, "slug_id": 3},
    ]

    class_map: Dict[int, ClassInfo] = {}
    for cfg in classes_config:
        cls = ClassInfo(
            class_name=cfg["name"],
            teacher_id=teacher.id,
            total_students=cfg["students"],
            subject="数学",
            grade="高三",
        )
        db.add(cls)
        await db.flush()
        class_map[cfg["slug_id"]] = cls

        for i in range(cfg["students"]):
            name = STUDENT_NAMES[i] if i < len(STUDENT_NAMES) else f"学生{i + 1}"
            db.add(ClassMember(
                class_id=cls.id,
                name=name,
                gender="男" if i % 2 == 0 else "女",
                order_index=i + 1,
            ))

    dataset_items = {item["id"]: item for item in list_dataset_homeworks()}
    class1 = class_map[1]
    for meta in DATASET_HOMEWORK_META:
        ref_answer = ""
        if meta["id"] in dataset_items:
            detail = get_dataset_homework(file_id=meta["id"])
            ref_answer = detail["reference_answer"] if detail else ""

        assignment = HomeworkAssignment(
            title=meta["title"],
            class_id=class1.id,
            teacher_id=teacher.id,
            reference_answer=ref_answer,
            assign_date=meta["date"],
            deadline=meta["date"],
            status=meta["status"],
            subject="数学",
            description=f"高考数学真题练习（{meta['title']}）",
            dataset_file_id=meta["id"] if meta["id"] in dataset_items else None,
            total_students=45,
        )
        db.add(assignment)
        await db.flush()
        await _seed_submissions_for_assignment(db, assignment, meta, has_test_data=True)

    for cls_key, homework_meta in ((2, CLASS2_HOMEWORK), (3, CLASS3_HOMEWORK)):
        cls = class_map[cls_key]
        for meta in homework_meta:
            assignment = HomeworkAssignment(
                title=meta["title"],
                class_id=cls.id,
                teacher_id=teacher.id,
                assign_date=meta["date"],
                deadline=meta["deadline"],
                status=meta["status"],
                subject="数学",
                description=meta["description"],
                total_students=meta["total"],
            )
            db.add(assignment)
            await db.flush()
            await _seed_submissions_for_assignment(db, assignment, meta, has_test_data=False)

    await db.commit()


async def _seed_submissions_for_assignment(
    db: AsyncSession,
    assignment: HomeworkAssignment,
    meta: dict,
    has_test_data: bool,
) -> None:
    from ai_client import ai_client

    existing_count = await db.scalar(
        select(func.count(HomeworkSubmission.id))
        .where(HomeworkSubmission.assignment_id == assignment.id)
    )
    if existing_count:
        return

    total = assignment.total_students
    submitted = meta["submitted"]
    graded = meta["status"] == "已批改"
    avg_score = meta.get("avgScore", 0)
    hw_id = meta.get("id", assignment.id)

    members = await _class_members(db, assignment.class_id)

    # 测试数据的批改结果使用本地规则批改（静态、确定性，不调用 AI）
    test_grading_result = None
    test_ocr_result = None
    if has_test_data and assignment.dataset_file_id and graded:
        dataset_data = get_dataset_homework(file_id=assignment.dataset_file_id)
        if dataset_data:
            test_ocr_result = dataset_data["full_content"]
            test_grading_result = ai_client._mock_grade_homework(
                dataset_data["full_content"], dataset_data["reference_answer"], assignment.subject or "数学"
            )
            test_grading_result.pop("debug_mode", None)
            test_grading_result["message"] = "演示数据（本地规则批改）"

    for i in range(min(total, submitted)):
        member = members[i] if i < len(members) else None
        name = member.name if member else f"学生{i + 1}"

        is_test = has_test_data and i == 0 and assignment.dataset_file_id is not None
        dataset_file_id = assignment.dataset_file_id if is_test else None

        if graded:
            if is_test and test_grading_result:
                score = test_grading_result.get("score", avg_score)
                wrong_count = test_grading_result.get("wrong_count", 0)
                grading_result = json.dumps(test_grading_result, ensure_ascii=False)
                ocr_result = test_ocr_result
            else:
                variance = ((i * 17 + hw_id * 7) % 31) - 15
                score = max(40, min(100, round(avg_score + variance)))
                wrong_count = round((100 - score) / 10)
                grading_result = None
                ocr_result = None
            status = "completed"
            grading_status = "已批改"
        else:
            score = None
            wrong_count = None
            grading_result = None
            ocr_result = None
            status = "pending"
            grading_status = "待批改"

        hour = 8 + (i % 12) if graded else 9 + (i % 10)
        minute = (i * 7) % 60 if graded else (i * 5) % 60
        submit_time = f"{assignment.assign_date} {hour:02d}:{minute:02d}"

        db.add(HomeworkSubmission(
            assignment_id=assignment.id,
            student_name=name,
            dataset_file_id=dataset_file_id,
            is_test_data=is_test,
            submit_time=submit_time,
            file_count=1 if is_test else 1 + (i % 2),
            score=score,
            wrong_count=wrong_count,
            status=status,
            grading_status=grading_status,
            subject=assignment.subject,
            image_paths=json.dumps([]),
            grading_result=grading_result,
            ocr_result=ocr_result,
        ))


# ==================== 班级 ====================

async def _class_to_dict(db: AsyncSession, cls: ClassInfo) -> dict:
    member_count = await _member_count(db, cls.id)
    homework_count = await db.scalar(
        select(func.count(HomeworkAssignment.id)).where(HomeworkAssignment.class_id == cls.id)
    ) or 0
    return {
        "id": cls.id,
        "slug": class_slug(cls.id),
        "name": cls.class_name,
        "students": member_count,
        "member_count": member_count,
        "homework_count": homework_count,
        "subject": cls.subject or "数学",
        "grade": cls.grade or "高三",
        "created_at": cls.created_at,
    }


async def get_class_list(db: AsyncSession, *, teacher_id: int) -> List[dict]:
    result = await db.execute(
        select(ClassInfo).where(ClassInfo.teacher_id == teacher_id).order_by(ClassInfo.id)
    )
    return [await _class_to_dict(db, cls) for cls in result.scalars().all()]


async def get_class_detail(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> dict:
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    return await _class_to_dict(db, cls)


async def create_class(db: AsyncSession, name: str, subject: str = "数学", grade: str = "高三",
                       *, teacher_id: int) -> dict:
    cls = ClassInfo(
        class_name=name,
        subject=subject or "数学",
        grade=grade or "高三",
        teacher_id=teacher_id,
        total_students=0,
    )
    db.add(cls)
    await db.commit()
    await db.refresh(cls)
    return await _class_to_dict(db, cls)


async def update_class(db: AsyncSession, class_slug_value: str, updates: dict, *, teacher_id: int) -> dict:
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    if updates.get("name") is not None:
        cls.class_name = updates["name"]
    if updates.get("subject") is not None:
        cls.subject = updates["subject"]
    if updates.get("grade") is not None:
        cls.grade = updates["grade"]
    await db.commit()
    await db.refresh(cls)
    return await _class_to_dict(db, cls)


async def delete_class(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> dict:
    """删除班级及其学生、作业和作业提交（错题本记录保留）"""
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    assignment_ids = [
        row[0] for row in (await db.execute(
            select(HomeworkAssignment.id).where(HomeworkAssignment.class_id == cls.id)
        )).all()
    ]
    deleted_submissions = 0
    if assignment_ids:
        res = await db.execute(
            delete(HomeworkSubmission).where(HomeworkSubmission.assignment_id.in_(assignment_ids))
        )
        deleted_submissions = res.rowcount or 0
    await db.execute(delete(HomeworkAssignment).where(HomeworkAssignment.class_id == cls.id))
    res_members = await db.execute(delete(ClassMember).where(ClassMember.class_id == cls.id))
    await db.delete(cls)
    await db.commit()
    return {
        "message": "班级已删除",
        "deleted_assignments": len(assignment_ids),
        "deleted_submissions": deleted_submissions,
        "deleted_members": res_members.rowcount or 0,
    }


# ==================== 学生 ====================

def _member_to_dict(m: ClassMember, display_name: Optional[str] = None) -> dict:
    return {
        "id": m.id,
        "class_id": m.class_id,
        "name": m.name,
        "display_name": display_name or m.name,
        "gender": m.gender,
        "student_no": m.student_no,
        "order_index": m.order_index,
        "created_at": m.created_at,
    }


def member_display_names(members: List[ClassMember]) -> Dict[int, str]:
    """
    班级内重名的学生在姓名后带学号区分，如“陈晓明（2025004）”；
    没有学号的重名学生（历史数据）标“未填学号”。不重名的只显示姓名。
    """
    counts: Dict[str, int] = {}
    for m in members:
        counts[m.name] = counts.get(m.name, 0) + 1
    names = {}
    for m in members:
        if counts[m.name] > 1:
            names[m.id] = f"{m.name}（{m.student_no or '未填学号'}）"
        else:
            names[m.id] = m.name
    return names


def _norm_no(student_no: Optional[str]) -> Optional[str]:
    value = (student_no or "").strip()
    return value[:50] or None


def _duplicate_reason(members: List[ClassMember], name: str, student_no: Optional[str],
                      exclude_id: Optional[int] = None) -> Optional[str]:
    """
    同一班级内的唯一性规则：有学号时以学号唯一；没有学号时以姓名唯一（同名不同学号可以共存）。
    返回重复原因（None 表示不重复）。
    """
    others = [m for m in members if exclude_id is None or m.id != exclude_id]
    if student_no:
        if any((m.student_no or "").strip() == student_no for m in others):
            return f"班级中已有学号为 {student_no} 的学生"
        return None
    if any(m.name == name for m in others):
        return f"班级中已有同名学生：{name}（如果是不同的学生，请填写学号区分）"
    return None


def _subs_by_member(members: List[ClassMember], subs: List[HomeworkSubmission]) -> Dict[int, List[HomeworkSubmission]]:
    """
    把提交记录归到学生：优先按 member_id；历史记录没有 member_id 时，只有姓名在班里唯一才按姓名归属
    （同名学生的旧记录无法区分，不归到任何人名下，避免成绩串号）。
    """
    by_id = {m.id: m for m in members}
    name_count: Dict[str, int] = {}
    for m in members:
        name_count[m.name] = name_count.get(m.name, 0) + 1
    unique_name = {m.name: m.id for m in members if name_count[m.name] == 1}
    result: Dict[int, List[HomeworkSubmission]] = {}
    for s in subs:
        mid = s.member_id if s.member_id in by_id else None
        if mid is None and not s.member_id and s.student_name in unique_name:
            mid = unique_name[s.student_name]
        if mid is not None:
            result.setdefault(mid, []).append(s)
    return result


def is_scored(sub: HomeworkSubmission) -> bool:
    """计入成绩统计的提交：批改完成且有分数（失败、排队、批改中、未批改都不计入）"""
    return sub.status == "completed" and sub.grading_status == "已批改" and sub.score is not None


async def list_members(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> List[dict]:
    """学生列表 + 每人作业统计（平均分 / 已交次数 / 排名 / 趋势），按学生 ID 聚合"""
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    members = await _class_members(db, cls.id)
    display = member_display_names(members)

    assignment_ids = [
        row[0] for row in (await db.execute(
            select(HomeworkAssignment.id).where(HomeworkAssignment.class_id == cls.id)
        )).all()
    ]
    subs: List[HomeworkSubmission] = []
    if assignment_ids:
        subs = list((await db.execute(
            select(HomeworkSubmission)
            .where(HomeworkSubmission.assignment_id.in_(assignment_ids))
            .order_by(HomeworkSubmission.id)
        )).scalars().all())
    by_member = _subs_by_member(members, subs)

    items = []
    for m in members:
        student_subs = by_member.get(m.id, [])
        scores = [s.score for s in student_subs if is_scored(s)]
        avg = round(sum(scores) / len(scores), 1) if scores else None
        trend = None
        if len(scores) >= 2:
            trend = "up" if scores[-1] > scores[-2] else ("down" if scores[-1] < scores[-2] else "flat")
        if avg is None:
            level = "暂无成绩"
        elif avg >= 85:
            level = "优秀"
        elif avg >= 75:
            level = "良好"
        elif avg >= PASS_SCORE:
            level = "待提高"
        else:
            level = "需关注"
        items.append({
            **_member_to_dict(m, display.get(m.id)),
            "avgScore": avg,
            "submittedCount": len(student_subs),
            "gradedCount": len(scores),
            "homeworkCount": len(assignment_ids),
            "trend": trend,
            "status": level,
            "rank": None,
        })

    ranked = sorted([i for i in items if i["avgScore"] is not None], key=lambda x: -x["avgScore"])
    for idx, item in enumerate(ranked):
        item["rank"] = idx + 1
    return items


async def add_member(db: AsyncSession, class_slug_value: str, name: str,
                     gender: Optional[str] = None, student_no: Optional[str] = None, *, teacher_id: int) -> dict:
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    name = (name or "").strip()[:50]
    if not name:
        raise InvalidInputError("学生姓名不能为空")
    student_no = _norm_no(student_no)
    members = await _class_members(db, cls.id)
    reason = _duplicate_reason(members, name, student_no)
    if reason:
        raise DuplicateError(reason)
    max_order = max([m.order_index or 0 for m in members], default=0)
    member = ClassMember(
        class_id=cls.id,
        name=name,
        gender=gender or "男",
        student_no=student_no,
        order_index=max_order + 1,
    )
    db.add(member)
    await db.flush()
    cls.total_students = await _member_count(db, cls.id)
    await db.commit()
    await db.refresh(member)
    members.append(member)
    return _member_to_dict(member, member_display_names(members).get(member.id))


def parse_member_lines(text: str) -> List[dict]:
    """
    解析批量导入文本：每行一个学生，格式 `姓名[,性别][,学号]`，
    分隔符支持英文/中文逗号、制表符、空格；自动跳过表头行（姓名/name）。
    """
    rows = []
    for raw in (text or "").splitlines():
        line = raw.strip().lstrip("﻿")
        if not line:
            continue
        parts = [p.strip() for p in re.split(r"[,，\t;；]+|\s{2,}|\s", line) if p.strip()]
        if not parts:
            continue
        if parts[0] in ("姓名", "name", "Name", "学生姓名"):
            continue
        name = parts[0][:50]
        gender = None
        student_no = None
        for p in parts[1:]:
            if p in ("男", "女") and gender is None:
                gender = p
            elif student_no is None:
                student_no = p[:50]
        rows.append({"name": name, "gender": gender, "student_no": student_no})
    return rows


async def import_members(db: AsyncSession, class_slug_value: str, text: str, *, teacher_id: int) -> dict:
    """
    批量导入。去重规则同 add_member：有学号按学号唯一，没学号按姓名唯一；
    同名不同学号的学生全部保留（R1-011）。
    """
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    rows = parse_member_lines(text)
    if not rows:
        raise InvalidInputError("没有解析到学生姓名，请每行填写一个学生")
    members = await _class_members(db, cls.id)
    max_order = max([m.order_index or 0 for m in members], default=0)
    added, skipped_name, skipped_no = [], [], []
    for row in rows:
        student_no = _norm_no(row["student_no"])
        reason = _duplicate_reason(members, row["name"], student_no)
        if reason:
            if student_no:
                skipped_no.append(f"{row['name']}（{student_no}）")
            else:
                skipped_name.append(row["name"])
            continue
        max_order += 1
        member = ClassMember(
            class_id=cls.id,
            name=row["name"],
            gender=row["gender"] or "男",
            student_no=student_no,
            order_index=max_order,
        )
        db.add(member)
        members.append(member)
        added.append(row["name"] if not student_no else f"{row['name']}（{student_no}）")
    await db.flush()
    cls.total_students = await _member_count(db, cls.id)
    await db.commit()
    skipped = skipped_name + skipped_no
    message = f"成功导入 {len(added)} 名学生"
    if skipped_name:
        message += f"，重名跳过 {len(skipped_name)} 名：{'、'.join(skipped_name)}"
    if skipped_no:
        message += f"，学号重复跳过 {len(skipped_no)} 名：{'、'.join(skipped_no)}"
    return {
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added": added,
        "skipped": skipped,
        "skipped_duplicate_name": skipped_name,
        "skipped_duplicate_no": skipped_no,
        "message": message,
    }


async def _get_member(db: AsyncSession, cls: ClassInfo, member_id: int) -> ClassMember:
    member = await db.get(ClassMember, member_id)
    if not member or member.class_id != cls.id:
        raise NotFoundError("学生不存在")
    return member


async def update_member(db: AsyncSession, class_slug_value: str, member_id: int, updates: dict, *, teacher_id: int) -> dict:
    """编辑学生。提交记录按 member_id 关联，改名后历史成绩仍归属该学生（同时刷新提交上的姓名快照）"""
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    member = await _get_member(db, cls, member_id)
    new_name = member.name
    if updates.get("name") is not None:
        new_name = updates["name"].strip()[:50]
        if not new_name:
            raise InvalidInputError("学生姓名不能为空")
    new_no = member.student_no
    if "student_no" in updates and updates["student_no"] is not None:
        new_no = _norm_no(updates["student_no"])
    if new_name != member.name or new_no != member.student_no:
        members = await _class_members(db, cls.id)
        reason = _duplicate_reason(members, new_name, new_no, exclude_id=member.id)
        if reason:
            raise DuplicateError(reason)
    if new_name != member.name:
        # 先把还没关联 member_id 的旧记录（按旧姓名唯一匹配）挂到该学生名下，再刷新姓名快照
        await _link_legacy_submissions(db, cls.id, member)
        subs = (await db.execute(
            select(HomeworkSubmission).where(HomeworkSubmission.member_id == member.id)
        )).scalars().all()
        for s in subs:
            s.student_name = new_name
        member.name = new_name
    member.student_no = new_no
    if updates.get("gender") is not None:
        member.gender = updates["gender"]
    await db.commit()
    await db.refresh(member)
    members = await _class_members(db, cls.id)
    return _member_to_dict(member, member_display_names(members).get(member.id))


async def delete_member(db: AsyncSession, class_slug_value: str, member_id: int, *, teacher_id: int) -> dict:
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    member = await _get_member(db, cls, member_id)
    await db.delete(member)
    await db.flush()
    cls.total_students = await _member_count(db, cls.id)
    await db.commit()
    return {"message": f"已移除学生：{member.name}"}


async def _link_legacy_submissions(db: AsyncSession, class_id: int, member: ClassMember) -> int:
    """把该班作业下 member_id 为空、姓名与该学生相同且班里没有重名的旧提交关联到该学生"""
    same_name = await db.scalar(
        select(func.count(ClassMember.id))
        .where(ClassMember.class_id == class_id, ClassMember.name == member.name)
    )
    if same_name != 1:
        return 0
    assignment_ids = select(HomeworkAssignment.id).where(HomeworkAssignment.class_id == class_id)
    subs = (await db.execute(
        select(HomeworkSubmission)
        .where(HomeworkSubmission.assignment_id.in_(assignment_ids))
        .where(HomeworkSubmission.member_id.is_(None))
        .where(HomeworkSubmission.student_name == member.name)
    )).scalars().all()
    for s in subs:
        s.member_id = member.id
    return len(subs)


# ==================== 作业 ====================

def _assignment_to_dict(assignment: HomeworkAssignment, stats: dict, total: Optional[int] = None) -> dict:
    """作业标识统一为数据库主键（id == assignment_id）"""
    return {
        "id": assignment.id,
        "assignment_id": assignment.id,
        "class_id": assignment.class_id,
        "title": assignment.title,
        "date": assignment.assign_date,
        "deadline": assignment.deadline,
        "submitted": stats["submitted"],
        "total": total if total is not None else assignment.total_students,
        "avgScore": stats["avg_score"],
        "status": assignment.status,
        "description": assignment.description,
        "subject": assignment.subject,
        "referenceAnswer": assignment.reference_answer or "",
        "hasReferenceAnswer": bool((assignment.reference_answer or "").strip()),
        "gradedCount": stats["graded"],
        "pendingCount": stats["pending"],
        "processingCount": stats["processing"],
        "failedCount": stats["failed"],
    }


async def _submission_stats(db: AsyncSession, assignment_id: int) -> dict:
    result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.assignment_id == assignment_id)
    )
    submissions = result.scalars().all()
    submitted = len(submissions)
    scores = [s.score for s in submissions if is_scored(s)]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    return {
        "submitted": submitted,
        "avg_score": avg_score,
        "graded": len(scores),
        "pending": sum(1 for s in submissions if s.grading_status == "待批改" and s.status != "failed"),
        "processing": sum(1 for s in submissions if s.status in ("processing", "queued")),
        "failed": sum(1 for s in submissions if s.status == "failed"),
    }


async def _assignment_total(db: AsyncSession, assignment: HomeworkAssignment) -> int:
    count = await _member_count(db, assignment.class_id)
    return count if count > 0 else (assignment.total_students or 0)


async def get_homework_list(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> List[dict]:
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    result = await db.execute(
        select(HomeworkAssignment)
        .where(HomeworkAssignment.class_id == cls.id)
        .order_by(HomeworkAssignment.assign_date.desc(), HomeworkAssignment.id.desc())
    )
    assignments = result.scalars().all()
    total = await _member_count(db, cls.id)
    items = []
    for a in assignments:
        stats = await _submission_stats(db, a.id)
        items.append(_assignment_to_dict(a, stats, total if total > 0 else None))
    return items


async def get_assignment_record(db: AsyncSession, class_slug_value: str, homework_id: int, *, teacher_id: int) -> Optional[HomeworkAssignment]:
    """按作业主键查找（必须属于该班级与当前教师）；不再兼容旧的“展示 ID”"""
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    a = await db.get(HomeworkAssignment, homework_id)
    if not a or a.class_id != cls.id:
        return None
    return a


async def get_homework_by_id(db: AsyncSession, class_slug_value: str, homework_id: int, *, teacher_id: int) -> Optional[dict]:
    a = await get_assignment_record(db, class_slug_value, homework_id, teacher_id=teacher_id)
    if not a:
        return None
    stats = await _submission_stats(db, a.id)
    return _assignment_to_dict(a, stats, await _assignment_total(db, a))


async def create_assignment(db: AsyncSession, class_slug_value: str, data: dict, *, teacher_id: int) -> dict:
    from datetime import date

    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    title = (data.get("title") or "").strip()
    if not title:
        raise InvalidInputError("作业标题不能为空")
    total = await _member_count(db, cls.id)
    assignment = HomeworkAssignment(
        title=title,
        class_id=cls.id,
        teacher_id=teacher_id,
        reference_answer=data.get("reference_answer") or "",
        assign_date=data.get("assign_date") or date.today().isoformat(),
        deadline=data.get("deadline") or data.get("assign_date") or date.today().isoformat(),
        status="待批改",
        subject=data.get("subject") or cls.subject or "数学",
        description=data.get("description") or "",
        total_students=total,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    stats = await _submission_stats(db, assignment.id)
    return _assignment_to_dict(assignment, stats, total)


async def update_assignment(db: AsyncSession, class_slug_value: str, homework_id: int, data: dict, *, teacher_id: int) -> Optional[dict]:
    a = await get_assignment_record(db, class_slug_value, homework_id, teacher_id=teacher_id)
    if not a:
        return None
    field_map = {
        "title": "title",
        "description": "description",
        "reference_answer": "reference_answer",
        "assign_date": "assign_date",
        "deadline": "deadline",
        "subject": "subject",
    }
    for key, attr in field_map.items():
        if data.get(key) is not None:
            setattr(a, attr, data[key])
    if data.get("title") is not None and not a.title.strip():
        raise InvalidInputError("作业标题不能为空")
    await db.commit()
    await db.refresh(a)
    stats = await _submission_stats(db, a.id)
    return _assignment_to_dict(a, stats, await _assignment_total(db, a))


async def delete_assignment(db: AsyncSession, class_slug_value: str, homework_id: int, *, teacher_id: int) -> Optional[dict]:
    a = await get_assignment_record(db, class_slug_value, homework_id, teacher_id=teacher_id)
    if not a:
        return None
    res = await db.execute(delete(HomeworkSubmission).where(HomeworkSubmission.assignment_id == a.id))
    await db.delete(a)
    await db.commit()
    return {"message": "作业已删除", "deleted_submissions": res.rowcount or 0}


async def get_student_submissions(db: AsyncSession, class_slug_value: str, homework_id: int, *, teacher_id: int) -> List[dict]:
    """作业名录：班级每个学生一行（按学生 ID 关联提交），外加不在花名册里的提交"""
    assignment = await get_assignment_record(db, class_slug_value, homework_id, teacher_id=teacher_id)
    if not assignment:
        return []

    members = await _class_members(db, assignment.class_id)
    display = member_display_names(members)
    subs = list((await db.execute(
        select(HomeworkSubmission)
        .where(HomeworkSubmission.assignment_id == assignment.id)
        .order_by(HomeworkSubmission.id)
    )).scalars().all())
    by_member = _subs_by_member(members, subs)

    students = []
    used = set()
    for i, member in enumerate(members):
        member_subs = by_member.get(member.id) or []
        sub = member_subs[-1] if member_subs else None  # 同一学生多次提交时取最新一次
        if sub:
            used.update(s.id for s in member_subs)
            item = _submission_to_student(sub, i + 1)
        else:
            item = _empty_student(i + 1, member.name)
        item.update({
            "member_id": member.id,
            "name": member.name,
            "display_name": display.get(member.id, member.name),
            "student_no": member.student_no,
            "in_roster": True,
        })
        students.append(item)

    # 班级里没有花名册时，按作业的计划人数补齐占位（兼容历史数据）
    if not members:
        seen_names = set()
        for i in range(assignment.total_students or 0):
            name = f"学生{i + 1}"
            seen_names.add(name)
            sub = next((s for s in reversed(subs) if s.student_name == name), None)
            if sub:
                used.add(sub.id)
            item = _submission_to_student(sub, i + 1) if sub else _empty_student(i + 1, name)
            item.update({"member_id": None, "display_name": item["name"], "student_no": None, "in_roster": False})
            students.append(item)

    # 已上传但不在花名册中的提交（学生已被移出班级，或临时录入的姓名）
    for sub in subs:
        if sub.id in used:
            continue
        item = _submission_to_student(sub, len(students) + 1)
        item.update({"member_id": sub.member_id, "display_name": item["name"], "student_no": None, "in_roster": False})
        students.append(item)
        used.add(sub.id)

    return students


def _empty_student(order_id: int, name: str) -> dict:
    return {
        "id": order_id,
        "submission_id": None,
        "name": name,
        "uploaded": False,
        "submitStatus": "未提交",
        "submitTime": None,
        "score": None,
        "gradingStatus": "未提交",
        "wrongCount": None,
        "fileCount": 0,
        "status": None,
        "progressStage": None,
        "errorMessage": None,
        "review_status": None,
        "needs_review": False,
        "teacher_modified": False,
    }


def _submission_to_student(sub: HomeworkSubmission, order_id: int) -> dict:
    scored = is_scored(sub)
    return {
        "id": order_id,
        "submission_id": sub.id,
        "name": sub.student_name or f"学生{order_id}",
        "uploaded": True,
        "submitStatus": "已提交",
        "submitTime": sub.submit_time,
        "score": sub.score if scored else None,
        "gradingStatus": sub.grading_status or ("已批改" if sub.status == "completed" else "待批改"),
        "wrongCount": sub.wrong_count if scored else None,
        "fileCount": sub.file_count or 1,
        "grading_result_id": sub.id if sub.status == "completed" else None,
        "status": sub.status,
        "progressStage": sub.progress_stage,
        "errorMessage": sub.error_message,
        "review_status": sub.review_status if scored else None,
        "needs_review": bool(sub.needs_review) if scored else False,
        "teacher_modified": bool(sub.teacher_modified) if scored else False,
    }


# ==================== 统计 ====================

async def _class_graded_submissions(db: AsyncSession, class_id: int) -> List[HomeworkSubmission]:
    """班级内计入成绩的提交（批改完成且有分数；失败 / 未批改的不计入）"""
    assignment_ids = [
        row[0] for row in (await db.execute(
            select(HomeworkAssignment.id).where(HomeworkAssignment.class_id == class_id)
        )).all()
    ]
    if not assignment_ids:
        return []
    subs = (await db.execute(
        select(HomeworkSubmission)
        .where(HomeworkSubmission.assignment_id.in_(assignment_ids))
        .where(HomeworkSubmission.status == "completed")
        .order_by(HomeworkSubmission.id)
    )).scalars().all()
    return [s for s in subs if is_scored(s)]


async def get_homework_stats(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> dict:
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    homework_list = await get_homework_list(db, class_slug_value, teacher_id=teacher_id)
    if not homework_list:
        return {
            "currentHomework": None,
            "submitRate": 0,
            "submitted": 0,
            "notSubmitted": 0,
            "total": await _member_count(db, cls.id),
            "gradedCount": 0,
            "pendingCount": 0,
            "pendingHomeworkCount": 0,
            "totalHomeworks": 0,
            "avgScore": 0,
            "passRate": 0,
        }

    current = next((h for h in homework_list if h["status"] == "待批改"), homework_list[0])
    pending_homeworks = [h for h in homework_list if h["status"] == "待批改"]
    graded_homeworks = [h for h in homework_list if h["status"] == "已批改"]

    graded_submissions = sum(h["gradedCount"] for h in homework_list)
    pending_count = sum(h["pendingCount"] for h in homework_list)

    avg_scores = [h["avgScore"] for h in homework_list if h["avgScore"] > 0]
    avg_score = round(sum(avg_scores) / len(avg_scores), 1) if avg_scores else 0
    submit_rate = round((current["submitted"] / current["total"]) * 1000) / 10 if current["total"] > 0 else 0

    graded = await _class_graded_submissions(db, cls.id)
    scored = [s.score for s in graded]
    pass_rate = round(sum(1 for s in scored if s >= PASS_SCORE) / len(scored) * 1000) / 10 if scored else 0

    return {
        "currentHomework": current,
        "submitRate": submit_rate,
        "submitted": current["submitted"],
        "notSubmitted": max(0, current["total"] - current["submitted"]),
        "total": current["total"],
        "gradedCount": graded_submissions,
        "pendingCount": pending_count,
        "pendingHomeworkCount": len(pending_homeworks),
        "totalHomeworks": len(homework_list),
        "avgScore": avg_score,
        "passRate": pass_rate,
        "gradedHomeworkCount": len(graded_homeworks),
    }


async def get_grading_tasks(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> List[dict]:
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    homework_list = await get_homework_list(db, class_slug_value, teacher_id=teacher_id)
    tasks = []
    for hw in homework_list:
        if hw["status"] != "待批改" or hw["submitted"] == 0:
            continue
        pending_count = hw["pendingCount"] + hw["processingCount"]
        done = hw["submitted"] - pending_count
        progress = round((done / hw["submitted"]) * 100) if hw["submitted"] > 0 else 0
        tasks.append({
            "id": f"hw-{cls.id}-{hw['id']}",
            "type": "homework-grading",
            "title": f"批改：{hw['title']}",
            "homeworkId": hw["id"],
            "assignmentId": hw["id"],
            "classId": cls.id,
            "className": cls.class_name,
            "status": "pending" if pending_count > 0 or hw["submitted"] == 0 else "completed",
            "progress": progress,
            "progressLabel": f"已批改 {done}/{hw['submitted']} 份",
            "pendingCount": pending_count,
            "submitted": hw["submitted"],
            "createdAt": hw["date"],
            "priority": "high" if pending_count > 5 else "medium",
        })
    return tasks


async def get_all_grading_tasks(db: AsyncSession, *, teacher_id: int) -> List[dict]:
    result = await db.execute(
        select(ClassInfo.id).where(ClassInfo.teacher_id == teacher_id).order_by(ClassInfo.id)
    )
    tasks = []
    for (cid,) in result.all():
        tasks.extend(await get_grading_tasks(db, str(cid), teacher_id=teacher_id))
    return tasks


async def get_alert_students(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> List[dict]:
    """预警学生：平均分低于及格线 / 最近一次成绩明显下滑 / 已过截止日期仍未上传（按学生 ID 统计）"""
    from datetime import date

    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    members = await _class_members(db, cls.id)
    display = member_display_names(members)
    alerts = []

    graded = await _class_graded_submissions(db, cls.id)
    by_member = _subs_by_member(members, graded)
    for m in members:
        scores = [s.score for s in by_member.get(m.id, [])]
        if not scores:
            continue
        avg = round(sum(scores) / len(scores), 1)
        name = display.get(m.id, m.name)
        if avg < PASS_SCORE:
            alerts.append({"member_id": m.id, "name": name, "score": avg, "trend": "down",
                           "warning": f"作业平均分低于{PASS_SCORE}分"})
        elif len(scores) >= 2 and scores[-2] - scores[-1] >= 15:
            alerts.append({"member_id": m.id, "name": name, "score": scores[-1], "trend": "down",
                           "warning": f"最近一次成绩下降 {round(scores[-2] - scores[-1])} 分"})

    homework_list = await get_homework_list(db, class_slug_value, teacher_id=teacher_id)
    today = date.today().isoformat()
    # 只对已过截止日期的待批改作业提示「未上传」
    latest_pending = next(
        (h for h in homework_list if h["status"] == "待批改" and (h["deadline"] or "") < today), None
    )
    if latest_pending:
        students = await get_student_submissions(db, class_slug_value, latest_pending["id"], teacher_id=teacher_id)
        not_submitted = [s for s in students if not s["uploaded"] and s.get("in_roster")]
        for s in not_submitted[:5]:
            alerts.append({
                "member_id": s.get("member_id"),
                "name": s.get("display_name") or s["name"],
                "score": None,
                "trend": "down",
                "warning": f"未上传作业《{latest_pending['title']}》",
            })

    alerts.sort(key=lambda a: (a["score"] is None, a["score"] if a["score"] is not None else 0))
    return alerts[:10]


def _submission_display_name(sub: HomeworkSubmission, display: Dict[int, str], unique_name: Dict[str, int]) -> str:
    if sub.member_id and sub.member_id in display:
        return display[sub.member_id]
    if not sub.member_id and sub.student_name in unique_name:
        return display.get(unique_name[sub.student_name], sub.student_name)
    return sub.student_name or "未填写姓名"


def _unique_name_map(members: List[ClassMember]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for m in members:
        counts[m.name] = counts.get(m.name, 0) + 1
    return {m.name: m.id for m in members if counts[m.name] == 1}


async def get_score_archive(db: AsyncSession, class_slug_value: str, *, teacher_id: int) -> List[dict]:
    """成绩档案：每份作业的成绩统计（平均/最高/最低/及格率/分布/前五名）；失败与未批改的不计入"""
    cls = await get_class_record(db, class_slug_value, teacher_id=teacher_id)
    members = await _class_members(db, cls.id)
    display = member_display_names(members)
    unique_name = _unique_name_map(members)
    assignments = (await db.execute(
        select(HomeworkAssignment)
        .where(HomeworkAssignment.class_id == cls.id)
        .order_by(HomeworkAssignment.assign_date.desc(), HomeworkAssignment.id.desc())
    )).scalars().all()

    items = []
    for a in assignments:
        subs = (await db.execute(
            select(HomeworkSubmission)
            .where(HomeworkSubmission.assignment_id == a.id)
            .where(HomeworkSubmission.status == "completed")
        )).scalars().all()
        scored = [(_submission_display_name(s, display, unique_name), s.score) for s in subs if is_scored(s)]
        if not scored:
            continue
        values = [v for _, v in scored]
        n = len(values)
        buckets = [
            ("90-100", lambda v: v >= 90),
            ("80-89", lambda v: 80 <= v < 90),
            ("70-79", lambda v: 70 <= v < 80),
            ("60-69", lambda v: 60 <= v < 70),
            ("60以下", lambda v: v < 60),
        ]
        distribution = []
        for label, pred in buckets:
            count = sum(1 for v in values if pred(v))
            distribution.append({"range": label, "count": count, "percentage": round(count / n * 1000) / 10})
        top = sorted(scored, key=lambda x: -x[1])[:5]
        items.append({
            "id": a.id,
            "assignment_id": a.id,
            "name": a.title,
            "date": a.assign_date,
            "avgScore": round(sum(values) / n, 1),
            "highest": max(values),
            "lowest": min(values),
            "passRate": round(sum(1 for v in values if v >= PASS_SCORE) / n * 1000) / 10,
            "gradedCount": n,
            "excellentCount": sum(1 for v in values if v >= 90),
            "goodCount": sum(1 for v in values if 80 <= v < 90),
            "passCount": sum(1 for v in values if PASS_SCORE <= v < 80),
            "failCount": sum(1 for v in values if v < PASS_SCORE),
            "distribution": distribution,
            "topStudents": [{"name": nme, "score": sc, "rank": i + 1} for i, (nme, sc) in enumerate(top)],
        })
    return items


async def get_homework_analysis(db: AsyncSession, class_slug_value: str, homework_id: int, *, teacher_id: int) -> Optional[dict]:
    """按题号统计本次作业各题的正确率（只统计批改完成的提交；做错名单按学生区分同名）"""
    a = await get_assignment_record(db, class_slug_value, homework_id, teacher_id=teacher_id)
    if not a:
        return None
    members = await _class_members(db, a.class_id)
    display = member_display_names(members)
    unique_name = _unique_name_map(members)
    subs = [s for s in (await db.execute(
        select(HomeworkSubmission)
        .where(HomeworkSubmission.assignment_id == a.id)
        .where(HomeworkSubmission.status == "completed")
    )).scalars().all() if is_scored(s)]

    per_q: Dict[str, dict] = {}
    analyzed = 0
    for s in subs:
        if not s.grading_result:
            continue
        try:
            gr = json.loads(s.grading_result)
        except (TypeError, ValueError):
            continue
        questions = gr.get("questions") or []
        if not questions:
            continue
        analyzed += 1
        name = _submission_display_name(s, display, unique_name)
        for idx, q in enumerate(questions):
            key = str(q.get("question_number") or idx + 1)
            entry = per_q.setdefault(key, {
                "question_number": key,
                "question_text": (q.get("question_text") or "")[:200],
                "total": 0,
                "correct": 0,
                "wrong_students": [],
                "wrong_members": [],
            })
            entry["total"] += 1
            if q.get("is_correct"):
                entry["correct"] += 1
            else:
                entry["wrong_students"].append(name)
                entry["wrong_members"].append({"member_id": s.member_id, "submission_id": s.id, "name": name})

    questions = []
    for key in sorted(per_q, key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else k)):
        e = per_q[key]
        e["correct_rate"] = round(e["correct"] / e["total"] * 1000) / 10 if e["total"] else 0
        questions.append(e)
    return {"analyzed_count": analyzed, "graded_count": len(subs), "questions": questions}


async def update_assignment_status(db: AsyncSession, assignment_id: int) -> None:
    result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.assignment_id == assignment_id)
    )
    submissions = result.scalars().all()
    if not submissions:
        return

    pending = sum(1 for s in submissions
                  if s.status in ("queued", "processing") or (s.grading_status == "待批改" and s.status != "failed"))
    assignment = await db.get(HomeworkAssignment, assignment_id)
    if not assignment:
        return

    if pending == 0:
        assignment.status = "已批改"
        scores = [s.score for s in submissions if is_scored(s)]
        assignment.avg_score = round(sum(scores) / len(scores), 1) if scores else None
    else:
        assignment.status = "待批改"


def _wrong_question_from(q: dict, *, student_name, subject, submission_id, teacher_id, member_id, source) -> WrongQuestion:
    kp = (q.get("knowledge_point") or "").strip() if isinstance(q.get("knowledge_point"), str) else ""
    return WrongQuestion(
        user_id=teacher_id,
        question_text=q.get("question_text", "") or "（无题目内容）",
        user_answer=str(q.get("student_answer", "") or ""),
        correct_answer=str(q.get("correct_answer", "") or ""),
        knowledge_point=kp[:200] or (f"作业批改-{student_name}" if student_name else "作业批改"),
        subject=subject,
        variant_questions=json.dumps([], ensure_ascii=False),
        student_name=student_name,
        submission_id=submission_id,
        question_number=str(q.get("question_number") or "")[:20] or None,
        member_id=member_id,
        source=source,
    )


async def sync_wrong_questions(
    db: AsyncSession,
    grading_result: dict,
    student_name: Optional[str],
    subject: str = "数学",
    submission_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    member_id: Optional[int] = None,
) -> int:
    """将批改错题同步到该提交所属教师的错题本（同一提交重批时先清掉旧的同步 / 改判记录）"""
    if submission_id:
        await db.execute(
            delete(WrongQuestion)
            .where(WrongQuestion.submission_id == submission_id)
            .where(WrongQuestion.source.in_(["grading", "teacher"]))
        )
    count = 0
    for q in grading_result.get("questions", []) or []:
        if q.get("is_correct", True):
            continue
        db.add(_wrong_question_from(q, student_name=student_name, subject=subject, submission_id=submission_id,
                                    teacher_id=teacher_id, member_id=member_id, source="grading"))
        count += 1
    return count


async def sync_rejudged_question(db: AsyncSession, sub: HomeworkSubmission, question: dict) -> None:
    """
    老师改判一题后同步错题本（R1-008）：判错 → 保证有这道题的错题（新加的来源标注“老师改判”）；
    判对 → 移除这道题由批改同步 / 改判产生的错题。
    """
    number = str(question.get("question_number") or "")
    existing = (await db.execute(
        select(WrongQuestion)
        .where(WrongQuestion.submission_id == sub.id)
        .where(WrongQuestion.source.in_(["grading", "teacher"]))
    )).scalars().all()
    # 旧数据没有记录题号时按题干匹配
    matched = [w for w in existing if (w.question_number or "") == number] or \
        [w for w in existing if not w.question_number and w.question_text == (question.get("question_text") or "（无题目内容）")]
    if question.get("is_correct"):
        for w in matched:
            await db.delete(w)
    elif not matched:
        db.add(_wrong_question_from(question, student_name=sub.student_name, subject=sub.subject or "数学",
                                    submission_id=sub.id, teacher_id=sub.teacher_id, member_id=sub.member_id,
                                    source="teacher"))


async def migrate_zero_question_results(db: AsyncSession) -> int:
    """
    幂等迁移（R1-008）：已有的“批改完成但一道题都没有”的记录改为失败，不再计入统计。
    只处理 grading_result 里 total_questions == 0 或 questions 为空的；grading_result 为空的旧记录不动。
    """
    subs = (await db.execute(
        select(HomeworkSubmission)
        .where(HomeworkSubmission.status == "completed")
        .where(HomeworkSubmission.grading_result.is_not(None))
    )).scalars().all()
    changed = 0
    for sub in subs:
        try:
            gr = json.loads(sub.grading_result)
        except (TypeError, ValueError):
            continue
        if not isinstance(gr, dict):
            continue
        questions = gr.get("questions")
        if (isinstance(questions, list) and len(questions) == 0) or gr.get("total_questions") == 0:
            sub.status = "failed"
            sub.grading_status = "批改失败"
            sub.progress_stage = "批改失败"
            sub.error_message = "未识别到题目，请检查照片是否清晰、是否拍到答题区域"
            sub.score = None
            sub.wrong_count = None
            sub.review_status = None
            changed += 1
    if changed:
        assignment_ids = {s.assignment_id for s in subs if s.status == "failed" and s.assignment_id}
        for aid in assignment_ids:
            await update_assignment_status(db, aid)
        print(f"[db] {changed} 条“0 题 0 分”的批改记录已改为失败（不再计入成绩统计）", flush=True)
    await db.commit()
    return changed


# ==================== 数据归属 ====================

async def backfill_ownership(db: AsyncSession) -> int:
    """
    启动时的幂等补齐（只更新空值，不改变已有归属、不删数据）：
    - 作业没有 teacher_id 时取所在班级的 teacher_id；
    - 提交没有 teacher_id 时取所属作业的 teacher_id。
    把无归属的历史数据归到某位教师请用 `python manage.py assign-orphans --username <账号>`。
    """
    changed = 0
    res = await db.execute(
        update(HomeworkAssignment)
        .where(HomeworkAssignment.teacher_id.is_(None))
        .where(HomeworkAssignment.class_id.is_not(None))
        .values(teacher_id=select(ClassInfo.teacher_id)
                .where(ClassInfo.id == HomeworkAssignment.class_id)
                .scalar_subquery())
        .execution_options(synchronize_session=False)
    )
    changed += res.rowcount or 0
    res = await db.execute(
        update(HomeworkSubmission)
        .where(HomeworkSubmission.teacher_id.is_(None))
        .where(HomeworkSubmission.assignment_id.is_not(None))
        .values(teacher_id=select(HomeworkAssignment.teacher_id)
                .where(HomeworkAssignment.id == HomeworkSubmission.assignment_id)
                .scalar_subquery())
        .execution_options(synchronize_session=False)
    )
    changed += res.rowcount or 0
    changed += await backfill_member_ids(db)
    changed += await migrate_zero_question_results(db)
    # 历史演示数据的作业说明里去掉开发用语（只改播种时写入的固定文案）
    await db.execute(
        update(HomeworkAssignment)
        .where(HomeworkAssignment.description.like("来自 dataset 测试集的真实作业数据%"))
        .values(description=func.replace(HomeworkAssignment.description, "来自 dataset 测试集的真实作业数据", "高考数学真题练习"))
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return changed


async def backfill_member_ids(db: AsyncSession) -> int:
    """
    幂等回填 homework_submissions.member_id：按“作业所在班级 + 学生姓名”匹配，
    只有班里恰好一个同名学生时才回填；有歧义的不回填并记录日志（R1-011）。
    """
    rows = (await db.execute(
        select(HomeworkSubmission.id, HomeworkSubmission.student_name, HomeworkAssignment.class_id)
        .join(HomeworkAssignment, HomeworkAssignment.id == HomeworkSubmission.assignment_id)
        .where(HomeworkSubmission.member_id.is_(None))
        .where(HomeworkSubmission.student_name.is_not(None))
    )).all()
    if not rows:
        return 0
    class_ids = {r.class_id for r in rows}
    members = (await db.execute(
        select(ClassMember.id, ClassMember.class_id, ClassMember.name).where(ClassMember.class_id.in_(class_ids))
    )).all()
    index: Dict[tuple, List[int]] = {}
    for m in members:
        index.setdefault((m.class_id, m.name), []).append(m.id)
    filled, ambiguous = 0, []
    for r in rows:
        ids = index.get((r.class_id, r.student_name), [])
        if len(ids) == 1:
            await db.execute(
                update(HomeworkSubmission).where(HomeworkSubmission.id == r.id).values(member_id=ids[0])
                .execution_options(synchronize_session=False)
            )
            filled += 1
        elif len(ids) > 1:
            ambiguous.append(r.id)
    if ambiguous:
        print(f"[db] {len(ambiguous)} 条批改记录因班级内有同名学生无法自动关联学生（提交 ID：{ambiguous[:20]}），"
              f"将显示在名录末尾，请老师重新上传或核对", flush=True)
    if filled:
        print(f"[db] 已为 {filled} 条批改记录关联学生（按班级 + 姓名唯一匹配）", flush=True)
    return filled
