"""
题库验证脚本
验证已导入的高考数学真题数据
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import AsyncSessionLocal, init_db
from models import QuestionBank
from sqlalchemy import func


async def verify_database():
    """验证数据库中的题目数据"""
    print("="*60)
    print("题库数据验证")
    print("="*60)
    
    # 初始化数据库
    await init_db()
    
    async with AsyncSessionLocal() as db:
        # 1. 总题目数
        result = await db.execute(func.count(QuestionBank.id))
        total_count = result.scalar()
        print(f"\n总题目数: {total_count}")
        
        # 2. 按年份统计
        from sqlalchemy import text
        result = await db.execute(text(
            "SELECT year, COUNT(*) as count FROM question_bank GROUP BY year ORDER BY year"
        ))
        
        print(f"\n各年份题目数:")
        print("-"*60)
        
        # 使用原生SQL查询
        from sqlalchemy import text
        result = await db.execute(text(
            "SELECT year, COUNT(*) as count FROM question_bank GROUP BY year ORDER BY year"
        ))
        rows = result.fetchall()
        
        for row in rows:
            year = row[0]
            count = row[1]
            print(f"  {year}年: {count} 道题")
        
        # 3. 按题型统计
        result = await db.execute(text(
            "SELECT question_type, COUNT(*) as count FROM question_bank GROUP BY question_type"
        ))
        type_rows = result.fetchall()
        
        print(f"\n各题型题目数:")
        print("-"*60)
        for row in type_rows:
            print(f"  {row[0]}: {row[1]} 道题")
        
        # 4. 按地区统计
        result = await db.execute(text(
            "SELECT region, COUNT(*) as count FROM question_bank GROUP BY region ORDER BY region"
        ))
        region_rows = result.fetchall()
        
        print(f"\n各地区题目数:")
        print("-"*60)
        for row in region_rows:
            region = row[0] if row[0] else "未分类"
            print(f"  {region}: {row[1]} 道题")
        
        # 5. 示例题目展示
        print(f"\n示例题目 (2022年选择题):")
        print("-"*60)
        result = await db.execute(text(
            "SELECT question_text, answer, knowledge_points FROM question_bank WHERE year=2022 AND question_type='选择题' LIMIT 2"
        ))
        sample_rows = result.fetchall()
        
        for i, row in enumerate(sample_rows, 1):
            question_text = row[0][:100] + "..." if len(row[0]) > 100 else row[0]
            print(f"\n题目{i}:")
            print(f"  题目: {question_text}")
            print(f"  答案: {row[1]}")
            print(f"  知识点: {row[2]}")
        
        # 6. 数据来源统计
        result = await db.execute(text(
            "SELECT source_url, COUNT(*) as count FROM question_bank GROUP BY source_url"
        ))
        source_rows = result.fetchall()
        
        print(f"\n数据来源:")
        print("-"*60)
        for row in source_rows:
            source = row[0] if row[0] else "未知"
            print(f"  {source}: {row[1]} 道题")
    
    print("\n" + "="*60)
    print("验证完成！")
    print("="*60)


async def main():
    """主函数"""
    await verify_database()


if __name__ == "__main__":
    asyncio.run(main())
