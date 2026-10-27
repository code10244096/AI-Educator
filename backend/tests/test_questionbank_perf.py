"""question_bank 索引 / 分页 / 迁移幂等。用小表验证结构，不依赖 27 万真实数据。"""
import sqlite3
from datetime import datetime

from sqlalchemy.dialects import sqlite

from database import QUESTION_BANK_INDEX_DDL, QUESTION_BANK_INDEX_NAMES, migrate_question_bank_indexes
from rag_retriever import (
    build_exam_type_query,
    build_keyword_query,
    build_knowledge_point_query,
)
from routers.questionbank import (
    LIST_MAX_LIMIT,
    LIST_MAX_OFFSET,
    SEARCH_MAX_LIMIT,
    build_list_query,
    build_search_query,
    clamp_limit,
    clamp_offset,
)


def _sql(query) -> str:
    return str(
        query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    ).upper()


def _index_names(path) -> set:
    con = sqlite3.connect(path)
    try:
        return {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='question_bank'"
            )
        }
    finally:
        con.close()


def test_question_bank_indexes_exist_on_app_db(app):
    from testenv import TEST_DB

    names = _index_names(TEST_DB)
    missing = set(QUESTION_BANK_INDEX_NAMES) - names
    assert not missing, f"sqlite_master 缺少索引: {missing}"


def test_index_migration_idempotent_on_tiny_table(tmp_path):
    db = tmp_path / "tiny_qb.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE question_bank ("
        "id INTEGER PRIMARY KEY, subject TEXT, education_level TEXT, grade INTEGER, "
        "exam_type TEXT, year INTEGER, question_type TEXT, difficulty INTEGER, "
        "created_at DATETIME, region TEXT)"
    )
    con.commit()
    for _ in range(2):
        for ddl in QUESTION_BANK_INDEX_DDL:
            con.execute(ddl)
        con.commit()
    names = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='question_bank'"
        )
    }
    con.close()
    assert set(QUESTION_BANK_INDEX_NAMES) <= names


def test_migrate_question_bank_indexes_twice_no_error(tmp_path):
    from sqlalchemy import create_engine

    db = tmp_path / "migrate_qb.db"
    engine = create_engine(f"sqlite:///{db.as_posix()}")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE question_bank (id INTEGER PRIMARY KEY, subject TEXT, "
            "education_level TEXT, grade INTEGER, exam_type TEXT, year INTEGER, "
            "question_type TEXT, difficulty INTEGER, created_at DATETIME, region TEXT)"
        )
        migrate_question_bank_indexes(conn)
        migrate_question_bank_indexes(conn)
    assert set(QUESTION_BANK_INDEX_NAMES) <= _index_names(db)
    engine.dispose()


async def test_init_db_index_migration_idempotent(app):
    import database

    await database.init_db()
    await database.init_db()
    from testenv import TEST_DB

    assert set(QUESTION_BANK_INDEX_NAMES) <= _index_names(TEST_DB)


def test_typical_queries_include_limit():
    list_sql = _sql(build_list_query(subject="数学", grade=12, limit=20, offset=0))
    assert "LIMIT" in list_sql

    search_sql = _sql(build_search_query("函数", subject="数学", education_level="高中", limit=10))
    assert "LIMIT" in search_sql

    kw_sql = _sql(build_keyword_query("函数", subject="数学", education_level="高中", limit=8))
    assert "LIMIT" in kw_sql

    kp_sql = _sql(build_knowledge_point_query(["函数"], subject="数学", limit=10))
    assert "LIMIT" in kp_sql

    exam_sql = _sql(build_exam_type_query("高考", year=2024, subject="数学", limit=20))
    assert "LIMIT" in exam_sql


def _compiled(query):
    return query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})


def test_list_query_clamps_deep_offset_and_limit():
    assert clamp_offset(999999) == LIST_MAX_OFFSET
    assert clamp_limit(5000) == LIST_MAX_LIMIT
    compiled = _compiled(build_list_query(subject="数学", grade=10, limit=5000, offset=999999))
    sql = str(compiled).upper()
    assert "LIMIT" in sql
    if f"LIMIT {LIST_MAX_LIMIT}" not in sql:
        assert LIST_MAX_LIMIT in getattr(compiled, "params", {}).values()
    if f"OFFSET {LIST_MAX_OFFSET}" not in sql:
        assert LIST_MAX_OFFSET in getattr(compiled, "params", {}).values()


def test_search_query_clamps_limit():
    compiled = _compiled(build_search_query("方程", limit=1000))
    sql = str(compiled).upper()
    assert "LIMIT" in sql
    if f"LIMIT {SEARCH_MAX_LIMIT}" not in sql:
        assert SEARCH_MAX_LIMIT in getattr(compiled, "params", {}).values()


def test_search_query_supports_offset():
    compiled = _compiled(build_search_query("方程", limit=20, offset=40))
    sql = str(compiled).upper()
    assert "OFFSET" in sql
    deep = _compiled(build_search_query("方程", offset=999999))
    deep_sql = str(deep).upper()
    if f"OFFSET {LIST_MAX_OFFSET}" not in deep_sql:
        assert LIST_MAX_OFFSET in getattr(deep, "params", {}).values()


def test_list_keyset_uses_limit_without_offset():
    compiled = build_list_query(
        subject="数学",
        after_id=5,
        cursor=(datetime(2024, 1, 1), 5),
        limit=20,
        offset=80,
    ).compile(dialect=sqlite.dialect())
    sql = str(compiled).upper()
    assert "LIMIT" in sql
    # sqlite 方言恒渲染 "LIMIT ? OFFSET ?"（pysqlite 限制），
    # 关键性质是 keyset 路径丢弃了调用方 offset=80，绑定的 offset 是 0/None。
    assert 80 not in list(compiled.params.values())
    assert "CREATED_AT" in sql


async def test_list_keyset_after_id_skips_cursor_row(client):
    marker = "PERFKEYSET"
    ids = []
    for i in range(3):
        r = await client.post(
            "/api/questionbank/add",
            data={
                "question_text": f"{marker} {i}",
                "answer": "1",
                "question_type": "填空题",
                "subject": "数学",
                "education_level": "高中",
            },
        )
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])

    first = (await client.get("/api/questionbank/list", params={"limit": 1})).json()
    assert first
    cursor_id = first[0]["id"]
    nxt = (
        await client.get(
            "/api/questionbank/list", params={"limit": 20, "after_id": cursor_id}
        )
    ).json()
    assert all(item["id"] != cursor_id for item in nxt)
