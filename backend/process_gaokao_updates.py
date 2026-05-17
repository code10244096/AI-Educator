"""
处理2023-2024年GAOKAO-Bench-Updates数据
将数据转换为题库系统格式并按卷别保存
"""

import json
import os
import re
from typing import Dict, List


def get_base_dir() -> str:
    """获取基础目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_updates_dir() -> str:
    """获取GAOKAO-Bench-Updates数据目录"""
    return os.path.join(
        get_base_dir(),
        "dataset",
        "高考",
        "数学",
        "全国卷数学真题",
        "GAOKAO-Bench-Updates-main",
        "Data"
    )


def get_target_dir() -> str:
    """获取目标数据目录"""
    return os.path.join(
        get_base_dir(),
        "dataset",
        "高考",
        "数学"
    )


def determine_question_type(question_text: str) -> str:
    """判断题型"""
    # 选择题特征
    if re.search(r'[A-D][\.、]', question_text) or re.search(r'选项|选择', question_text):
        return "选择题"
    
    # 填空题特征
    if '____' in question_text or '______' in question_text:
        return "填空题"
    
    # 解答题特征
    if re.search(r'解答|证明|计算|求.*值|求.*范围', question_text):
        return "解答题"
    
    return "选择题"


def extract_knowledge_points(question_text: str, analysis: str = "") -> List[str]:
    """提取知识点"""
    knowledge_points = []
    content = question_text + " " + analysis
    
    # 常见数学知识点关键词
    keywords = {
        "集合": r'集合|∪|∩|⊆|∈',
        "复数": r'复数|虚数|\\mathrm{i}|z=',
        "向量": r'向量|→|⋅|\\vec',
        "数列": r'数列|等差|等比|a_n|S_n',
        "不等式": r'不等式|≥|≤|约束条件',
        "立体几何": r'棱柱|棱锥|球|体积|表面积|双曲线',
        "解析几何": r'椭圆|双曲线|抛物线|直线与圆|焦点',
        "概率统计": r'概率|统计|分布|期望|频数',
        "导数": r'导数|切线|极值|最值|f\'|f\(',
        "三角函数": r'sin|cos|tan|三角',
        "排列组合": r'排列|组合|C|P',
        "二项式定理": r'二项式|展开',
        "函数": r'函数|f\(x\)|单调|奇偶|周期',
    }
    
    for point, pattern in keywords.items():
        if re.search(pattern, content, re.IGNORECASE):
            knowledge_points.append(point)
    
    return knowledge_points if knowledge_points else ["综合"]


def generate_teaching_tips(knowledge_points: List[str]) -> str:
    """生成教学建议"""
    if not knowledge_points:
        return "本题为高考真题，建议结合教材系统复习相关知识点。"
    
    points_str = "、".join(knowledge_points)
    return f"本题主要考查{points_str}知识点，建议结合教材和历年真题进行系统训练。"


def generate_common_mistakes(knowledge_points: List[str]) -> str:
    """生成常见错误"""
    mistakes = {
        "集合": "1. 忽略集合为空集的情况；2. 不理解集合关系的等价条件",
        "复数": "1. 复数除法运算错误；2. 模的公式记错",
        "向量": "1. 向量数量积公式记错；2. 向量夹角计算错误",
        "数列": "1. 等差等比公式混淆；2. 求和公式使用错误",
        "不等式": "1. 不等号方向改变忘记变号；2. 忽略定义域限制",
        "立体几何": "1. 空间想象能力不足；2. 体积表面积公式记错",
        "解析几何": "1. 圆锥曲线方程记错；2. 计算过程复杂容易出错",
        "概率统计": "1. 概率公式使用错误；2. 统计概念混淆",
        "导数": "1. 求导公式记错；2. 切线方程求解错误",
        "三角函数": "1. 三角函数公式记错；2. 角度弧度转换错误",
        "排列组合": "1. 排列组合概念混淆；2. 重复计数或漏计",
        "二项式定理": "1. 二项式系数计算错误；2. 通项公式记错",
        "函数": "1. 函数性质判断错误；2. 定义域值域求解错误",
    }
    
    result = []
    for point in knowledge_points:
        if point in mistakes:
            result.append(mistakes[point])
    
    return "；".join(result) if result else "请参考教材和历年真题"


def convert_question(raw_question: Dict) -> Dict:
    """将GAOKAO-Bench格式转换为题库系统格式"""
    year = int(raw_question.get("year", 2024))
    category = raw_question.get("category", "")
    question_text = raw_question.get("question", "")
    answer = raw_question.get("answer", [])
    analysis = raw_question.get("analysis", "")
    score = raw_question.get("score", 5)
    
    # 标准化卷别名称
    region = category.replace("理科", "").replace("文科", "").strip()
    if "全国甲卷" in region:
        region = "全国甲卷"
    elif "全国乙卷" in region:
        region = "全国乙卷"
    elif "新高考" in region or "新课标" in region:
        if "Ⅰ" in region or "1" in region:
            region = "新课标Ⅰ"
        elif "Ⅱ" in region or "2" in region:
            region = "新课标Ⅱ"
    
    # 判断题型
    question_type = determine_question_type(question_text)
    
    # 提取知识点
    knowledge_points = extract_knowledge_points(question_text, analysis)
    
    # 构建题目
    question = {
        "question_text": question_text,
        "answer": ", ".join(answer) if isinstance(answer, list) else answer,
        "solution": analysis,
        "question_type": question_type,
        "subject": "数学",
        "education_level": "高中",
        "exam_type": "高考",
        "year": year,
        "region": region,
        "knowledge_points": knowledge_points,
        "difficulty": 3,
        "score": float(score),
        "source_url": "https://github.com/OpenLMLab/GAOKAO-Bench-Updates",
        "teaching_tips": generate_teaching_tips(knowledge_points),
        "common_mistakes": generate_common_mistakes(knowledge_points)
    }
    
    return question


def process_updates():
    """处理GAOKAO-Bench-Updates数据"""
    updates_dir = get_updates_dir()
    target_dir = get_target_dir()
    
    print("="*60)
    print("处理2023-2024年GAOKAO-Bench-Updates数据")
    print("="*60)
    
    # 处理2024年数据
    math_2024_file = os.path.join(updates_dir, "GAOKAO-Bench-2024", "2024_Math_MCQs.json")
    
    if not os.path.exists(math_2024_file):
        print(f"✗ 找不到2024年数学数据文件: {math_2024_file}")
        return
    
    with open(math_2024_file, 'r', encoding='utf-8') as f:
        data_2024 = json.load(f)
    
    questions_2024 = data_2024.get("example", [])
    print(f"\n找到 {len(questions_2024)} 道2024年题目")
    
    # 按卷别分组
    region_questions = {}
    
    for q in questions_2024:
        category = q.get("category", "")
        region = category.replace("理科", "").replace("文科", "").strip()
        
        if "全国甲卷" in region:
            region = "全国甲卷"
        elif "全国乙卷" in region:
            region = "全国乙卷"
        elif "新高考" in region or "新课标" in region:
            if "Ⅰ" in region or "1" in region:
                region = "新课标Ⅰ"
            elif "Ⅱ" in region or "2" in region:
                region = "新课标Ⅱ"
        
        if region not in region_questions:
            region_questions[region] = []
        
        region_questions[region].append(convert_question(q))
    
    # 保存2024年数据
    for region, questions in region_questions.items():
        region_dir = os.path.join(target_dir, region)
        os.makedirs(region_dir, exist_ok=True)
        
        output_file = os.path.join(region_dir, "2024.json")
        
        # 如果文件已存在，合并数据
        existing_questions = []
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_questions = existing_data.get("questions", [])
        
        # 合并并去重
        all_questions = existing_questions + questions
        # 简单去重：基于题目文本
        seen = set()
        unique_questions = []
        for q in all_questions:
            if q["question_text"] not in seen:
                seen.add(q["question_text"])
                unique_questions.append(q)
        
        output_data = {
            "year": 2024,
            "region": region,
            "total_questions": len(unique_questions),
            "questions": unique_questions
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ {region} 2024年: {len(unique_questions)} 道题")
    
    print("\n" + "="*60)
    print("处理完成!")
    print("="*60)


if __name__ == "__main__":
    process_updates()
