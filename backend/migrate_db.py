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
    
    print("迁移完成！")


if __name__ == "__main__":
    asyncio.run(migrate_database())
