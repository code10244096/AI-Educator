"""
RAG 检索模块
用于从题库中检索相关题目，辅助 AI 生成教案和解答
"""
import json
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import QuestionBank


class QuestionRetriever:
    """题目检索器 - 支持多种检索策略"""
    
    def __init__(self):
        pass
    
    async def keyword_search(
        self,
        db: AsyncSession,
        keyword: str,
        subject: Optional[str] = None,
        education_level: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        关键词搜索
        
        参数:
            db: 数据库会话
            keyword: 搜索关键词
            subject: 学科筛选
            education_level: 学龄筛选
            limit: 返回数量
        """
        query = select(QuestionBank).where(
            QuestionBank.question_text.like(f"%{keyword}%")
        )
        
        if subject:
            query = query.where(QuestionBank.subject == subject)
        if education_level:
            query = query.where(QuestionBank.education_level == education_level)
        
        query = query.limit(limit)
        
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
                "knowledge_points": json.loads(q.knowledge_points) if q.knowledge_points else [],
                "difficulty": q.difficulty
            }
            for q in questions
        ]
    
    async def knowledge_point_search(
        self,
        db: AsyncSession,
        knowledge_points: List[str],
        subject: Optional[str] = None,
        education_level: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        知识点检索
        
        参数:
            db: 数据库会话
            knowledge_points: 知识点列表
            subject: 学科筛选
            education_level: 学龄筛选
            limit: 返回数量
        """
        query = select(QuestionBank)
        
        # 匹配任意一个知识点
        conditions = []
        for kp in knowledge_points:
            conditions.append(QuestionBank.knowledge_points.like(f"%{kp}%"))
        
        if conditions:
            from sqlalchemy import or_
            query = query.where(or_(*conditions))
        
        if subject:
            query = query.where(QuestionBank.subject == subject)
        if education_level:
            query = query.where(QuestionBank.education_level == education_level)
        
        query = query.limit(limit)
        
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
                "knowledge_points": json.loads(q.knowledge_points) if q.knowledge_points else [],
                "difficulty": q.difficulty
            }
            for q in questions
        ]
    
    async def exam_type_search(
        self,
        db: AsyncSession,
        exam_type: str,
        year: Optional[int] = None,
        region: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        考试类型检索（如高考真题）
        
        参数:
            db: 数据库会话
            exam_type: 考试类型（高考/中考等）
            year: 年份
            region: 地区
            subject: 学科
            limit: 返回数量
        """
        query = select(QuestionBank).where(
            QuestionBank.exam_type == exam_type
        )
        
        if year:
            query = query.where(QuestionBank.year == year)
        if region:
            query = query.where(QuestionBank.region == region)
        if subject:
            query = query.where(QuestionBank.subject == subject)
        
        query = query.order_by(QuestionBank.year.desc())
        query = query.limit(limit)
        
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
                "exam_type": q.exam_type,
                "year": q.year,
                "region": q.region,
                "knowledge_points": json.loads(q.knowledge_points) if q.knowledge_points else [],
                "difficulty": q.difficulty
            }
            for q in questions
        ]
    
    async def hybrid_search(
        self,
        db: AsyncSession,
        query_text: str,
        subject: Optional[str] = None,
        education_level: Optional[str] = None,
        knowledge_points: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        混合检索 - 结合多种策略
        
        参数:
            db: 数据库会话
            query_text: 查询文本
            subject: 学科
            education_level: 学龄
            knowledge_points: 知识点列表
            limit: 返回数量
        """
        results = []
        
        # 1. 关键词搜索
        keyword_results = await self.keyword_search(
            db, query_text, subject, education_level, limit
        )
        results.extend(keyword_results)
        
        # 2. 知识点搜索
        if knowledge_points:
            kp_results = await self.knowledge_point_search(
                db, knowledge_points, subject, education_level, limit
            )
            results.extend(kp_results)
        
        # 去重（按 ID）
        seen_ids = set()
        unique_results = []
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_results.append(r)
        
        return unique_results[:limit]
    
    def format_for_rag(self, questions: List[Dict]) -> str:
        """
        将检索结果格式化为 RAG 上下文
        
        参数:
            questions: 题目列表
        
        返回:
            格式化的文本，用于 AI 模型参考
        """
        if not questions:
            return "未找到相关题目。"
        
        context_parts = []
        
        for i, q in enumerate(questions, 1):
            part = f"""
题目 {i}:
{q['question_text']}

答案: {q['answer']}

解析: {q.get('solution', '暂无解析')}

知识点: {', '.join(q.get('knowledge_points', []))}
难度: {'★' * q.get('difficulty', 3)}
"""
            context_parts.append(part)
        
        return "\n".join(context_parts)


# 全局检索器实例
retriever = QuestionRetriever()
