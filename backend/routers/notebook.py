"""错题本：录入错题、列表、标记掌握、变式题"""
import asyncio
import json
import re
from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_client import ai_client
from auth import current_user
from database import get_db
from file_utils import FileParseError, extract_text, save_upload, validate_upload
from llm import LLMError
from models import User, WrongQuestion

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
    user: User = Depends(current_user),
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
    from trial_quota import TrialLimited, enforce
    await enforce(user, "variant", db)
    saved = await save_upload(file, ext)
    filepath = saved["path"]

    try:
        text_content = await extract_text(filepath, ext, task_meta={"feature_source": "notebook", "teacher_id": user.id})
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
            subject=subject,
            task_meta={"teacher_id": user.id, "feature_source": "notebook", "subject": subject},
        )
    except TrialLimited:
        raise
    except Exception:  # noqa: BLE001  变式题失败不影响错题录入
        variant_questions = []

    wrong_question = WrongQuestion(
        user_id=user.id,
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
    user: User = Depends(current_user),
):
    """获取错题列表（返回数组，按录入时间倒序）"""
    query = select(WrongQuestion).where(WrongQuestion.user_id == user.id)
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
async def get_notebook_stats(subject: Optional[str] = None, db: AsyncSession = Depends(get_db),
                             user: User = Depends(current_user)):
    """错题本统计：总数 / 已掌握 / 知识点分布"""
    base = select(WrongQuestion).where(WrongQuestion.user_id == user.id)
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


@router.get("/notebook/frequent")
async def get_frequent_wrong_questions(
    subject: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """高频错题：按题目聚合历史批改同步进来的错题（含手动录入），
    统计出错次数、涉及学生数与最近出错时间，按频次倒序。"""
    query = select(WrongQuestion).where(WrongQuestion.user_id == user.id)
    if subject:
        query = query.where(WrongQuestion.subject == subject)
    rows = (await db.execute(query)).scalars().all()

    groups: Dict[str, dict] = {}
    for q in rows:
        text = (q.question_text or "").strip()
        if not text or text == "（无题目内容）":
            continue
        key = re.sub(r"\s+", "", text)[:150]
        g = groups.setdefault(key, {
            "question_text": text[:300],
            "knowledge_point": q.knowledge_point,
            "count": 0,
            "students": set(),
            "submissions": set(),
            "latest": None,
            "mastered_all": True,
            "ids": [],
        })
        g["count"] += 1
        g["ids"].append(q.id)
        if q.student_name:
            g["students"].add(q.student_name)
        if q.submission_id:
            g["submissions"].add(q.submission_id)
        if not q.is_mastered:
            g["mastered_all"] = False
        if q.error_date and (g["latest"] is None or q.error_date > g["latest"]):
            g["latest"] = q.error_date

    items = sorted(groups.values(), key=lambda g: (-g["count"], -len(g["students"])))
    out = []
    for g in items[:limit]:
        out.append({
            "question_text": g["question_text"],
            "knowledge_point": g["knowledge_point"],
            "count": g["count"],
            "student_count": len(g["students"]),
            "students": sorted(g["students"]),
            "submission_count": len(g["submissions"]),
            "latest_error_date": g["latest"].isoformat() if g["latest"] else None,
            "mastered_all": g["mastered_all"],
            "question_ids": g["ids"],
        })
    return {"total_groups": len(items), "items": out}


# 知识点归类规则（仅数学启用关键词表）：按优先级顺序匹配，命中第一个即归入该板块
_KNOWLEDGE_RULES = [
    ("三角函数", ["三角函数", "诱导公式", "同角三角", "正弦", "余弦", "正切函数", "三角恒等",
                  "两角和", "二倍角", "正弦定理", "余弦定理", "解三角形", "三角图象", "三角图像"]),
    ("立体几何", ["立体几何", "三视图", "空间几何体", "棱柱", "棱锥", "棱台", "圆柱",
                  "球", "异面直线", "二面角", "线面", "面面", "空间向量", "法向量", "展开图"]),
    ("圆锥曲线", ["椭圆", "双曲线", "抛物线", "圆锥曲线", "焦点", "离心率", "渐近线", "准线", "弦长"]),
    ("直线与圆", ["直线与圆", "圆的方程", "切线", "点到直线", "斜率", "倾斜角", "直线方程", "两直线"]),
    ("数列", ["数列", "等差", "等比", "通项", "前n项和", "前 n 项和", "递推"]),
    ("导数", ["导数", "求导", "导函数", "极值", "定积分", "微积分", "f′", "f'"]),
    ("排列组合与二项式定理", ["排列", "组合", "二项式", "种数", "选法", "展开式系数"]),
    ("概率与统计", ["概率", "统计", "随机", "抽样", "平均数", "中位数", "方差", "标准差", "频数",
                    "频率分布", "分层抽样", "样本", "期望", "分布列", "二项分布", "正态分布",
                    "古典概型", "几何概型", "众数", "极差", "茎叶图", "直方图", "回归", "独立性检验"]),
    ("平面向量", ["向量", "数量积", "基底"]),
    ("集合", ["集合", "子集", "并集", "交集", "补集", "∈", "∪", "∩"]),
    ("复数", ["复数", "虚数", "共轭", "z="]),
    ("不等式", ["不等式", "线性规划", "约束条件", "均值不等式", "基本不等式"]),
    ("函数", ["函数", "定义域", "值域", "单调", "奇偶", "周期", "指数", "对数", "幂函数",
              "零点", "f(x)", "解析式", "反函数"]),
    ("程序框图", ["程序框图", "算法", "框图"]),
]


def _classify_knowledge(subject: str, knowledge_point: str, question_text: str) -> str:
    """把一道错题归入知识板块。数学按关键词表；其他学科或关键词未命中时，
    取知识点描述的第一个分句作为板块名；都没有则归入「未标注知识点」。"""
    if (subject or "") == "数学":
        text = f"{knowledge_point or ''} {question_text or ''}"
        for category, keywords in _KNOWLEDGE_RULES:
            if any(k in text for k in keywords):
                return category
    if knowledge_point:
        first = re.split(r"[、，,；;]", knowledge_point.strip())[0].strip()
        if first:
            return first[:20]
    return "未标注知识点"


@router.get("/notebook/knowledge-clusters")
async def get_knowledge_clusters(
    subject: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """按知识板块归类错题：每个板块列出旗下错题，按题次倒序——板块题次越高越是薄弱点。"""
    query = select(WrongQuestion).where(WrongQuestion.user_id == user.id)
    if subject:
        query = query.where(WrongQuestion.subject == subject)
    rows = (await db.execute(query)).scalars().all()

    clusters: Dict[str, dict] = {}
    for q in rows:
        text = (q.question_text or "").strip()
        if not text or text == "（无题目内容）":
            continue
        category = _classify_knowledge(q.subject or "", q.knowledge_point or "", text)
        g = clusters.setdefault(category, {"category": category, "questions": {}})
        key = re.sub(r"\s+", "", text)[:150]
        item = g["questions"].setdefault(key, {
            "question_text": text[:300],
            "knowledge_point": q.knowledge_point,
            "error_date": q.error_date,
            "is_mastered": bool(q.is_mastered),
            "times": 0,
        })
        item["times"] += 1
        if q.error_date and (item["error_date"] is None or q.error_date > item["error_date"]):
            item["error_date"] = q.error_date
        item["is_mastered"] = item["is_mastered"] and bool(q.is_mastered)

    out = []
    for g in clusters.values():
        qs = sorted(g["questions"].values(),
                    key=lambda x: (-x["times"], -(x["error_date"].timestamp() if x["error_date"] else 0)))
        out.append({
            "category": g["category"],
            "count": len(qs),
            "errors": sum(i["times"] for i in qs),
            "mastered_count": sum(1 for i in qs if i["is_mastered"]),
            "questions": qs,
        })
    out.sort(key=lambda x: (-x["errors"], -x["count"], x["category"]))
    return {"total_categories": len(out),
            "total_questions": sum(g["count"] for g in out),
            "categories": out}


async def _get_question(db: AsyncSession, question_id: int, user_id: int) -> WrongQuestion:
    """取当前教师的错题；不存在或属于其他教师一律 404"""
    q = await db.get(WrongQuestion, question_id)
    if not q or q.user_id != user_id:
        raise HTTPException(status_code=404, detail="错题不存在")
    return q


@router.get("/notebook/{question_id}")
async def get_wrong_question(question_id: int, db: AsyncSession = Depends(get_db),
                             user: User = Depends(current_user)):
    """查询单道错题（含变式题），供前端在切页返回后轮询生成进度"""
    q = await _get_question(db, question_id, user.id)
    return _question_to_dict(q)


@router.post("/notebook/{question_id}/mastered")
async def mark_as_mastered(question_id: int, db: AsyncSession = Depends(get_db),
                           user: User = Depends(current_user)):
    """标记为已掌握"""
    q = await _get_question(db, question_id, user.id)
    q.is_mastered = True
    await db.commit()
    return {"message": "已标记为已掌握"}


@router.post("/notebook/{question_id}/unmastered")
async def mark_as_unmastered(question_id: int, db: AsyncSession = Depends(get_db),
                             user: User = Depends(current_user)):
    """取消已掌握标记"""
    q = await _get_question(db, question_id, user.id)
    q.is_mastered = False
    await db.commit()
    return {"message": "已取消掌握标记"}


@router.post("/notebook/{question_id}/variants")
async def generate_variants(question_id: int, count: int = Form(3), db: AsyncSession = Depends(get_db),
                            user: User = Depends(current_user)):
    """为错题（重新）生成变式题（同步调用 AI，约 20-60 秒）"""
    q = await _get_question(db, question_id, user.id)
    from trial_quota import enforce
    await enforce(user, "variant", db)
    count = max(1, min(count, 5))
    variants = await ai_client.generate_variant_questions(
        question_text=q.question_text, knowledge_point=q.knowledge_point or "", count=count,
        subject=q.subject or "",
        task_meta={"teacher_id": user.id, "wrong_question_id": q.id, "feature_source": "notebook",
                   "subject": q.subject or ""},
    )
    if not variants:
        raise HTTPException(status_code=502, detail="AI 未返回有效的变式题，请重试")
    q.variant_questions = json.dumps(variants, ensure_ascii=False)
    await db.commit()
    from user_archive import save_record
    try:
        await asyncio.to_thread(
            save_record, user.username, user.display_name or "", "variant", q.id,
            (q.knowledge_point or q.question_text or "变式题")[:80],
            {"question_text": q.question_text, "variants": variants},
        )
    except Exception:  # noqa: BLE001
        pass
    return {"id": q.id, "variant_questions": variants}


@router.delete("/notebook/{question_id}")
async def delete_wrong_question(question_id: int, db: AsyncSession = Depends(get_db),
                                user: User = Depends(current_user)):
    """删除错题"""
    q = await _get_question(db, question_id, user.id)
    await db.delete(q)
    await db.commit()
    return {"message": "错题已删除", "id": question_id}
