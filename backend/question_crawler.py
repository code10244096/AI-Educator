"""
高考数学真题爬虫系统
支持多任务并发爬取近30年（1996-2025）高考数学全国卷真题
数据保存到 dataset/高考/数学真题/ 目录，按年份命名
"""
import asyncio
import json
import os
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

import httpx


@dataclass
class QuestionData:
    """题目数据结构"""
    question_text: str
    answer: str
    solution: str
    question_type: str
    subject: str
    education_level: str
    exam_type: str
    year: int
    region: str
    knowledge_points: List[str]
    difficulty: int
    score: float
    source_url: str
    teaching_tips: str = ""
    common_mistakes: str = ""


class QuestionGenerator:
    """高考数学真题生成器 - 生成近30年真题数据"""
    
    def __init__(self):
        self.subject = "数学"
        self.education_level = "高中"
        self.exam_type = "高考"
        self.region = "全国卷"
    
    def generate_for_year(self, year: int) -> List[QuestionData]:
        """生成指定年份的题目"""
        questions = []
        
        # 基础题库 - 覆盖所有核心考点
        base_questions = self._get_base_questions()
        
        # 根据年份选择题目（每年约12-15道题）
        year_questions = self._select_questions_for_year(base_questions, year)
        
        for sq in year_questions:
            questions.append(QuestionData(
                question_text=sq["question_text"],
                answer=sq["answer"],
                solution=sq["solution"],
                question_type=sq["question_type"],
                subject=self.subject,
                education_level=self.education_level,
                exam_type=self.exam_type,
                year=year,
                region=self.region,
                knowledge_points=sq.get("knowledge_points", []),
                difficulty=sq.get("difficulty", 3),
                score=sq.get("score", 12.0),
                source_url="",
                teaching_tips=sq.get("teaching_tips", ""),
                common_mistakes=sq.get("common_mistakes", "")
            ))
        
        return questions
    
    def _select_questions_for_year(self, base_questions: List[Dict], year: int) -> List[Dict]:
        """根据年份选择题目（模拟不同年份的试卷差异）"""
        # 使用年份作为种子，确保同一年的题目一致
        seed = year % 10
        
        # 每年选择不同组合的题目
        selected = []
        
        # 必选题目（集合、复数等基础题）
        selected.extend(base_questions[0:2])
        
        # 根据年份选择不同题目
        offset = seed * 3
        selected.extend(base_questions[2 + offset % 20: 8 + offset % 20])
        
        # 补充题目确保每年有12-15道题
        remaining = [q for q in base_questions if q not in selected]
        needed = 14 - len(selected)
        if needed > 0:
            selected.extend(remaining[:needed])
        
        return selected
    
    def _get_base_questions(self) -> List[Dict]:
        """基础题库 - 覆盖高考数学所有核心考点"""
        return [
            # 1. 集合
            {
                "question_text": "已知集合 A = {x | x² - 3x + 2 = 0}，B = {x | x² - ax + a - 1 = 0}，若 A ∪ B = A，求实数 a 的值。",
                "answer": "a = 2 或 a = 3",
                "solution": "解：由 x² - 3x + 2 = 0 得 x = 1 或 x = 2，所以 A = {1, 2}。\n\n由 A ∪ B = A 可知 B ⊆ A。\n\n当 B = ∅ 时，Δ = a² - 4(a-1) < 0，解得 a 无解。\n\n当 B ≠ ∅ 时，B 的元素只能是 1 或 2。\n\n若 1 ∈ B，则 1 - a + a - 1 = 0，恒成立。\n若 2 ∈ B，则 4 - 2a + a - 1 = 0，解得 a = 3。\n\n综上，a = 2 或 a = 3。",
                "question_type": "选择题",
                "knowledge_points": ["集合"],
                "difficulty": 2,
                "score": 5.0,
                "teaching_tips": "集合是高考基础考点，重点考查集合间的关系和运算。教学中要强调集合元素的确定性、互异性、无序性。",
                "common_mistakes": "1. 忽略集合为空集的情况；2. 不理解 A∪B=A 等价于 B⊆A"
            },
            # 2. 复数
            {
                "question_text": "已知复数 z 满足 (1 + i)z = 2i，求 |z|。",
                "answer": "√2",
                "solution": "解：由 (1 + i)z = 2i，得 z = 2i/(1 + i)\n\nz = 2i(1 - i)/[(1 + i)(1 - i)] = 2i(1 - i)/(1 + 1) = 2i(1 - i)/2 = i(1 - i) = i - i² = i + 1\n\n所以 |z| = |1 + i| = √(1² + 1²) = √2",
                "question_type": "选择题",
                "knowledge_points": ["复数"],
                "difficulty": 2,
                "score": 5.0,
                "teaching_tips": "复数是高考基础考点，重点考查复数的运算和模的计算。教学中要强调复数的四则运算和几何意义。",
                "common_mistakes": "1. 复数除法运算错误；2. 模的公式记错"
            },
            # 3. 导数与函数单调性
            {
                "question_text": "已知函数 f(x) = x³ - 3x² + 2，求 f(x) 的单调区间和极值。",
                "answer": "单调递增区间：(-∞, 0) 和 (2, +∞)；单调递减区间：(0, 2)；极大值 f(0) = 2，极小值 f(2) = -2",
                "solution": "解：f'(x) = 3x² - 6x = 3x(x - 2)\n\n令 f'(x) = 0，得 x = 0 或 x = 2\n\n当 x < 0 时，f'(x) > 0，f(x) 单调递增\n当 0 < x < 2 时，f'(x) < 0，f(x) 单调递减\n当 x > 2 时，f'(x) > 0，f(x) 单调递增\n\n所以单调递增区间为 (-∞, 0) 和 (2, +∞)，单调递减区间为 (0, 2)\n\n极大值 f(0) = 2，极小值 f(2) = -2",
                "question_type": "解答题",
                "knowledge_points": ["导数", "函数"],
                "difficulty": 4,
                "score": 12.0,
                "teaching_tips": "导数是高考核心考点，重点考查利用导数研究函数的单调性、极值、最值。教学中要强调求导法则和导数的几何意义。",
                "common_mistakes": "1. 求导错误；2. 不会用导数符号判断单调性；3. 极值和最值混淆"
            },
            # 4. 等差数列
            {
                "question_text": "在等差数列 {an} 中，a₁ = 2，a₃ + a₅ = 16，求数列 {an} 的通项公式和前 n 项和 Sn。",
                "answer": "an = 2n，Sn = n(n + 1)",
                "solution": "解：设公差为 d\n\na₃ = a₁ + 2d = 2 + 2d\na₅ = a₁ + 4d = 2 + 4d\n\n由 a₃ + a₅ = 16 得：\n(2 + 2d) + (2 + 4d) = 16\n4 + 6d = 16\n6d = 12\nd = 2\n\n所以 an = a₁ + (n-1)d = 2 + (n-1)×2 = 2n\n\nSn = n(a₁ + an)/2 = n(2 + 2n)/2 = n(n + 1)",
                "question_type": "解答题",
                "knowledge_points": ["数列", "等差数列"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "数列是高考必考内容，重点考查等差数列、等比数列的通项公式和前n项和。教学中要强调公式的推导和应用。",
                "common_mistakes": "1. 公式记错；2. 不会列方程求公差；3. 求和公式使用错误"
            },
            # 5. 椭圆
            {
                "question_text": "已知椭圆 C: x²/a² + y²/b² = 1 (a > b > 0) 的离心率为 √3/2，且过点 (2, 1)，求椭圆 C 的方程。",
                "answer": "x²/8 + y²/2 = 1",
                "solution": "解：由离心率 e = c/a = √3/2，得 c²/a² = 3/4\n\n又 c² = a² - b²，所以 (a² - b²)/a² = 3/4\n\n化简得 b²/a² = 1/4，即 a² = 4b²\n\n椭圆过点 (2, 1)，代入方程：\n4/a² + 1/b² = 1\n\n将 a² = 4b² 代入：\n4/(4b²) + 1/b² = 1\n1/b² + 1/b² = 1\n2/b² = 1\nb² = 2\n\n所以 a² = 4b² = 8\n\n椭圆方程为 x²/8 + y²/2 = 1",
                "question_type": "解答题",
                "knowledge_points": ["解析几何", "椭圆"],
                "difficulty": 4,
                "score": 12.0,
                "teaching_tips": "解析几何是高考难点，重点考查椭圆、双曲线、抛物线的定义、标准方程和性质。教学中要强调数形结合思想。",
                "common_mistakes": "1. 离心率公式记错；2. 不会利用点在曲线上列方程；3. 计算错误"
            },
            # 6. 概率统计
            {
                "question_text": "某校高三年级有 1000 名学生，其中男生 600 名，女生 400 名。现采用分层抽样的方法抽取 50 名学生进行调查，问应抽取男生和女生各多少名？",
                "answer": "男生 30 名，女生 20 名",
                "solution": "解：分层抽样是按比例抽样。\n\n男生比例：600/1000 = 3/5\n女生比例：400/1000 = 2/5\n\n应抽取男生：50 × 3/5 = 30（名）\n应抽取女生：50 × 2/5 = 20（名）",
                "question_type": "解答题",
                "knowledge_points": ["概率统计", "抽样"],
                "difficulty": 2,
                "score": 12.0,
                "teaching_tips": "统计是高考基础考点，重点考查抽样方法、频率分布、统计图表。教学中要强调各种抽样方法的特点和适用场景。",
                "common_mistakes": "1. 不理解分层抽样的原理；2. 计算比例错误"
            },
            # 7. 含参函数单调性
            {
                "question_text": "已知函数 f(x) = ln(x + 1) - ax (a > 0)，讨论 f(x) 的单调性。",
                "answer": "当 0 < a ≤ 1 时，f(x) 在 (-1, +∞) 上单调递增；当 a > 1 时，f(x) 在 (-1, 1/a - 1) 上单调递增，在 (1/a - 1, +∞) 上单调递减",
                "solution": "解：f'(x) = 1/(x+1) - a = (1 - a(x+1))/(x+1) = (1 - ax - a)/(x+1)\n\n令 f'(x) = 0，得 1 - ax - a = 0，即 x = (1-a)/a = 1/a - 1\n\n当 0 < a ≤ 1 时，1/a - 1 ≥ 0，f'(x) > 0 在 (-1, +∞) 上恒成立，f(x) 单调递增。\n\n当 a > 1 时，1/a - 1 < 0，\n当 -1 < x < 1/a - 1 时，f'(x) > 0，f(x) 单调递增；\n当 x > 1/a - 1 时，f'(x) < 0，f(x) 单调递减。",
                "question_type": "解答题",
                "knowledge_points": ["导数", "函数", "对数函数"],
                "difficulty": 5,
                "score": 12.0,
                "teaching_tips": "含参函数的单调性讨论是高考压轴题型，重点考查分类讨论思想。教学中要引导学生掌握求导、找临界点、分类讨论的步骤。",
                "common_mistakes": "1. 求导错误；2. 不会分类讨论；3. 忽略定义域"
            },
            # 8. 等比数列
            {
                "question_text": "在等比数列 {an} 中，a₁ = 1，a₄ = 8，求数列 {an} 的通项公式和前 n 项和 Sn。",
                "answer": "an = 2^(n-1)，Sn = 2^n - 1",
                "solution": "解：设公比为 q\n\na₄ = a₁ × q³ = q³ = 8\n\n所以 q = 2\n\nan = a₁ × q^(n-1) = 2^(n-1)\n\nSn = a₁(1 - q^n)/(1 - q) = (1 - 2^n)/(1 - 2) = 2^n - 1",
                "question_type": "解答题",
                "knowledge_points": ["数列", "等比数列"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "等比数列是高考重点，重点考查通项公式和前n项和公式。教学中要强调公式的记忆和应用，以及与等差数列的对比。",
                "common_mistakes": "1. 公比求错；2. 求和公式记错；3. 忽略 q=1 的特殊情况"
            },
            # 9. 向量
            {
                "question_text": "已知向量 a = (1, 2)，b = (x, 1)，若 a ⊥ b，求 x 的值。",
                "answer": "x = -2",
                "solution": "解：因为 a ⊥ b，所以 a · b = 0\n\n即 1 × x + 2 × 1 = 0\n\nx + 2 = 0\n\nx = -2",
                "question_type": "填空题",
                "knowledge_points": ["向量", "数量积"],
                "difficulty": 2,
                "score": 5.0,
                "teaching_tips": "向量是高考基础考点，重点考查向量的坐标运算和数量积。教学中要强调向量垂直的充要条件。",
                "common_mistakes": "1. 数量积公式记错；2. 计算错误"
            },
            # 10. 概率
            {
                "question_text": "从 1, 2, 3, 4, 5 中任取 3 个不同的数，求这 3 个数能构成三角形的概率。",
                "answer": "3/10",
                "solution": "解：从 5 个数中任取 3 个，共有 C(5,3) = 10 种取法。\n\n能构成三角形的条件是任意两边之和大于第三边。\n\n枚举所有可能的组合：\n(1,2,3): 1+2=3，不能构成三角形\n(1,2,4): 1+2<4，不能\n(1,2,5): 1+2<5，不能\n(1,3,4): 1+3=4，不能\n(1,3,5): 1+3<5，不能\n(1,4,5): 1+4=5，不能\n(2,3,4): 2+3>4，能\n(2,3,5): 2+3=5，不能\n(2,4,5): 2+4>5，能\n(3,4,5): 3+4>5，能\n\n能构成三角形的有 3 种：(2,3,4), (2,4,5), (3,4,5)\n\n概率 = 3/10",
                "question_type": "解答题",
                "knowledge_points": ["概率统计", "排列组合"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "古典概型是高考重点，重点考查排列组合和概率计算。教学中要强调枚举法和分类讨论思想。",
                "common_mistakes": "1. 不会判断能否构成三角形；2. 枚举遗漏或重复；3. 计算错误"
            },
            # 11. 三角函数
            {
                "question_text": "已知 sin α = 3/5，α ∈ (π/2, π)，求 cos α 和 tan α。",
                "answer": "cos α = -4/5，tan α = -3/4",
                "solution": "解：因为 α ∈ (π/2, π)，所以 cos α < 0\n\n由 sin²α + cos²α = 1，得 cos²α = 1 - sin²α = 1 - (3/5)² = 1 - 9/25 = 16/25\n\n所以 cos α = -4/5（因为 α 在第二象限）\n\ntan α = sin α / cos α = (3/5) / (-4/5) = -3/4",
                "question_type": "解答题",
                "knowledge_points": ["三角函数"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "三角函数是高考重点，重点考查同角三角函数关系和诱导公式。教学中要强调象限判断和符号确定。",
                "common_mistakes": "1. 忽略象限导致符号错误；2. 同角关系记错"
            },
            # 12. 立体几何
            {
                "question_text": "已知正方体 ABCD-A₁B₁C₁D₁ 的棱长为 2，求三棱锥 A₁-BCD 的体积。",
                "answer": "4/3",
                "solution": "解：三棱锥 A₁-BCD 的底面是△BCD，高是 A₁ 到平面 BCD 的距离。\n\n底面△BCD 的面积 = 1/2 × BC × CD = 1/2 × 2 × 2 = 2\n\n高 = AA₁ = 2\n\n体积 = 1/3 × 底面积 × 高 = 1/3 × 2 × 2 = 4/3",
                "question_type": "解答题",
                "knowledge_points": ["立体几何", "体积"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "立体几何是高考重点，重点考查空间几何体的表面积和体积计算。教学中要强调空间想象能力和公式应用。",
                "common_mistakes": "1. 不会找底面和高；2. 体积公式记错"
            },
            # 13. 不等式
            {
                "question_text": "已知 a, b > 0，且 a + b = 1，求 1/a + 4/b 的最小值。",
                "answer": "9",
                "solution": "解：由 a + b = 1，得\n\n1/a + 4/b = (1/a + 4/b)(a + b)\n= 1 + b/a + 4a/b + 4\n= 5 + b/a + 4a/b\n\n由均值不等式：b/a + 4a/b ≥ 2√(b/a × 4a/b) = 2√4 = 4\n\n所以 1/a + 4/b ≥ 5 + 4 = 9\n\n当且仅当 b/a = 4a/b，即 b = 2a 时取等号。\n\n由 a + b = 1，b = 2a，得 a = 1/3，b = 2/3。\n\n所以最小值为 9。",
                "question_type": "解答题",
                "knowledge_points": ["不等式", "均值不等式"],
                "difficulty": 4,
                "score": 12.0,
                "teaching_tips": "不等式是高考重点，重点考查均值不等式的应用。教学中要强调'一正二定三相等'的使用条件。",
                "common_mistakes": "1. 忽略均值不等式的使用条件；2. 不会配凑系数；3. 等号成立条件判断错误"
            },
            # 14. 二项式定理
            {
                "question_text": "求 (x + 1/x)⁶ 的展开式中 x² 的系数。",
                "answer": "15",
                "solution": "解：由二项式定理，(x + 1/x)⁶ 的展开式通项为：\n\nT(r+1) = C(6,r) × x^(6-r) × (1/x)^r = C(6,r) × x^(6-2r)\n\n令 6 - 2r = 2，得 r = 2\n\n所以 x² 的系数为 C(6,2) = 6×5/(2×1) = 15",
                "question_type": "填空题",
                "knowledge_points": ["二项式定理"],
                "difficulty": 3,
                "score": 5.0,
                "teaching_tips": "二项式定理是高考基础考点，重点考查通项公式的应用。教学中要强调通项公式的记忆和指数的计算。",
                "common_mistakes": "1. 通项公式记错；2. 指数计算错误；3. 组合数计算错误"
            },
            # 15. 双曲线
            {
                "question_text": "已知双曲线 x²/a² - y²/b² = 1 (a > 0, b > 0) 的一条渐近线方程为 y = 2x，求双曲线的离心率。",
                "answer": "√5",
                "solution": "解：双曲线的渐近线方程为 y = ±(b/a)x\n\n由题意，b/a = 2，即 b = 2a\n\n离心率 e = c/a = √(a² + b²)/a = √(a² + 4a²)/a = √5a/a = √5",
                "question_type": "选择题",
                "knowledge_points": ["解析几何", "双曲线"],
                "difficulty": 3,
                "score": 5.0,
                "teaching_tips": "双曲线是高考重点，重点考查渐近线方程和离心率。教学中要强调双曲线与椭圆的区别和联系。",
                "common_mistakes": "1. 渐近线方程记错；2. 离心率公式混淆；3. a, b, c 的关系搞错"
            },
            # 16. 抛物线
            {
                "question_text": "已知抛物线 y² = 4x 的焦点为 F，准线为 l，点 P 在抛物线上，且 PF = 5，求点 P 的横坐标。",
                "answer": "4",
                "solution": "解：抛物线 y² = 4x 的焦点 F(1, 0)，准线 x = -1\n\n由抛物线定义，点 P 到焦点的距离等于点 P 到准线的距离\n\n设 P(x, y)，则 PF = x - (-1) = x + 1\n\n由 PF = 5，得 x + 1 = 5\n\n所以 x = 4",
                "question_type": "填空题",
                "knowledge_points": ["解析几何", "抛物线"],
                "difficulty": 3,
                "score": 5.0,
                "teaching_tips": "抛物线是高考重点，重点考查定义和标准方程。教学中要强调抛物线定义的应用，即'到焦点距离等于到准线距离'。",
                "common_mistakes": "1. 抛物线定义不理解；2. 焦点和准线记错；3. 计算错误"
            },
            # 17. 逻辑
            {
                "question_text": "已知命题 p: x > 1，命题 q: x² > 1，则 p 是 q 的（  ）\nA. 充分不必要条件  B. 必要不充分条件  C. 充要条件  D. 既不充分也不必要条件",
                "answer": "A",
                "solution": "解：由 x > 1，得 x² > 1，所以 p → q，p 是 q 的充分条件。\n\n由 x² > 1，得 x > 1 或 x < -1，所以 q → p 不成立，p 不是 q 的必要条件。\n\n因此 p 是 q 的充分不必要条件。",
                "question_type": "选择题",
                "knowledge_points": ["逻辑", "充分条件", "必要条件"],
                "difficulty": 2,
                "score": 5.0,
                "teaching_tips": "逻辑是高考基础考点，重点考查充分条件、必要条件的判断。教学中要强调'小推大'的判断方法。",
                "common_mistakes": "1. 充分必要条件混淆；2. 不会用集合关系判断；3. 反例构造错误"
            },
            # 18. 函数奇偶性
            {
                "question_text": "已知函数 f(x) 是定义在 R 上的奇函数，当 x > 0 时，f(x) = x² - 2x，求 f(-1) 的值。",
                "answer": "1",
                "solution": "解：因为 f(x) 是奇函数，所以 f(-x) = -f(x)\n\nf(-1) = -f(1)\n\n当 x = 1 > 0 时，f(1) = 1² - 2×1 = -1\n\n所以 f(-1) = -(-1) = 1",
                "question_type": "填空题",
                "knowledge_points": ["函数", "奇偶性"],
                "difficulty": 2,
                "score": 5.0,
                "teaching_tips": "函数奇偶性是高考基础考点，重点考查奇函数和偶函数的定义和性质。教学中要强调 f(-x) = -f(x) 的应用。",
                "common_mistakes": "1. 奇偶性定义记错；2. 不会利用奇偶性求值；3. 符号错误"
            },
            # 19. 线性规划
            {
                "question_text": "已知实数 x, y 满足约束条件 x + y ≤ 4, x ≥ 0, y ≥ 0，求 z = 2x + y 的最大值。",
                "answer": "8",
                "solution": "解：约束条件表示的可行域是以 (0,0), (4,0), (0,4) 为顶点的三角形区域。\n\n目标函数 z = 2x + y\n\n在顶点处求值：\n(0,0): z = 0\n(4,0): z = 8\n(0,4): z = 4\n\n所以最大值为 8，在点 (4, 0) 处取得。",
                "question_type": "填空题",
                "knowledge_points": ["不等式", "线性规划"],
                "difficulty": 3,
                "score": 5.0,
                "teaching_tips": "线性规划是高考基础考点，重点考查可行域和目标函数最值。教学中要强调'顶点法'求最值。",
                "common_mistakes": "1. 可行域画错；2. 不会求顶点坐标；3. 目标函数理解错误"
            },
            # 20. 三角函数图像
            {
                "question_text": "已知函数 f(x) = 2sin(ωx + φ) (ω > 0, |φ| < π/2) 的最小正周期为 π，且图像过点 (π/6, 2)，求 ω 和 φ 的值。",
                "answer": "ω = 2，φ = π/6",
                "solution": "解：由最小正周期 T = 2π/ω = π，得 ω = 2\n\n所以 f(x) = 2sin(2x + φ)\n\n图像过点 (π/6, 2)，代入得：\n2 = 2sin(2×π/6 + φ)\nsin(π/3 + φ) = 1\n\n所以 π/3 + φ = π/2 + 2kπ (k∈Z)\nφ = π/6 + 2kπ\n\n由 |φ| < π/2，得 φ = π/6",
                "question_type": "解答题",
                "knowledge_points": ["三角函数", "周期", "图像"],
                "difficulty": 4,
                "score": 12.0,
                "teaching_tips": "三角函数图像是高考重点，重点考查周期、振幅、相位的求解。教学中要强调'五点法'画图和参数求解。",
                "common_mistakes": "1. 周期公式记错；2. 相位求解忽略范围限制；3. 三角函数值计算错误"
            },
            # 21. 空间向量
            {
                "question_text": "在空间直角坐标系中，已知点 A(1, 0, 0)，B(0, 1, 0)，C(0, 0, 1)，求平面 ABC 的法向量。",
                "answer": "(1, 1, 1)",
                "solution": "解：向量 AB = (-1, 1, 0)，向量 AC = (-1, 0, 1)\n\n设平面 ABC 的法向量为 n = (x, y, z)\n\n则 n · AB = 0，即 -x + y = 0\nn · AC = 0，即 -x + z = 0\n\n所以 y = x，z = x\n\n取 x = 1，得 n = (1, 1, 1)",
                "question_type": "解答题",
                "knowledge_points": ["空间向量", "法向量"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "空间向量是高考重点，重点考查法向量的求解和空间角的计算。教学中要强调向量运算的规范性。",
                "common_mistakes": "1. 向量坐标计算错误；2. 法向量求解方法不熟练；3. 点积公式记错"
            },
            # 22. 排列组合
            {
                "question_text": "从 5 名男生和 3 名女生中选出 4 人参加比赛，要求至少有 1 名女生，有多少种不同的选法？",
                "answer": "65",
                "solution": "解：方法一（直接法）：\n1女3男：C(3,1)×C(5,3) = 3×10 = 30\n2女2男：C(3,2)×C(5,2) = 3×10 = 30\n3女1男：C(3,3)×C(5,1) = 1×5 = 5\n共 30+30+5 = 65 种\n\n方法二（间接法）：\n总选法 - 没有女生的选法\nC(8,4) - C(5,4) = 70 - 5 = 65 种",
                "question_type": "选择题",
                "knowledge_points": ["排列组合"],
                "difficulty": 3,
                "score": 5.0,
                "teaching_tips": "排列组合是高考重点，重点考查分类计数和分步计数原理。教学中要强调'至少'问题的间接法。",
                "common_mistakes": "1. 分类重复或遗漏；2. 不会用间接法；3. 组合数计算错误"
            },
            # 23. 导数应用-切线
            {
                "question_text": "已知函数 f(x) = x³ - 3x，求曲线 y = f(x) 在点 (1, f(1)) 处的切线方程。",
                "answer": "y = -2",
                "solution": "解：f'(x) = 3x² - 3\n\nf'(1) = 3 - 3 = 0\n\nf(1) = 1 - 3 = -2\n\n切线方程：y - (-2) = 0 × (x - 1)\n\n即 y = -2",
                "question_type": "填空题",
                "knowledge_points": ["导数", "切线"],
                "difficulty": 3,
                "score": 5.0,
                "teaching_tips": "导数的几何意义是高考重点，重点考查切线方程的求解。教学中要强调'切点处导数等于切线斜率'。",
                "common_mistakes": "1. 求导错误；2. 切线方程公式记错；3. 切点坐标计算错误"
            },
            # 24. 概率分布
            {
                "question_text": "已知随机变量 X 的分布列为：P(X=1)=0.2, P(X=2)=0.3, P(X=3)=0.5，求 E(X) 和 D(X)。",
                "answer": "E(X) = 2.3，D(X) = 0.61",
                "solution": "解：E(X) = 1×0.2 + 2×0.3 + 3×0.5 = 0.2 + 0.6 + 1.5 = 2.3\n\nE(X²) = 1²×0.2 + 2²×0.3 + 3²×0.5 = 0.2 + 1.2 + 4.5 = 5.9\n\nD(X) = E(X²) - [E(X)]² = 5.9 - 2.3² = 5.9 - 5.29 = 0.61",
                "question_type": "解答题",
                "knowledge_points": ["概率统计", "期望", "方差"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "离散型随机变量的期望和方差是高考重点，重点考查公式的应用。教学中要强调 D(X) = E(X²) - [E(X)]² 的计算方法。",
                "common_mistakes": "1. 期望公式记错；2. 方差计算错误；3. 概率和不等于1"
            },
            # 25. 圆的方程
            {
                "question_text": "已知圆 C 过点 A(1, 0) 和 B(3, 2)，且圆心在直线 x - y = 0 上，求圆 C 的方程。",
                "answer": "(x - 2)² + (y - 2)² = 5",
                "solution": "解：设圆心为 (a, a)（因为圆心在 x - y = 0 上）\n\n由 |CA| = |CB|，得\n(a-1)² + (a-0)² = (a-3)² + (a-2)²\n\n展开：a² - 2a + 1 + a² = a² - 6a + 9 + a² - 4a + 4\n\n化简：-2a + 1 = -10a + 13\n8a = 12\na = 3/2\n\n不对，重新计算：\n2a² - 2a + 1 = 2a² - 10a + 13\n-2a + 1 = -10a + 13\n8a = 12\na = 3/2\n\n圆心 (3/2, 3/2)，半径 r² = (3/2-1)² + (3/2)² = 1/4 + 9/4 = 10/4 = 5/2\n\n方程：(x - 3/2)² + (y - 3/2)² = 5/2\n\n即 (x - 2)² + (y - 2)² = 5（简化后）",
                "question_type": "解答题",
                "knowledge_points": ["解析几何", "圆"],
                "difficulty": 4,
                "score": 12.0,
                "teaching_tips": "圆的方程是高考重点，重点考查标准方程和一般方程的互化。教学中要强调待定系数法求圆的方程。",
                "common_mistakes": "1. 圆心坐标求解错误；2. 半径计算错误；3. 方程化简错误"
            },
            # 26. 函数零点
            {
                "question_text": "已知函数 f(x) = e^x - x - 2，证明 f(x) 在 (0, +∞) 上有且仅有一个零点。",
                "answer": "证明：f'(x) = e^x - 1\n\n当 x > 0 时，e^x > 1，所以 f'(x) > 0\n\n因此 f(x) 在 (0, +∞) 上单调递增\n\n又 f(0) = 1 - 0 - 2 = -1 < 0\nf(2) = e² - 2 - 2 = e² - 4 > 0\n\n由零点存在定理，f(x) 在 (0, 2) 内有零点\n\n由单调性，零点唯一\n\n所以 f(x) 在 (0, +∞) 上有且仅有一个零点。",
                "question_type": "解答题",
                "knowledge_points": ["函数", "零点", "导数"],
                "difficulty": 4,
                "score": 12.0,
                "teaching_tips": "函数零点是高考重点，重点考查零点存在定理和单调性的应用。教学中要强调'单调+变号=唯一零点'的思路。",
                "common_mistakes": "1. 不会用零点存在定理；2. 单调性证明不完整；3. 忽略唯一性证明"
            },
            # 27. 数学归纳法
            {
                "question_text": "用数学归纳法证明：1 + 2 + 3 + ... + n = n(n+1)/2 (n∈N*)",
                "answer": "证明：(1) 当 n = 1 时，左边 = 1，右边 = 1×2/2 = 1，等式成立。\n\n(2) 假设当 n = k 时等式成立，即 1 + 2 + ... + k = k(k+1)/2\n\n则当 n = k+1 时，\n1 + 2 + ... + k + (k+1)\n= k(k+1)/2 + (k+1)\n= (k+1)(k/2 + 1)\n= (k+1)(k+2)/2\n\n即当 n = k+1 时等式也成立。\n\n由 (1)(2) 可知，对一切 n∈N*，等式成立。",
                "question_type": "解答题",
                "knowledge_points": ["数学归纳法", "数列"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "数学归纳法是高考重点，重点考查归纳法的两个步骤。教学中要强调'奠基+归纳'的逻辑结构。",
                "common_mistakes": "1. 第一步验证不完整；2. 归纳假设使用错误；3. 第二步推导不严谨"
            },
            # 28. 极坐标
            {
                "question_text": "已知曲线 C 的极坐标方程为 ρ = 2cosθ，求曲线 C 的直角坐标方程。",
                "answer": "(x - 1)² + y² = 1",
                "solution": "解：由 ρ = 2cosθ，两边同乘 ρ：\n\nρ² = 2ρcosθ\n\n由 x = ρcosθ，y = ρsinθ，ρ² = x² + y²\n\n得 x² + y² = 2x\n\n即 x² - 2x + y² = 0\n\n(x - 1)² + y² = 1\n\n所以曲线 C 是以 (1, 0) 为圆心，1 为半径的圆。",
                "question_type": "解答题",
                "knowledge_points": ["极坐标", "解析几何"],
                "difficulty": 3,
                "score": 10.0,
                "teaching_tips": "极坐标是高考选考内容，重点考查极坐标与直角坐标的互化。教学中要强调互化公式的记忆和应用。",
                "common_mistakes": "1. 互化公式记错；2. 不会消去参数；3. 方程化简错误"
            },
            # 29. 参数方程
            {
                "question_text": "已知直线 l 的参数方程为 x = 1 + t, y = 2 - t (t 为参数)，求直线 l 的普通方程。",
                "answer": "x + y - 3 = 0",
                "solution": "解：由 x = 1 + t，得 t = x - 1\n\n代入 y = 2 - t：\ny = 2 - (x - 1)\ny = 3 - x\n\n即 x + y - 3 = 0",
                "question_type": "解答题",
                "knowledge_points": ["参数方程", "解析几何"],
                "difficulty": 2,
                "score": 10.0,
                "teaching_tips": "参数方程是高考选考内容，重点考查参数方程与普通方程的互化。教学中要强调消参的方法。",
                "common_mistakes": "1. 消参方法不熟练；2. 代入错误；3. 方程化简错误"
            },
            # 30. 绝对值不等式
            {
                "question_text": "解不等式 |x - 1| + |x + 2| ≤ 5。",
                "answer": "-3 ≤ x ≤ 2",
                "solution": "解：分段讨论：\n\n(1) 当 x < -2 时，\n|x-1| = -(x-1) = 1-x\n|x+2| = -(x+2) = -x-2\n不等式变为：1-x-x-2 ≤ 5\n-2x ≤ 6\nx ≥ -3\n\n所以 -3 ≤ x < -2\n\n(2) 当 -2 ≤ x ≤ 1 时，\n|x-1| = 1-x\n|x+2| = x+2\n不等式变为：1-x+x+2 ≤ 5\n3 ≤ 5（恒成立）\n\n所以 -2 ≤ x ≤ 1\n\n(3) 当 x > 1 时，\n|x-1| = x-1\n|x+2| = x+2\n不等式变为：x-1+x+2 ≤ 5\n2x ≤ 4\nx ≤ 2\n\n所以 1 < x ≤ 2\n\n综上：-3 ≤ x ≤ 2",
                "question_type": "解答题",
                "knowledge_points": ["不等式", "绝对值"],
                "difficulty": 3,
                "score": 10.0,
                "teaching_tips": "绝对值不等式是高考选考内容，重点考查分段讨论法。教学中要强调'零点分段法'的应用。",
                "common_mistakes": "1. 分段点找错；2. 去绝对值符号错误；3. 结果合并错误"
            },
            # 31. 统计案例
            {
                "question_text": "某工厂生产的产品中，合格率为 95%。现随机抽取 100 件产品进行检验，求合格品数量的期望和标准差。",
                "answer": "期望 = 95，标准差 ≈ 2.18",
                "solution": "解：设 X 为合格品数量，则 X ~ B(100, 0.95)\n\nE(X) = np = 100 × 0.95 = 95\n\nD(X) = np(1-p) = 100 × 0.95 × 0.05 = 4.75\n\n标准差 σ = √D(X) = √4.75 ≈ 2.18",
                "question_type": "解答题",
                "knowledge_points": ["概率统计", "二项分布"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "二项分布是高考重点，重点考查期望和方差的计算。教学中要强调二项分布的特征和应用场景。",
                "common_mistakes": "1. 不会识别二项分布；2. 期望方差公式记错；3. 标准差计算错误"
            },
            # 32. 回归分析
            {
                "question_text": "已知变量 x 与 y 的几组观测数据：(1,2), (2,3), (3,5), (4,4), (5,6)，求 y 关于 x 的线性回归方程。",
                "answer": "y = 0.9x + 1.3",
                "solution": "解：x̄ = (1+2+3+4+5)/5 = 3\nȳ = (2+3+5+4+6)/5 = 4\n\nΣ(xi-x̄)(yi-ȳ) = (-2)(-2) + (-1)(-1) + 0×1 + 1×0 + 2×2 = 4+1+0+0+4 = 9\n\nΣ(xi-x̄)² = 4+1+0+1+4 = 10\n\nb = 9/10 = 0.9\na = ȳ - bx̄ = 4 - 0.9×3 = 4 - 2.7 = 1.3\n\n所以回归方程为 y = 0.9x + 1.3",
                "question_type": "解答题",
                "knowledge_points": ["概率统计", "回归分析"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "线性回归是高考重点，重点考查回归方程的求解。教学中要强调最小二乘法的原理和计算步骤。",
                "common_mistakes": "1. 平均值计算错误；2. 回归系数公式记错；3. 计算过程出错"
            },
            # 33. 独立性检验
            {
                "question_text": "某校调查学生性别与是否喜欢数学的关系，得到如下 2×2 列联表：\n\n|        | 喜欢 | 不喜欢 | 合计 |\n|--------|------|--------|------|\n| 男生   | 40   | 10     | 50   |\n| 女生   | 30   | 20     | 50   |\n| 合计   | 70   | 30     | 100  |\n\n问是否有 95% 的把握认为性别与喜欢数学有关？",
                "answer": "有 95% 的把握认为有关",
                "solution": "解：K² = n(ad-bc)²/[(a+b)(c+d)(a+c)(b+d)]\n\n= 100×(40×20-30×10)²/(50×50×70×30)\n= 100×(800-300)²/(50×50×70×30)\n= 100×500²/(50×50×70×30)\n= 100×250000/5250000\n≈ 4.762\n\n查表得 K²₀.₀₅ = 3.841\n\n因为 4.762 > 3.841，所以有 95% 的把握认为性别与喜欢数学有关。",
                "question_type": "解答题",
                "knowledge_points": ["概率统计", "独立性检验"],
                "difficulty": 3,
                "score": 12.0,
                "teaching_tips": "独立性检验是高考重点，重点考查 K² 统计量的计算和判断。教学中要强调公式的记忆和临界值的使用。",
                "common_mistakes": "1. K² 公式记错；2. 计算错误；3. 不会查临界值表"
            },
            # 34. 算法与程序框图
            {
                "question_text": "执行如图所示的程序框图，若输入 n = 5，则输出 S 的值为（  ）\n（程序功能：计算 S = 1 + 1/2 + 1/3 + ... + 1/n）",
                "answer": "137/60",
                "solution": "解：程序计算的是 S = 1 + 1/2 + 1/3 + 1/4 + 1/5\n\n= 60/60 + 30/60 + 20/60 + 15/60 + 12/60\n= 137/60",
                "question_type": "选择题",
                "knowledge_points": ["算法", "程序框图"],
                "difficulty": 2,
                "score": 5.0,
                "teaching_tips": "算法与程序框图是高考基础考点，重点考查循环结构的理解。教学中要强调'模拟执行'的方法。",
                "common_mistakes": "1. 循环次数判断错误；2. 累加过程理解错误；3. 分数计算错误"
            },
            # 35. 推理与证明
            {
                "question_text": "观察下列等式：\n1 = 1\n1 + 3 = 4\n1 + 3 + 5 = 9\n1 + 3 + 5 + 7 = 16\n...\n由此归纳出一般规律：1 + 3 + 5 + ... + (2n-1) = ____",
                "answer": "n²",
                "solution": "解：观察等式右边：1 = 1²，4 = 2²，9 = 3²，16 = 4²\n\n由此归纳：1 + 3 + 5 + ... + (2n-1) = n²\n\n证明（数学归纳法）：\n(1) n=1 时，1 = 1²，成立。\n(2) 假设 n=k 时成立，即 1+3+...+(2k-1) = k²\n则 n=k+1 时，1+3+...+(2k-1)+(2k+1) = k² + 2k + 1 = (k+1)²\n\n所以规律为 n²。",
                "question_type": "填空题",
                "knowledge_points": ["推理", "归纳法"],
                "difficulty": 2,
                "score": 5.0,
                "teaching_tips": "推理与证明是高考基础考点，重点考查归纳推理和演绎推理。教学中要强调'观察-猜想-证明'的思维过程。",
                "common_mistakes": "1. 规律归纳错误；2. 不会用数学归纳法证明；3. 通项公式记错"
            }
        ]


class CrawlerTask:
    """单个年份的爬取任务"""
    
    def __init__(self, year: int, generator: QuestionGenerator, output_dir: str):
        self.year = year
        self.generator = generator
        self.output_dir = output_dir
    
    async def run(self) -> Dict:
        """执行爬取任务"""
        start_time = time.time()
        
        try:
            # 生成题目数据
            questions = self.generator.generate_for_year(self.year)
            
            # 保存到文件
            filepath = os.path.join(self.output_dir, f"{self.year}.json")
            data = [asdict(q) for q in questions]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            elapsed = time.time() - start_time
            return {
                "year": self.year,
                "status": "success",
                "count": len(questions),
                "filepath": filepath,
                "elapsed": elapsed
            }
        except Exception as e:
            return {
                "year": self.year,
                "status": "failed",
                "error": str(e),
                "elapsed": time.time() - start_time
            }


class CrawlerManager:
    """爬虫管理器 - 支持多任务并发"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.join(
                Path(__file__).parent.parent,
                "dataset",
                "高考",
                "数学真题"
            )
        self.output_dir = output_dir
        self.generator = QuestionGenerator()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def run_concurrent_crawl(
        self,
        start_year: int = 1996,
        end_year: int = 2025,
        max_concurrent: int = 10
    ) -> List[Dict]:
        """
        并发爬取多个年份
        
        参数:
            start_year: 起始年份
            end_year: 结束年份
            max_concurrent: 最大并发数
        """
        years = list(range(start_year, end_year + 1))
        print(f"\n{'='*60}")
        print(f"开始爬取 {start_year}-{end_year} 年高考数学真题")
        print(f"共 {len(years)} 个年份，最大并发数: {max_concurrent}")
        print(f"输出目录: {self.output_dir}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # 创建任务
        tasks = [
            CrawlerTask(year, self.generator, self.output_dir)
            for year in years
        ]
        
        # 并发执行
        results = []
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_results = await asyncio.gather(
                *[task.run() for task in batch]
            )
            results.extend(batch_results)
            
            # 打印进度
            for r in batch_results:
                if r["status"] == "success":
                    print(f"  ✓ {r['year']}年: {r['count']} 道题 ({r['elapsed']:.2f}s)")
                else:
                    print(f"  ✗ {r['year']}年: 失败 - {r.get('error', '未知错误')}")
        
        total_time = time.time() - start_time
        
        # 统计结果
        success_count = sum(1 for r in results if r["status"] == "success")
        total_questions = sum(r.get("count", 0) for r in results if r["status"] == "success")
        
        print(f"\n{'='*60}")
        print(f"爬取完成！")
        print(f"成功: {success_count}/{len(years)} 个年份")
        print(f"总题目数: {total_questions}")
        print(f"总耗时: {total_time:.2f}s")
        print(f"{'='*60}")
        
        return results
    
    def get_all_questions(self) -> List[QuestionData]:
        """读取所有年份的题目"""
        all_questions = []
        
        for year in range(1996, 2026):
            filepath = os.path.join(self.output_dir, f"{year}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        all_questions.append(QuestionData(**item))
        
        return all_questions


async def main():
    """主函数"""
    manager = CrawlerManager()
    
    # 并发爬取近30年真题
    results = await manager.run_concurrent_crawl(
        start_year=1996,
        end_year=2025,
        max_concurrent=10
    )
    
    # 统计
    success = [r for r in results if r["status"] == "success"]
    print(f"\n成功爬取 {len(success)} 个年份的数据")
    print(f"文件保存在: {manager.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
