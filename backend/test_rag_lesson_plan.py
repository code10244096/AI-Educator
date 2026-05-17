"""
测试题库RAG集成到教案生成
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import AsyncSessionLocal, init_db
from rag_retriever import QuestionRetriever
from ai_client import ai_client


async def test_rag_lesson_plan():
    """测试RAG检索+教案生成"""
    await init_db()
    
    # 测试课题
    topics = ["导数与函数单调性", "集合的运算", "三角函数"]
    
    for topic in topics:
        print(f"\n{'='*60}")
        print(f"测试课题: {topic}")
        print(f"{'='*60}")
        
        async with AsyncSessionLocal() as db:
            # 1. RAG检索相关题目
            retriever = QuestionRetriever()
            questions = await retriever.keyword_search(
                db=db,
                keyword=topic,
                subject="数学",
                education_level="高中",
                limit=5
            )
            
            print(f"\n检索到 {len(questions)} 道相关题目:")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q['question_text'][:50]}...")
                print(f"     知识点: {', '.join(q.get('knowledge_points', []))}")
                print(f"     难度: {'★' * q.get('difficulty', 3)}")
            
            # 2. 格式化为RAG上下文
            context = retriever.format_for_rag(questions)
            print(f"\nRAG上下文长度: {len(context)} 字符")
            
            # 3. 生成教案（带题库参考）
            print(f"\n正在生成教案...")
            try:
                lesson_plan = await ai_client.generate_lesson_plan(
                    topic=topic,
                    period="1 课时",
                    student_level="中等",
                    question_bank_context=context
                )
                print(f"\n✓ 教案生成成功，长度: {len(lesson_plan)} 字符")
                print(f"\n教案预览（前500字符）:")
                print(lesson_plan[:500])
            except Exception as e:
                print(f"\n✗ 教案生成失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_rag_lesson_plan())
