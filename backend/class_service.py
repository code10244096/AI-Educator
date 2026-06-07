"""班级作业管理服务：种子数据、统计与任务聚合"""
import json
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import ClassInfo, ClassMember, HomeworkAssignment, HomeworkSubmission, User, WrongQuestion
from homework_dataset import list_dataset_homeworks, get_dataset_homework

CLASS_SLUGS = {1: "class1", 2: "class2", 3: "class3"}
SLUG_TO_ID = {v: k for k, v in CLASS_SLUGS.items()}

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


def resolve_class_id(class_slug: str) -> int:
    if class_slug not in SLUG_TO_ID:
        raise ValueError(f"未知班级: {class_slug}")
    return SLUG_TO_ID[class_slug]


async def seed_initial_data(db: AsyncSession) -> None:
    """初始化班级、学生与作业数据（仅首次）"""
    result = await db.execute(select(ClassInfo).limit(1))
    if result.scalar_one_or_none():
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
        )
        db.add(cls)
        await db.flush()
        class_map[cfg["slug_id"]] = cls

        count = cfg["students"]
        for i in range(count):
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
        ds = dataset_items.get(meta["id"])
        ref_answer = ""
        if ds:
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
            description=f"来自 dataset 测试集的真实作业数据（{meta['title']}）",
            dataset_file_id=meta["id"],
            total_students=45,
        )
        db.add(assignment)
        await db.flush()
        await _seed_submissions_for_assignment(db, assignment, meta, has_test_data=True)

    class2 = class_map[2]
    for meta in CLASS2_HOMEWORK:
        assignment = HomeworkAssignment(
            title=meta["title"],
            class_id=class2.id,
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

    class3 = class_map[3]
    for meta in CLASS3_HOMEWORK:
        assignment = HomeworkAssignment(
            title=meta["title"],
            class_id=class3.id,
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
    total = assignment.total_students
    submitted = meta["submitted"]
    graded = meta["status"] == "已批改"
    avg_score = meta.get("avgScore", 0)
    hw_id = meta.get("id", assignment.id)

    members_result = await db.execute(
        select(ClassMember)
        .where(ClassMember.class_id == assignment.class_id)
        .order_by(ClassMember.order_index)
    )
    members = members_result.scalars().all()

    for i in range(total):
        member = members[i] if i < len(members) else None
        name = member.name if member else f"学生{i + 1}"
        is_submitted = i < submitted

        if not is_submitted:
            continue

        is_test = has_test_data and i == 0
        dataset_file_id = assignment.dataset_file_id if is_test else None

        if graded:
            variance = ((i * 17 + hw_id * 7) % 31) - 15
            score = avg_score if is_test else max(40, min(100, round(avg_score + variance)))
            wrong_count = round((100 - score) / 10)
            status = "completed"
            grading_status = "已批改"
        else:
            score = None
            wrong_count = None
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
            image_paths=json.dumps([]),
        ))


def _assignment_to_dict(assignment: HomeworkAssignment, stats: dict) -> dict:
    return {
        "id": assignment.dataset_file_id or assignment.id,
        "assignment_id": assignment.id,
        "title": assignment.title,
        "date": assignment.assign_date,
        "deadline": assignment.deadline,
        "submitted": stats["submitted"],
        "total": assignment.total_students,
        "avgScore": stats["avg_score"],
        "status": assignment.status,
        "description": assignment.description,
        "datasetFileId": assignment.dataset_file_id,
        "hasTestData": assignment.dataset_file_id is not None,
        "subject": assignment.subject,
    }


async def _submission_stats(db: AsyncSession, assignment_id: int) -> dict:
    result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.assignment_id == assignment_id)
    )
    submissions = result.scalars().all()
    submitted = len(submissions)
    scores = [s.score for s in submissions if s.score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    graded = sum(1 for s in submissions if s.grading_status == "已批改")
    pending = sum(1 for s in submissions if s.grading_status == "待批改")
    return {
        "submitted": submitted,
        "avg_score": avg_score,
        "graded": graded,
        "pending": pending,
    }


async def get_class_list(db: AsyncSession) -> List[dict]:
    result = await db.execute(select(ClassInfo).order_by(ClassInfo.id))
    classes = result.scalars().all()
    return [
        {
            "id": cls.id,
            "slug": CLASS_SLUGS.get(cls.id, f"class{cls.id}"),
            "name": cls.class_name,
            "students": cls.total_students,
            "subject": "数学",
            "grade": "高三",
        }
        for cls in classes
    ]


async def get_homework_list(db: AsyncSession, class_slug: str) -> List[dict]:
    class_id = resolve_class_id(class_slug)
    result = await db.execute(
        select(HomeworkAssignment)
        .where(HomeworkAssignment.class_id == class_id)
        .order_by(HomeworkAssignment.assign_date.desc())
    )
    assignments = result.scalars().all()
    items = []
    for a in assignments:
        stats = await _submission_stats(db, a.id)
        items.append(_assignment_to_dict(a, stats))
    return items


async def get_homework_by_id(db: AsyncSession, class_slug: str, homework_id: int) -> Optional[dict]:
    class_id = resolve_class_id(class_slug)
    result = await db.execute(
        select(HomeworkAssignment).where(HomeworkAssignment.class_id == class_id)
    )
    assignments = result.scalars().all()
    for a in assignments:
        hw_key = a.dataset_file_id or a.id
        if hw_key == homework_id or a.id == homework_id:
            stats = await _submission_stats(db, a.id)
            return _assignment_to_dict(a, stats)
    return None


async def get_assignment_record(db: AsyncSession, class_slug: str, homework_id: int) -> Optional[HomeworkAssignment]:
    class_id = resolve_class_id(class_slug)
    result = await db.execute(
        select(HomeworkAssignment).where(HomeworkAssignment.class_id == class_id)
    )
    for a in result.scalars().all():
        hw_key = a.dataset_file_id or a.id
        if hw_key == homework_id or a.id == homework_id:
            return a
    return None


async def get_student_submissions(db: AsyncSession, class_slug: str, homework_id: int) -> List[dict]:
    assignment = await get_assignment_record(db, class_slug, homework_id)
    if not assignment:
        return []

    members_result = await db.execute(
        select(ClassMember)
        .where(ClassMember.class_id == assignment.class_id)
        .order_by(ClassMember.order_index)
    )
    members = members_result.scalars().all()

    sub_result = await db.execute(
        select(HomeworkSubmission)
        .where(HomeworkSubmission.assignment_id == assignment.id)
        .order_by(HomeworkSubmission.id)
    )
    submission_by_name = {s.student_name: s for s in sub_result.scalars().all()}

    students = []
    for i, member in enumerate(members[:assignment.total_students]):
        sub = submission_by_name.get(member.name)
        if sub:
            students.append(_submission_to_student(sub, i + 1))
        else:
            students.append({
                "id": i + 1,
                "submission_id": None,
                "name": member.name,
                "submitStatus": "未提交",
                "submitTime": None,
                "score": None,
                "gradingStatus": "未提交",
                "wrongCount": None,
                "fileCount": 0,
                "datasetFileId": None,
                "isTestData": False,
            })

    for i in range(len(members), assignment.total_students):
        students.append({
            "id": i + 1,
            "submission_id": None,
            "name": f"学生{i + 1}",
            "submitStatus": "未提交",
            "submitTime": None,
            "score": None,
            "gradingStatus": "未提交",
            "wrongCount": None,
            "fileCount": 0,
            "datasetFileId": None,
            "isTestData": False,
        })

    return students


def _submission_to_student(sub: HomeworkSubmission, order_id: int) -> dict:
    return {
        "id": order_id,
        "submission_id": sub.id,
        "name": sub.student_name,
        "submitStatus": "已提交",
        "submitTime": sub.submit_time,
        "score": sub.score,
        "gradingStatus": sub.grading_status or ("已批改" if sub.status == "completed" else "待批改"),
        "wrongCount": sub.wrong_count,
        "fileCount": sub.file_count or 1,
        "datasetFileId": sub.dataset_file_id,
        "isTestData": sub.is_test_data,
        "grading_result_id": sub.id if sub.status == "completed" else None,
    }


async def get_homework_stats(db: AsyncSession, class_slug: str) -> dict:
    homework_list = await get_homework_list(db, class_slug)
    if not homework_list:
        return {
            "currentHomework": None,
            "submitRate": 0,
            "submitted": 0,
            "notSubmitted": 0,
            "total": 0,
            "gradedCount": 0,
            "pendingCount": 0,
            "pendingHomeworkCount": 0,
            "totalHomeworks": 0,
            "avgScore": 0,
            "passRate": 82.3,
        }

    current = next((h for h in homework_list if h["status"] == "待批改"), homework_list[0])
    pending_homeworks = [h for h in homework_list if h["status"] == "待批改"]
    graded_homeworks = [h for h in homework_list if h["status"] == "已批改"]

    total_submitted = sum(h["submitted"] for h in homework_list)
    graded_submissions = sum(h["submitted"] for h in graded_homeworks)

    pending_count = 0
    for h in pending_homeworks:
        students = await get_student_submissions(db, class_slug, h["id"])
        pending_count += sum(1 for s in students if s["gradingStatus"] == "待批改")

    avg_scores = [h["avgScore"] for h in graded_homeworks if h["avgScore"] > 0]
    avg_score = round(sum(avg_scores) / len(avg_scores), 1) if avg_scores else 0
    submit_rate = round((current["submitted"] / current["total"]) * 1000) / 10 if current["total"] > 0 else 0

    return {
        "currentHomework": current,
        "submitRate": submit_rate,
        "submitted": current["submitted"],
        "notSubmitted": current["total"] - current["submitted"],
        "total": current["total"],
        "gradedCount": graded_submissions,
        "pendingCount": pending_count,
        "pendingHomeworkCount": len(pending_homeworks),
        "totalHomeworks": len(homework_list),
        "avgScore": avg_score,
        "passRate": 82.3,
    }


async def get_grading_tasks(db: AsyncSession, class_slug: str) -> List[dict]:
    homework_list = await get_homework_list(db, class_slug)
    tasks = []
    for hw in homework_list:
        if hw["status"] != "待批改":
            continue
        students = await get_student_submissions(db, class_slug, hw["id"])
        pending_count = sum(1 for s in students if s["gradingStatus"] == "待批改")
        progress = round(((hw["submitted"] - pending_count) / hw["submitted"]) * 100) if hw["submitted"] > 0 else 0
        tasks.append({
            "id": f"hw-{class_slug}-{hw['id']}",
            "type": "homework-grading",
            "title": f"批改：{hw['title']}",
            "homeworkId": hw["id"],
            "classId": class_slug,
            "status": "pending" if pending_count > 0 else "completed",
            "progress": progress,
            "progressLabel": f"已批改 {hw['submitted'] - pending_count}/{hw['submitted']} 份",
            "pendingCount": pending_count,
            "submitted": hw["submitted"],
            "createdAt": hw["date"],
            "priority": "high" if pending_count > 5 else "medium",
        })
    return tasks


async def get_alert_students(db: AsyncSession, class_slug: str) -> List[dict]:
    homework_list = await get_homework_list(db, class_slug)
    latest_pending = next((h for h in homework_list if h["status"] == "待批改"), None)
    if not latest_pending:
        return [
            {"name": "吴九", "score": 55, "trend": "down", "warning": "近期平均分低于60分"},
            {"name": "孙七", "score": 58, "trend": "down", "warning": "错题率持续偏高"},
        ]

    students = await get_student_submissions(db, class_slug, latest_pending["id"])
    not_submitted = [s for s in students if s["submitStatus"] == "未提交"]
    return [
        {
            "name": s["name"],
            "score": None,
            "trend": "down",
            "warning": "未提交当前作业" if idx == 0 else "作业提交逾期",
        }
        for idx, s in enumerate(not_submitted[:3])
    ]


async def update_assignment_status(db: AsyncSession, assignment_id: int) -> None:
    result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.assignment_id == assignment_id)
    )
    submissions = result.scalars().all()
    if not submissions:
        return

    pending = sum(1 for s in submissions if s.grading_status == "待批改")
    assign_result = await db.execute(
        select(HomeworkAssignment).where(HomeworkAssignment.id == assignment_id)
    )
    assignment = assign_result.scalar_one_or_none()
    if not assignment:
        return

    if pending == 0:
        assignment.status = "已批改"
        scores = [s.score for s in submissions if s.score is not None]
        if scores:
            assignment.avg_score = round(sum(scores) / len(scores), 1)
    else:
        assignment.status = "待批改"


async def sync_wrong_questions(
    db: AsyncSession,
    grading_result: dict,
    student_name: str,
    subject: str = "数学",
) -> int:
    """将批改错题同步到错题本"""
    count = 0
    for q in grading_result.get("questions", []):
        if q.get("is_correct", True):
            continue
        db.add(WrongQuestion(
            user_id=1,
            question_text=q.get("question_text", ""),
            user_answer=q.get("student_answer", ""),
            correct_answer=q.get("correct_answer", ""),
            knowledge_point=f"作业批改-{student_name}",
            subject=subject,
            variant_questions=json.dumps([], ensure_ascii=False),
        ))
        count += 1
    return count
