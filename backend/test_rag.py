"""
题库 RAG 检索测试
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import AsyncSessionLocal, init_db
from rag_retriever import retriever


async def test_rag_retrieval():
    """测试 RAG 检索功能"""
    await init_db()
    
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("测试 1: 关键词搜索 - '函数'")
        print("=" * 60)
        
        results = await retriever.keyword_search(
            db,
            keyword="函数",
            subject="数学",
            education_level="高中",
            limit=5
        )
        
        print(f"找到 {len(results)} 道题目:\n")
        for q in results:
            print(f"ID: {q['id']}")
            print(f"题目: {q['question_text'][:50]}...")
            print(f"知识点: {q['knowledge_points']}")
            print(f"难度: {'★' * q['difficulty']}")
            print("-" * 40)
        
        print("\n" + "=" * 60)
        print("测试 2: 知识点检索 - ['导数', '函数']")
        print("=" * 60)
        
        results = await retriever.knowledge_point_search(
            db,
            knowledge_points=["导数", "函数"],
            subject="数学",
            education_level="高中",
            limit=5
        )
        
        print(f"找到 {len(results)} 道题目:\n")
        for q in results:
            print(f"ID: {q['id']}")
            print(f"题目: {q['question_text'][:50]}...")
            print(f"知识点: {q['knowledge_points']}")
            print("-" * 40)
        
        print("\n" + "=" * 60)
        print("测试 3: 混合检索 - '集合'")
        print("=" * 60)
        
        results = await retriever.hybrid_search(
            db,
            query_text="集合",
            subject="数学",
            education_level="高中",
            knowledge_points=["集合"],
            limit=5
        )
        
        print(f"找到 {len(results)} 道题目:\n")
        for q in results:
            print(f"ID: {q['id']}")
            print(f"题目: {q['question_text'][:50]}...")
            print("-" * 40)
        
        print("\n" + "=" * 60)
        print("测试 4: RAG 上下文格式化")
        print("=" * 60)
        
        context = retriever.format_for_rag(results)
        print(context)


if __name__ == "__main__":
    asyncio.run(test_rag_retrieval())
