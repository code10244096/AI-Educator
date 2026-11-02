"""题库管理 API"""
import json
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from bank_subjects import BANK_STAGES, BANK_SUBJECTS, SEARCH_SYNONYMS
from database import get_db
from models import QuestionBank, QuestionVariant

router = APIRouter()


def _known_subjects(extra) -> list:
    seen = set()
    ordered = []
    for name in (*BANK_SUBJECTS, *(extra or [])):
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered

LIST_MAX_LIMIT = 200
LIST_MAX_OFFSET = 10000
SEARCH_MAX_LIMIT = 50


def clamp_limit(limit: Optional[int], default: int = 20, max_limit: int = LIST_MAX_LIMIT) -> int:
    try:
        value = int(limit) if limit is not None else default
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, max_limit))


def clamp_offset(offset: Optional[int], max_offset: int = LIST_MAX_OFFSET) -> int:
    try:
        value = int(offset) if offset is not None else 0
    except (TypeError, ValueError):
        value = 0
    return max(0, min(value, max_offset))


def _apply_list_filters(
    query: Select,
    *,
    subject: Optional[str] = None,
    education_level: Optional[str] = None,
    grade: Optional[int] = None,
    exam_type: Optional[str] = None,
    year: Optional[int] = None,
    question_type: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    difficulty: Optional[int] = None,
    is_verified: Optional[bool] = None,
) -> Select:
    if subject:
        query = query.where(QuestionBank.subject == subject)
    if education_level:
        query = query.where(QuestionBank.education_level == education_level)
    if grade:
        query = query.where(QuestionBank.grade == grade)
    if exam_type:
        query = query.where(QuestionBank.exam_type == exam_type)
    if year:
        query = query.where(QuestionBank.year == year)
    if question_type:
        query = query.where(QuestionBank.question_type == question_type)
    if knowledge_point:
        query = query.where(QuestionBank.knowledge_points.like(f"%{knowledge_point}%"))
    if difficulty:
        query = query.where(QuestionBank.difficulty == difficulty)
    if is_verified is not None:
        query = query.where(QuestionBank.is_verified == is_verified)
    return query


def keyset_after_cursor(created_at, question_id: int):
    """(created_at DESC, id DESC) 的下一页条件。

    存储精度混杂：server_default=func.now() 存 'YYYY-MM-DD HH:MM:SS'（无微秒），
    ORM 显式写入带微秒。驱动再把 datetime 参数转成带微秒的字符串直接比较会出错
    （'...29' < '...29.000000' 恒真，游标行被漏回第一页）。
    统一用 SQLite datetime() 归一化到秒后比较，同秒内顺序由自增 id 兜底。
    """
    normalized = func.datetime(QuestionBank.created_at)
    if created_at is None:
        return and_(QuestionBank.created_at.is_(None), QuestionBank.id < question_id)
    ts = created_at.strftime("%Y-%m-%d %H:%M:%S")
    return or_(
        normalized < ts,
        and_(normalized == ts, QuestionBank.id < question_id),
    )


def build_list_query(
    *,
    subject: Optional[str] = None,
    education_level: Optional[str] = None,
    grade: Optional[int] = None,
    exam_type: Optional[str] = None,
    year: Optional[int] = None,
    question_type: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    difficulty: Optional[int] = None,
    is_verified: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    after_id: Optional[int] = None,
    cursor: Optional[Tuple] = None,
) -> Select:
    query = _apply_list_filters(
        select(QuestionBank),
        subject=subject,
        education_level=education_level,
        grade=grade,
        exam_type=exam_type,
        year=year,
        question_type=question_type,
        knowledge_point=knowledge_point,
        difficulty=difficulty,
        is_verified=is_verified,
    )
    query = query.order_by(QuestionBank.created_at.desc(), QuestionBank.id.desc())
    if after_id is not None and cursor is not None:
        query = query.where(keyset_after_cursor(cursor[0], cursor[1]))
        return query.limit(clamp_limit(limit))
    return query.offset(clamp_offset(offset)).limit(clamp_limit(limit))


def expand_search_terms(token: str) -> list:
    """命中 SEARCH_SYNONYMS 时展开为同义词列表；未命中则原词。大小写不敏感。"""
    text = (token or "").strip()
    if not text:
        return []
    lowered = text.lower()
    for key, synonyms in SEARCH_SYNONYMS.items():
        if key.lower() == lowered:
            seen = set()
            ordered = []
            for item in synonyms:
                name = (item or "").strip()
                if not name:
                    continue
                mark = name.lower()
                if mark not in seen:
                    seen.add(mark)
                    ordered.append(name)
            return ordered or [text]
    return [text]


def _like_any_field(term: str):
    """question_text / knowledge_points / search_keywords 任一字段 LIKE。

    SQLite LIKE 对 ASCII 默认不区分大小写，sin/cos 等英文词无需再套 LOWER()。
    """
    pattern = f"%{term}%"
    return or_(
        QuestionBank.question_text.like(pattern),
        QuestionBank.knowledge_points.like(pattern),
        QuestionBank.search_keywords.like(pattern),
    )


def _token_match_clause(token: str):
    terms = expand_search_terms(token)
    if not terms:
        return None
    if len(terms) == 1:
        return _like_any_field(terms[0])
    return or_(*(_like_any_field(term) for term in terms))


def build_search_query(
    keyword: str,
    *,
    subject: Optional[str] = None,
    education_level: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
) -> Select:
    """多字段 LIKE；空格分词后词间 AND；同义词组内 OR；知识点命中优先。"""
    query = select(QuestionBank)
    if subject:
        query = query.where(QuestionBank.subject == subject)
    if education_level:
        query = query.where(QuestionBank.education_level == education_level)

    tokens = [part for part in (keyword or "").split() if part.strip()]
    token_clauses = []
    rank_terms = []
    for token in tokens:
        clause = _token_match_clause(token)
        if clause is not None:
            token_clauses.append(clause)
            rank_terms.extend(expand_search_terms(token))
    if token_clauses:
        query = query.where(and_(*token_clauses) if len(token_clauses) > 1 else token_clauses[0])

    if rank_terms:
        kp_hit = or_(*(QuestionBank.knowledge_points.like(f"%{term}%") for term in rank_terms))
        text_hit = or_(*(QuestionBank.question_text.like(f"%{term}%") for term in rank_terms))
        relevance = case((kp_hit, 0), (text_hit, 1), else_=2)
        query = query.order_by(relevance, QuestionBank.id.desc())
    else:
        query = query.order_by(QuestionBank.id.desc())
    return query.offset(clamp_offset(offset)).limit(clamp_limit(limit, default=10, max_limit=SEARCH_MAX_LIMIT))


# ==================== 题库管理 API ====================

@router.post("/questionbank/add")
async def add_question(
    question_text: str = Form(...),
    answer: str = Form(...),
    solution: str = Form(""),
    question_type: str = Form(...),
    subject: str = Form(...),
    education_level: str = Form(...),
    exam_type: str = Form(""),
    year: int = Form(None),
    region: str = Form(""),
    knowledge_points: str = Form(""),  # JSON 字符串
    difficulty: int = Form(3),
    score: float = Form(None),
    source_url: str = Form(""),
    teaching_tips: str = Form(""),
    common_mistakes: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """添加题目到题库"""
    question = QuestionBank(
        question_text=question_text,
        answer=answer,
        solution=solution,
        question_type=question_type,
        subject=subject,
        education_level=education_level,
        exam_type=exam_type,
        year=year,
        region=region,
        knowledge_points=knowledge_points,
        difficulty=difficulty,
        score=score,
        source_url=source_url,
        teaching_tips=teaching_tips,
        common_mistakes=common_mistakes,
        is_verified=True
    )
    
    db.add(question)
    await db.commit()
    await db.refresh(question)
    
    return {
        "id": question.id,
        "message": "题目添加成功"
    }


@router.post("/questionbank/batch-add")
async def batch_add_questions(
    questions: List[dict],
    db: AsyncSession = Depends(get_db)
):
    """批量添加题目（用于爬虫导入）"""
    added_count = 0
    
    for q_data in questions:
        question = QuestionBank(
            question_text=q_data.get("question_text"),
            answer=q_data.get("answer"),
            solution=q_data.get("solution", ""),
            question_type=q_data.get("question_type"),
            subject=q_data.get("subject"),
            education_level=q_data.get("education_level"),
            exam_type=q_data.get("exam_type", ""),
            year=q_data.get("year"),
            region=q_data.get("region", ""),
            knowledge_points=json.dumps(q_data.get("knowledge_points", []), ensure_ascii=False),
            difficulty=q_data.get("difficulty", 3),
            score=q_data.get("score"),
            source_url=q_data.get("source_url", ""),
            teaching_tips=q_data.get("teaching_tips", ""),
            common_mistakes=q_data.get("common_mistakes", ""),
            is_verified=False  # 爬虫导入的需要审核
        )
        
        db.add(question)
        added_count += 1
    
    await db.commit()
    
    return {
        "added_count": added_count,
        "message": f"成功添加 {added_count} 道题目"
    }


@router.get("/questionbank/list")
async def get_question_list(
    subject: Optional[str] = None,
    education_level: Optional[str] = None,
    grade: Optional[int] = None,
    exam_type: Optional[str] = None,
    year: Optional[int] = None,
    question_type: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    difficulty: Optional[int] = None,
    is_verified: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    after_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取题目列表（支持多条件筛选）。深分页用 after_id keyset；offset 上限 LIST_MAX_OFFSET。"""
    cursor = None
    if after_id is not None:
        cursor_row = (
            await db.execute(
                select(QuestionBank.created_at, QuestionBank.id).where(QuestionBank.id == after_id)
            )
        ).first()
        if cursor_row is not None:
            cursor = (cursor_row[0], cursor_row[1])

    query = build_list_query(
        subject=subject,
        education_level=education_level,
        grade=grade,
        exam_type=exam_type,
        year=year,
        question_type=question_type,
        knowledge_point=knowledge_point,
        difficulty=difficulty,
        is_verified=is_verified,
        limit=limit,
        offset=offset,
        after_id=after_id,
        cursor=cursor,
    )

    result = await db.execute(query)
    questions = result.scalars().all()
    
    return [
        {
            "id": q.id,
            "question_text": q.question_text,
            "answer": q.answer,
            "solution": q.solution,
            "question_type": q.question_type,
            "subject": q.subject,
            "education_level": q.education_level,
            "grade": q.grade,
            "exam_type": q.exam_type,
            "year": q.year,
            "region": q.region,
            "knowledge_points": json.loads(q.knowledge_points) if q.knowledge_points else [],
            "difficulty": q.difficulty,
            "score": q.score,
            "teaching_tips": q.teaching_tips,
            "common_mistakes": q.common_mistakes,
            "is_verified": q.is_verified,
            "created_at": q.created_at
        }
        for q in questions
    ]


@router.get("/questionbank/stats")
async def get_question_stats(db: AsyncSession = Depends(get_db)):
    """获取题库统计信息"""
    # 按学科统计
    subject_result = await db.execute(
        select(QuestionBank.subject, func.count(QuestionBank.id))
        .group_by(QuestionBank.subject)
    )
    subject_stats = dict(subject_result.all())
    
    # 按学龄统计
    level_result = await db.execute(
        select(QuestionBank.education_level, func.count(QuestionBank.id))
        .group_by(QuestionBank.education_level)
    )
    level_stats = dict(level_result.all())
    
    # 总数
    total_result = await db.execute(select(func.count(QuestionBank.id)))
    total = total_result.scalar()
    
    return {
        "total": total,
        "by_subject": subject_stats,
        "by_education_level": level_stats
    }


@router.get("/questionbank/subjects")
async def get_question_subjects(db: AsyncSession = Depends(get_db)):
    """题库合法学科/学段（固定露出语文/数学/英语/科学，并附上库内实际有题的学科）。"""
    subject_result = await db.execute(
        select(QuestionBank.subject, func.count(QuestionBank.id))
        .group_by(QuestionBank.subject)
    )
    by_subject = {name: count for name, count in subject_result.all() if name}
    return {
        "subjects": _known_subjects(by_subject.keys()),
        "education_levels": list(BANK_STAGES),
        "by_subject": by_subject,
    }


@router.get("/questionbank/{question_id}")
async def get_question_detail(question_id: int, db: AsyncSession = Depends(get_db)):
    """获取题目详情（包含变式题）"""
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.id == question_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    # 获取变式题
    variants_result = await db.execute(
        select(QuestionVariant).where(QuestionVariant.original_id == question_id)
    )
    variants = variants_result.scalars().all()
    
    return {
        "id": question.id,
        "question_text": question.question_text,
        "answer": question.answer,
        "solution": question.solution,
        "question_type": question.question_type,
        "subject": question.subject,
        "education_level": question.education_level,
        "grade": question.grade,
        "exam_type": question.exam_type,
        "year": question.year,
        "region": question.region,
        "knowledge_points": json.loads(question.knowledge_points) if question.knowledge_points else [],
        "difficulty": question.difficulty,
        "score": question.score,
        "source_url": question.source_url,
        "teaching_tips": question.teaching_tips,
        "common_mistakes": question.common_mistakes,
        "is_verified": question.is_verified,
        "variants": [
            {
                "id": v.id,
                "question_text": v.question_text,
                "answer": v.answer,
                "solution": v.solution,
                "variant_type": v.variant_type
            }
            for v in variants
        ]
    }


@router.post("/questionbank/search")
async def search_questions(
    keyword: str = Form(...),
    subject: Optional[str] = Form(None),
    education_level: Optional[str] = Form(None),
    limit: int = Form(10),
    offset: int = Form(0),
    db: AsyncSession = Depends(get_db)
):
    """搜索题目。多字段 LIKE + 空格分词 AND + 同义词 OR；两侧通配无法用 B-tree。offset 上限 LIST_MAX_OFFSET。"""
    query = build_search_query(
        keyword, subject=subject, education_level=education_level, limit=limit, offset=offset
    )

    result = await db.execute(query)
    questions = result.scalars().all()
    
    return [
        {
            "id": q.id,
            "question_text": q.question_text,
            "answer": q.answer,
            "solution": q.solution,
            "subject": q.subject,
            "education_level": q.education_level,
            "difficulty": q.difficulty
        }
        for q in questions
    ]
