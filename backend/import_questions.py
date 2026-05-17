"""
题库导入脚本
将爬取的题目导入到数据库
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import AsyncSessionLocal, init_db
from models import QuestionBank


async def import_questions_from_json(json_file: str):
    """从 JSON 文件导入题目"""
    with open(json_file, 'r', encoding='utf-8') as f:
        questions_data = json.load(f)
    
    async with AsyncSessionLocal() as db:
        added_count = 0
        
        for q_data in questions_data:
            question = QuestionBank(
                question_text=q_data.get("question_text"),
                answer=q_data.get("answer"),
                solution=q_data.get("solution", ""),
                question_type=q_data.get("question_type"),
                subject=q_data.get("subject", "数学"),
                education_level=q_data.get("education_level", "高中"),
                exam_type=q_data.get("exam_type", "高考"),
                year=q_data.get("year"),
                region=q_data.get("region", ""),
                knowledge_points=json.dumps(q_data.get("knowledge_points", []), ensure_ascii=False),
                difficulty=q_data.get("difficulty", 3),
                score=q_data.get("score"),
                source_url=q_data.get("source_url", ""),
                teaching_tips=q_data.get("teaching_tips", ""),
                common_mistakes=q_data.get("common_mistakes", ""),
                is_verified=True
            )
            
            db.add(question)
            added_count += 1
        
        await db.commit()
        print(f"成功导入 {added_count} 道题目")


async def import_sample_questions():
    """导入示例题目"""
    sample_questions = [
        {
            "question_text": "（2024年全国卷）已知集合 A = {x | x² - 3x + 2 = 0}，B = {x | x² - ax + a - 1 = 0}，若 A ∪ B = A，求实数 a 的值。",
            "answer": "a = 2 或 a = 3",
            "solution": "解：由 x² - 3x + 2 = 0 得 x = 1 或 x = 2，所以 A = {1, 2}。\n\n由 A ∪ B = A 可知 B ⊆ A。\n\n当 B = ∅ 时，Δ = a² - 4(a-1) < 0，解得 a 无解。\n\n当 B ≠ ∅ 时，B 的元素只能是 1 或 2。\n\n若 1 ∈ B，则 1 - a + a - 1 = 0，恒成立。\n若 2 ∈ B，则 4 - 2a + a - 1 = 0，解得 a = 3。\n\n综上，a = 2 或 a = 3。",
            "question_type": "解答题",
            "subject": "数学",
            "education_level": "高中",
            "exam_type": "高考",
            "year": 2024,
            "region": "全国卷",
            "knowledge_points": ["集合", "函数"],
            "difficulty": 3,
            "score": 12.0,
            "source_url": ""
        },
        {
            "question_text": "（2024年全国卷）已知函数 f(x) = x³ - 3x² + 2，求 f(x) 的单调区间和极值。",
            "answer": "单调递增区间：(-∞, 0) 和 (2, +∞)；单调递减区间：(0, 2)；极大值 f(0) = 2，极小值 f(2) = -2",
            "solution": "解：f'(x) = 3x² - 6x = 3x(x - 2)\n\n令 f'(x) = 0，得 x = 0 或 x = 2\n\n当 x < 0 时，f'(x) > 0，f(x) 单调递增\n当 0 < x < 2 时，f'(x) < 0，f(x) 单调递减\n当 x > 2 时，f'(x) > 0，f(x) 单调递增\n\n所以单调递增区间为 (-∞, 0) 和 (2, +∞)，单调递减区间为 (0, 2)\n\n极大值 f(0) = 2，极小值 f(2) = -2",
            "question_type": "解答题",
            "subject": "数学",
            "education_level": "高中",
            "exam_type": "高考",
            "year": 2024,
            "region": "全国卷",
            "knowledge_points": ["导数", "函数"],
            "difficulty": 4,
            "score": 12.0,
            "source_url": ""
        },
        {
            "question_text": "（2023年全国卷）在等差数列 {an} 中，a₁ = 2，a₃ + a₅ = 16，求数列 {an} 的通项公式和前 n 项和 Sn。",
            "answer": "an = 2n，Sn = n(n + 1)",
            "solution": "解：设公差为 d\n\na₃ = a₁ + 2d = 2 + 2d\na₅ = a₁ + 4d = 2 + 4d\n\n由 a₃ + a₅ = 16 得：\n(2 + 2d) + (2 + 4d) = 16\n4 + 6d = 16\n6d = 12\nd = 2\n\n所以 an = a₁ + (n-1)d = 2 + (n-1)×2 = 2n\n\nSn = n(a₁ + an)/2 = n(2 + 2n)/2 = n(n + 1)",
            "question_type": "解答题",
            "subject": "数学",
            "education_level": "高中",
            "exam_type": "高考",
            "year": 2023,
            "region": "全国卷",
            "knowledge_points": ["数列", "等差数列"],
            "difficulty": 3,
            "score": 12.0,
            "source_url": ""
        }
    ]
    
    async with AsyncSessionLocal() as db:
        for q_data in sample_questions:
            question = QuestionBank(
                question_text=q_data["question_text"],
                answer=q_data["answer"],
                solution=q_data["solution"],
                question_type=q_data["question_type"],
                subject=q_data["subject"],
                education_level=q_data["education_level"],
                exam_type=q_data["exam_type"],
                year=q_data["year"],
                region=q_data["region"],
                knowledge_points=json.dumps(q_data["knowledge_points"], ensure_ascii=False),
                difficulty=q_data["difficulty"],
                score=q_data["score"],
                source_url=q_data["source_url"],
                is_verified=True
            )
            
            db.add(question)
        
        await db.commit()
        print(f"成功导入 {len(sample_questions)} 道示例题目")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="题库导入脚本")
    parser.add_argument("--file", type=str, help="JSON 文件路径")
    parser.add_argument("--sample", action="store_true", help="导入示例题目")
    
    args = parser.parse_args()
    
    async def main():
        await init_db()
        
        if args.file:
            await import_questions_from_json(args.file)
        elif args.sample:
            await import_sample_questions()
        else:
            print("用法:")
            print("  python import_questions.py --file questions.json  # 从 JSON 文件导入")
            print("  python import_questions.py --sample                # 导入示例题目")
    
    asyncio.run(main())
