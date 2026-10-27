"""
RAG 检索模块
用于从题库中检索相关题目，辅助 AI 生成教案和解答

全文检索取舍：题干/知识点是中文连续文本。FTS5 的 simple/unicode61 按空白和标点切词，
对中文几乎等同一整句一个 token，没有 jieba 一类分词就无法按「函数」「方程」命中。
当前需求是子串匹配（LIKE %kw%）。前导通配无法走 B-tree；前缀 kw% 会改变语义。
因此保持 LIKE，用 subject/education_level 等值条件缩小扫描范围，每条查询带 LIMIT。
"""
import json
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from sqlalchemy.sql import Select
from models import QuestionBank

SEARCH_MAX_LIMIT = 50


def clamp_search_limit(limit: Optional[int], default: int = 10) -> int:
    try:
        value = int(limit) if limit is not None else default
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, SEARCH_MAX_LIMIT))


def _eq_scope(query: Select, subject: Optional[str], education_level: Optional[str]) -> Select:
    if subject:
        query = query.where(QuestionBank.subject == subject)
    if education_level:
        query = query.where(QuestionBank.education_level == education_level)
    return query


def build_keyword_query(
    keyword: str,
    subject: Optional[str] = None,
    education_level: Optional[str] = None,
    limit: int = 10,
) -> Select:
    query = _eq_scope(select(QuestionBank), subject, education_level)
    query = query.where(QuestionBank.question_text.like(f"%{keyword}%"))
    return query.limit(clamp_search_limit(limit))


def build_knowledge_point_query(
    knowledge_points: List[str],
    subject: Optional[str] = None,
    education_level: Optional[str] = None,
    limit: int = 10,
) -> Select:
    query = _eq_scope(select(QuestionBank), subject, education_level)
    conditions = [QuestionBank.knowledge_points.like(f"%{kp}%") for kp in knowledge_points if kp]
    if conditions:
        query = query.where(or_(*conditions))
    return query.limit(clamp_search_limit(limit))


def build_exam_type_query(
    exam_type: str,
    year: Optional[int] = None,
    region: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = 20,
) -> Select:
    query = select(QuestionBank).where(QuestionBank.exam_type == exam_type)
    if year:
        query = query.where(QuestionBank.year == year)
    if region:
        query = query.where(QuestionBank.region == region)
    if subject:
        query = query.where(QuestionBank.subject == subject)
    return query.order_by(QuestionBank.year.desc()).limit(clamp_search_limit(limit, default=20))


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
        query = build_keyword_query(keyword, subject, education_level, limit)
        
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
        query = build_knowledge_point_query(
            knowledge_points, subject, education_level, limit
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
        query = build_exam_type_query(exam_type, year, region, subject, limit)
        
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
