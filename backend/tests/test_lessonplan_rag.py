"""教案 RAG v2：年级解析、降级链、关键词提取、接口回写。"""
import uuid

import database
from bank_subjects import parse_grade_number
from helpers import generate_plan
from jobs import extract_title_keywords, retrieve_question_context
from models import LessonPlan, QuestionBank
from routers.lessonplan import _plan_to_dict


def test_parse_grade_number():
    assert parse_grade_number("三年级") == 3
    assert parse_grade_number("初一") == 7
    assert parse_grade_number("高一") == 10
    assert parse_grade_number("12") == 12
    assert parse_grade_number("高三") == 12
    assert parse_grade_number("垃圾输入") is None
    assert parse_grade_number("") is None
    assert parse_grade_number(None) is None


def test_extract_title_keywords_strips_book_title_and_period():
    kws = extract_title_keywords("《秋天的雨》第一课时")
    assert "秋天的雨" in kws
    assert kws[0] == "秋天的雨第一课时"


async def _add_bank_q(*, text, subject="语文", education_level="小学", grade=None):
    async with database.AsyncSessionLocal() as db:
        q = QuestionBank(
            question_text=text,
            answer="略",
            question_type="填空题",
            subject=subject,
            education_level=education_level,
            grade=grade,
            knowledge_points='["阅读"]',
            difficulty=2,
        )
        db.add(q)
        await db.commit()
        await db.refresh(q)
        return q.id


async def test_retrieve_grade_hit_does_not_fallback(app):
    # 依赖 app（session 级）触发建表；否则测试库里没有 question_bank
    kw = f"GRD{uuid.uuid4().hex[:8]}"
    id_grade = await _add_bank_q(text=f"{kw} GRADE_HIT 秋天的雨", subject="语文",
                                 education_level="小学", grade=3)
    await _add_bank_q(text=f"{kw} STAGE_ONLY 秋天的雨", subject="语文",
                      education_level="小学", grade=5)
    await _add_bank_q(text=f"{kw} NULL_GRADE 秋天的雨", subject="语文",
                      education_level="小学", grade=None)

    async with database.AsyncSessionLocal() as db:
        rag = await retrieve_question_context(
            db, kw, subject="语文", education_level="小学", grade="三年级",
        )
    assert rag["count"] == 1
    assert rag["question_ids"] == [id_grade]
    assert "GRADE_HIT" in rag["context"]
    assert "STAGE_ONLY" not in rag["context"]
    assert "NULL_GRADE" not in rag["context"]
    assert f"[题库ID:{id_grade}]" in rag["context"]


async def test_retrieve_grade_miss_falls_to_subject_level(app):
    kw = f"FB{uuid.uuid4().hex[:8]}"
    id_stage = await _add_bank_q(text=f"{kw} STAGE_FALLBACK", subject="语文",
                                 education_level="小学", grade=5)
    async with database.AsyncSessionLocal() as db:
        rag = await retrieve_question_context(
            db, kw, subject="语文", education_level="小学", grade="四年级",
        )
    assert rag["count"] >= 1
    assert id_stage in rag["question_ids"]
    assert "STAGE_FALLBACK" in rag["context"]


async def test_retrieve_no_hit_returns_empty_without_error(app):
    async with database.AsyncSessionLocal() as db:
        rag = await retrieve_question_context(
            db, f"NOHIT{uuid.uuid4().hex}", subject="化学",
            education_level="高中", grade="高三",
        )
    assert rag["count"] == 0
    assert rag["question_ids"] == []
    assert rag["context"] in ("", "未找到相关题目。")


async def test_retrieve_keyword_from_decorated_title(app):
    marker = f"QT{uuid.uuid4().hex[:8]}"
    qid = await _add_bank_q(text=f"朗读课文秋天的雨 {marker}", subject="语文",
                            education_level="小学", grade=3)
    async with database.AsyncSessionLocal() as db:
        rag = await retrieve_question_context(
            db, "《秋天的雨》第一课时", subject="语文", education_level="小学", grade="三年级",
        )
    assert rag["count"] >= 1
    assert qid in rag["question_ids"]
    assert marker in rag["context"]


def test_plan_to_dict_includes_grade_and_referenced_ids():
    plan = LessonPlan(
        title="课题",
        grade="三年级",
        referenced_question_ids="[11, 22]",
        retrieved_questions_count=2,
    )
    data = _plan_to_dict(plan)
    assert data["grade"] == "三年级"
    assert data["referenced_question_ids"] == [11, 22]
    assert data["retrieved_questions_count"] == 2

    empty = _plan_to_dict(LessonPlan(title="空"))
    assert empty["grade"] == ""
    assert empty["referenced_question_ids"] == []

    broken = _plan_to_dict(LessonPlan(title="坏", referenced_question_ids="不是JSON"))
    assert broken["referenced_question_ids"] == []


async def test_generate_persists_grade_and_referenced_ids(client, fake_ai):
    marker = f"API{uuid.uuid4().hex[:8]}"
    qid = await _add_bank_q(text=f"{marker} 课堂练习题", subject="语文",
                            education_level="小学", grade=3)
    r, final = await generate_plan(client, {
        "title": marker, "subject": "语文", "grade": "三年级", "wait": "true",
    })
    assert r.status_code == 200, r.text
    assert final["grade"] == "三年级"
    assert "referenced_question_ids" in final
    assert isinstance(final["referenced_question_ids"], list)
    assert qid in final["referenced_question_ids"]
    assert final["retrieved_questions_count"] >= 1

    detail = (await client.get(f"/api/lessonplan/{final['id']}")).json()
    assert detail["grade"] == "三年级"
    assert qid in detail["referenced_question_ids"]
