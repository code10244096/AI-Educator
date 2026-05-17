"""
GAOKAO-Bench数据转换脚本
将复旦大学的GAOKAO-Bench数据集转换为题库系统所需格式
按年份保存到 dataset/高考/数学真题/ 目录
"""
import json
import os
from pathlib import Path
from typing import List, Dict


def load_gaokao_bench_data(base_dir: str) -> List[Dict]:
    """
    加载GAOKAO-Bench数学数据
    
    参数:
        base_dir: GAOKAO-Bench数据集根目录
    
    返回:
        所有数学题目列表
    """
    all_questions = []
    
    # 数学客观题文件
    math_mcq_files = [
        "2010-2022_Math_I_MCQs.json",
        "2010-2022_Math_II_MCQs.json"
    ]
    
    # 数学习答题文件
    math_open_files = [
        "2010-2022_Math_I_Open-ended_Questions.json",
        "2010-2022_Math_II_Open-ended_Questions.json",
        "2010-2022_Math_I_Fill-in-the-Blank.json",
        "2010-2022_Math_II_Fill-in-the-Blank.json"
    ]
    
    # 加载客观题
    for filename in math_mcq_files:
        filepath = os.path.join(base_dir, "Data", "Objective_Questions", filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_questions.extend(data.get("example", []))
            print(f"✓ 加载客观题: {filename} - {len(data.get('example', []))} 道题")
    
    # 加载主观题和填空题
    for filename in math_open_files:
        filepath = os.path.join(base_dir, "Data", "Subjective_Questions", filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_questions.extend(data.get("example", []))
            print(f"✓ 加载主观题/填空题: {filename} - {len(data.get('example', []))} 道题")
    
    print(f"\n总共加载 {len(all_questions)} 道数学题目")
    return all_questions


def determine_question_type(question_text: str, filename: str) -> str:
    """根据题目内容和文件名判断题型"""
    if "Fill-in-the-Blank" in filename:
        return "填空题"
    elif "MCQ" in filename:
        return "选择题"
    else:
        return "解答题"


def extract_knowledge_points(question_text: str, analysis: str) -> List[str]:
    """从题目中提取知识点（简化版）"""
    knowledge_points = []
    
    # 根据题目内容判断知识点
    text = question_text + " " + analysis
    
    if "集合" in text or "A ∩ B" in text or "A ∪ B" in text:
        knowledge_points.append("集合")
    if "复数" in text or "z=" in text or "共轭" in text:
        knowledge_points.append("复数")
    if "导数" in text or "f'(x)" in text or "单调" in text:
        knowledge_points.append("导数")
    if "数列" in text or "等差" in text or "等比" in text:
        knowledge_points.append("数列")
    if "椭圆" in text or "双曲线" in text or "抛物线" in text:
        knowledge_points.append("解析几何")
    if "概率" in text or "期望" in text or "抽样" in text:
        knowledge_points.append("概率统计")
    if "向量" in text or "数量积" in text:
        knowledge_points.append("向量")
    if "三角" in text or "sin" in text or "cos" in text or "tan" in text:
        knowledge_points.append("三角函数")
    if "立体" in text or "棱柱" in text or "球" in text or "体积" in text:
        knowledge_points.append("立体几何")
    if "不等式" in text or "均值" in text:
        knowledge_points.append("不等式")
    if "函数" in text and ("奇偶" in text or "奇函数" in text or "偶函数" in text):
        knowledge_points.append("函数性质")
    if "切线" in text:
        knowledge_points.append("导数应用")
    if "逻辑" in text or "命题" in text:
        knowledge_points.append("逻辑")
    if "二项式" in text:
        knowledge_points.append("二项式定理")
    
    if not knowledge_points:
        knowledge_points.append("数学")
    
    return knowledge_points


def convert_to_question_bank_format(
    raw_question: Dict,
    filename: str
) -> Dict:
    """
    将GAOKAO-Bench格式转换为题库系统格式
    
    参数:
        raw_question: 原始题目数据
        filename: 来源文件名
    
    返回:
        题库系统格式的题目
    """
    year = int(raw_question.get("year", 2010))
    category = raw_question.get("category", "全国卷")
    question_text = raw_question.get("question", "")
    answer = raw_question.get("answer", "")
    analysis = raw_question.get("analysis", "")
    score = raw_question.get("score", 5)
    
    # 判断题型
    question_type = determine_question_type(question_text, filename)
    
    # 提取知识点
    knowledge_points = extract_knowledge_points(question_text, analysis)
    
    # 构建题目
    question = {
        "question_text": question_text,
        "answer": answer if isinstance(answer, str) else ", ".join(answer),
        "solution": analysis,
        "question_type": question_type,
        "subject": "数学",
        "education_level": "高中",
        "exam_type": "高考",
        "year": year,
        "region": category,
        "knowledge_points": knowledge_points,
        "difficulty": 3,  # 默认中等难度，后续可根据实际情况调整
        "score": float(score),
        "source_url": "https://github.com/OpenLMLab/GAOKAO-Bench",
        "teaching_tips": generate_teaching_tips(knowledge_points),
        "common_mistakes": generate_common_mistakes(knowledge_points)
    }
    
    return question


def generate_teaching_tips(knowledge_points: List[str]) -> str:
    """根据知识点生成教学建议"""
    tips_map = {
        "集合": "集合是高考基础考点，重点考查集合间的关系和运算。教学中要强调集合元素的确定性、互异性、无序性。",
        "复数": "复数是高考基础考点，重点考查复数的运算和模的计算。教学中要强调复数的四则运算和几何意义。",
        "导数": "导数是高考核心考点，重点考查利用导数研究函数的单调性、极值、最值。教学中要强调求导法则和导数的几何意义。",
        "数列": "数列是高考必考内容，重点考查等差数列、等比数列的通项公式和前n项和。教学中要强调公式的推导和应用。",
        "解析几何": "解析几何是高考难点，重点考查椭圆、双曲线、抛物线的定义、标准方程和性质。教学中要强调数形结合思想。",
        "概率统计": "统计是高考基础考点，重点考查抽样方法、频率分布、统计图表。教学中要强调各种抽样方法的特点和适用场景。",
        "向量": "向量是高考基础考点，重点考查向量的坐标运算和数量积。教学中要强调向量垂直的充要条件。",
        "三角函数": "三角函数是高考重点，重点考查同角三角函数关系和诱导公式。教学中要强调象限判断和符号确定。",
        "立体几何": "立体几何是高考重点，重点考查空间几何体的表面积和体积计算。教学中要强调空间想象能力和公式应用。",
        "不等式": "不等式是高考重点，重点考查均值不等式的应用。教学中要强调'一正二定三相等'的使用条件。",
        "函数性质": "函数性质是高考重点，重点考查函数的奇偶性、单调性、周期性。教学中要强调函数图像与性质的关系。",
        "导数应用": "导数应用是高考重点，重点考查切线方程、函数极值和最值。教学中要强调导数的几何意义。",
        "逻辑": "逻辑是高考基础考点，重点考查充分条件、必要条件的判断。教学中要强调'小推大'的判断方法。",
        "二项式定理": "二项式定理是高考基础考点，重点考查通项公式的应用。教学中要强调通项公式的记忆和指数的计算。"
    }
    
    tips = []
    for kp in knowledge_points:
        if kp in tips_map:
            tips.append(tips_map[kp])
    
    return " ".join(tips) if tips else "本题是高考重点考点，教学中要强调基础知识和解题方法的掌握。"


def generate_common_mistakes(knowledge_points: List[str]) -> str:
    """根据知识点生成常见错误"""
    mistakes_map = {
        "集合": "1. 忽略集合为空集的情况；2. 不理解集合关系的等价条件",
        "复数": "1. 复数除法运算错误；2. 模的公式记错",
        "导数": "1. 求导错误；2. 不会用导数符号判断单调性；3. 极值和最值混淆",
        "数列": "1. 公式记错；2. 不会列方程求公差/公比；3. 求和公式使用错误",
        "解析几何": "1. 离心率公式记错；2. 不会利用点在曲线上列方程；3. 计算错误",
        "概率统计": "1. 不理解分层抽样的原理；2. 计算比例错误",
        "向量": "1. 数量积公式记错；2. 计算错误",
        "三角函数": "1. 忽略象限导致符号错误；2. 同角关系记错",
        "立体几何": "1. 不会找底面和高；2. 体积公式记错",
        "不等式": "1. 忽略均值不等式的使用条件；2. 不会配凑系数；3. 等号成立条件判断错误",
        "函数性质": "1. 奇偶性判断错误；2. 忽略定义域",
        "导数应用": "1. 求导错误；2. 切线方程公式记错",
        "逻辑": "1. 充分必要条件混淆；2. 不会用集合关系判断；3. 反例构造错误",
        "二项式定理": "1. 通项公式记错；2. 指数计算错误；3. 组合数计算错误"
    }
    
    mistakes = []
    for kp in knowledge_points:
        if kp in mistakes_map:
            mistakes.append(mistakes_map[kp])
    
    return "；".join(mistakes) if mistakes else "1. 审题不清；2. 计算错误；3. 公式记错"


def save_by_year(
    questions: List[Dict],
    output_dir: str
) -> Dict[int, int]:
    """
    按年份保存题目到JSON文件
    
    参数:
        questions: 所有题目列表
        output_dir: 输出目录
    
    返回:
        各年份题目数量统计
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 按年份分组
    year_groups = {}
    for q in questions:
        year = q["year"]
        if year not in year_groups:
            year_groups[year] = []
        year_groups[year].append(q)
    
    # 按年份保存
    stats = {}
    for year in sorted(year_groups.keys()):
        year_questions = year_groups[year]
        
        # 排序：按题型和顺序
        year_questions.sort(key=lambda x: (
            0 if x["question_type"] == "选择题" else 
            1 if x["question_type"] == "填空题" else 2
        ))
        
        # 保存文件
        output_file = os.path.join(output_dir, f"{year}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "year": year,
                "total_questions": len(year_questions),
                "questions": year_questions
            }, f, ensure_ascii=False, indent=2)
        
        stats[year] = len(year_questions)
        print(f"  ✓ {year}年: {len(year_questions)} 道题 -> {output_file}")
    
    return stats


def main():
    """主函数"""
    # 路径配置
    gaokao_bench_dir = os.path.join(
        Path(__file__).parent.parent,
        "temp_gaokao_bench"
    )
    
    output_dir = os.path.join(
        Path(__file__).parent.parent,
        "dataset",
        "高考",
        "数学真题"
    )
    
    print("="*60)
    print("GAOKAO-Bench 数据转换工具")
    print("="*60)
    print(f"\n数据源: {gaokao_bench_dir}")
    print(f"输出目录: {output_dir}\n")
    
    # 1. 加载数据
    print("【步骤1】加载GAOKAO-Bench数据...")
    raw_questions = load_gaokao_bench_data(gaokao_bench_dir)
    
    if not raw_questions:
        print("错误：未找到任何数据，请检查GAOKAO-Bench数据集路径")
        return
    
    # 2. 转换数据格式
    print("\n【步骤2】转换数据格式...")
    converted_questions = []
    
    # 需要知道每个题目来自哪个文件
    # 这里我们重新加载并标记来源
    math_files = [
        ("2010-2022_Math_I_MCQs.json", "Objective_Questions"),
        ("2010-2022_Math_II_MCQs.json", "Objective_Questions"),
        ("2010-2022_Math_I_Open-ended_Questions.json", "Subjective_Questions"),
        ("2010-2022_Math_II_Open-ended_Questions.json", "Subjective_Questions"),
        ("2010-2022_Math_I_Fill-in-the-Blank.json", "Subjective_Questions"),
        ("2010-2022_Math_II_Fill-in-the-Blank.json", "Subjective_Questions"),
    ]
    
    for filename, folder in math_files:
        filepath = os.path.join(gaokao_bench_dir, "Data", folder, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for raw_q in data.get("example", []):
                    converted_q = convert_to_question_bank_format(raw_q, filename)
                    converted_questions.append(converted_q)
    
    print(f"✓ 转换完成: {len(converted_questions)} 道题")
    
    # 3. 按年份保存
    print("\n【步骤3】按年份保存数据...")
    stats = save_by_year(converted_questions, output_dir)
    
    # 4. 统计信息
    print("\n" + "="*60)
    print("转换完成！")
    print("="*60)
    print(f"总题目数: {len(converted_questions)}")
    print(f"年份范围: {min(stats.keys())} - {max(stats.keys())}")
    print(f"年份数量: {len(stats)}")
    print(f"\n各年份题目数:")
    for year in sorted(stats.keys()):
        print(f"  {year}年: {stats[year]} 道题")
    
    total = sum(stats.values())
    print(f"\n总计: {total} 道题")
    print("="*60)


if __name__ == "__main__":
    main()
