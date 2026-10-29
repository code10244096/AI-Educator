"""
数据库迁移脚本 - 添加新字段
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from database import engine


async def migrate_database():
    """添加新字段到现有表"""
    async with engine.begin() as conn:
        # 添加 teaching_tips 字段
        try:
            await conn.execute(text("ALTER TABLE question_bank ADD COLUMN teaching_tips TEXT"))
            print("✓ 添加 teaching_tips 字段")
        except Exception as e:
            print(f"teaching_tips 字段可能已存在: {e}")
        
        # 添加 common_mistakes 字段
        try:
            await conn.execute(text("ALTER TABLE question_bank ADD COLUMN common_mistakes TEXT"))
            print("✓ 添加 common_mistakes 字段")
        except Exception as e:
            print(f"common_mistakes 字段可能已存在: {e}")

        await _add_column_if_missing(conn, "lesson_plans", "grade", "VARCHAR(20)")
        await _add_column_if_missing(conn, "lesson_plans", "referenced_question_ids", "TEXT")
    
    print("迁移完成！")


async def _add_column_if_missing(conn, table: str, column: str, spec: str) -> None:
    """SQLite ALTER TABLE ADD COLUMN；列已存在则跳过。"""
    rows = (await conn.execute(text(f"PRAGMA table_info('{table}')"))).fetchall()
    names = {row[1] for row in rows}
    if column in names:
        print(f"{table}.{column} 已存在，跳过")
        return
    try:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {spec}"))
        print(f"✓ 添加 {table}.{column}")
    except Exception as e:
        print(f"{table}.{column} 添加失败或已存在: {e}")


if __name__ == "__main__":
    asyncio.run(migrate_database())
