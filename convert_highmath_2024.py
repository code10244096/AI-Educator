import json
import os
import re
from pathlib import Path
from collections import defaultdict

def clean_latex(text):
    """将LaTeX公式转换为更易读的文本格式"""
    if not text:
        return ''
    
    # 移除LaTeX标记
    text = text.replace('\\(', '').replace('\\)', '')
    text = text.replace('\\[', '').replace('\\]', '')
    text = text.replace('$', '')
    
    # 转换常见符号
    replacements = {
        '\\geq': '≥',
        '\\leq': '≤',
        '\\neq': '≠',
        '\\approx': '≈',
        '\\times': '×',
        '\\div': '÷',
        '\\cdot': '·',
        '\\pm': '±',
        '\\infty': '∞',
        '\\pi': 'π',
        '\\Delta': 'Δ',
        '\\triangle': '△',
        '\\circ': '°',
        '\\alpha': 'α',
        '\\beta': 'β',
        '\\gamma': 'γ',
        '\\theta': 'θ',
        '\\lambda': 'λ',
        '\\mu': 'μ',
        '\\sigma': 'σ',
        '\\phi': 'φ',
        '\\psi': 'ψ',
        '\\omega': 'ω',
        '\\rightarrow': '→',
        '\\leftarrow': '←',
        '\\Rightarrow': '⇒',
        '\\Leftarrow': '⇐',
        '\\in': '∈',
        '\\notin': '∉',
        '\\subset': '⊂',
        '\\supset': '⊃',
        '\\cup': '∪',
        '\\cap': '∩',
        '\\emptyset': '∅',
        '\\forall': '∀',
        '\\exists': '∃',
        '\\nabla': '∇',
        '\\quad': '  ',
        '\\qquad': '    ',
        '\\mathrm': '',
        '\\mathbf': '',
        '\\vec': '',
        '\\sin': 'sin',
        '\\cos': 'cos',
        '\\tan': 'tan',
        '\\log': 'log',
        '\\ln': 'ln',
        '\\lim': 'lim',
        '\\max': 'max',
        '\\min': 'min',
    }
    
    for latex, plain in replacements.items():
        text = text.replace(latex, plain)
    
    # 处理上下标
    text = re.sub(r'\^\{([^}]+)\}', r'^(\1)', text)
    text = re.sub(r'_\{([^}]+)\}', r'_(\1)', text)
    
    # 处理分数
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
    
    # 处理平方根
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', text)
    text = re.sub(r'\\sqrt(\d+)', r'√\1', text)
    
    # 处理集合
    text = text.replace('\\{', '{').replace('\\}', '}')
    
    # 处理数学环境
    text = re.sub(r'\\begin\{[^}]+\}', '', text)
    text = re.sub(r'\\end\{[^}]+\}', '', text)
    text = text.replace('\\\\', '\n')
    
    # 清理多余空格
    text = re.sub(r'  +', ' ', text)
    
    return text.strip()

def map_type_to_knowledge_points(type_name):
    """将HighMATH的分类映射到知识点"""
    type_mapping = {
        'Logic_Set_Inequality_Complex': ['逻辑', '集合', '不等式', '复数'],
        'Function_Derivative': ['函数', '导数'],
        'Trigonometric_Functions_and_Triangle_Solving': ['三角函数', '解三角形'],
        'Sequence': ['数列'],
        'Plane_Analytic_Geometry': ['平面解析几何'],
        'Solid_Geometry': ['立体几何'],
        'Statistics_Probability': ['统计', '概率'],
        'Counting_Principle': ['计数原理', '排列组合'],
    }
    return type_mapping.get(type_name, [])

def convert_highmath_to_target_format(source_dir, target_dir):
    """转换HighMATH数据集为目标格式"""
    
    # 所有分类文件
    category_files = [
        'Logic_Set_Inequality_Complex.jsonl',
        'Function_Derivative.jsonl',
        'Trigonometric_Functions_and_Triangle_Solving.jsonl',
        'Sequence.jsonl',
        'Plane_Analytic_Geometry.jsonl',
        'Solid_Geometry.jsonl',
        'Statistics_Probability.jsonl',
        'Counting_Principle.jsonl',
    ]
    
    total_questions = 0
    all_converted_questions = []
    
    for category_file in category_files:
        filepath = os.path.join(source_dir, category_file)
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            continue
        
        category_name = category_file.replace('.jsonl', '')
        knowledge_points = map_type_to_knowledge_points(category_name)
        
        print(f"\n处理分类: {category_name}")
        
        # 读取JSONL数据
        questions = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    questions.append(item)
                except json.JSONDecodeError:
                    continue
        
        print(f"  解析到 {len(questions)} 道题目")
        
        # 转换所有题目
        converted_questions = []
        for item in questions:
            problem = clean_latex(item.get('problem', ''))
            answer = clean_latex(item.get('answer', ''))
            steps = clean_latex(item.get('steps', ''))
            level = item.get('level', '3')
            
            # 难度映射: 1-5 -> 1-5
            difficulty = int(level) if level.isdigit() else 3
            
            question_obj = {
                "question_text": problem,
                "answer": answer,
                "solution": f"【解析】\n{steps}" if steps else "",
                "question_type": "解答题" if difficulty >= 4 else "选择题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "全国卷",
                "knowledge_points": knowledge_points.copy(),
                "difficulty": difficulty,
                "score": 5.0 if difficulty <= 3 else 10.0,
                "source_url": "https://github.com/tjunlp-lab/HighMATH",
                "teaching_tips": "",
                "common_mistakes": ""
            }
            
            converted_questions.append(question_obj)
        
        all_converted_questions.extend(converted_questions)
        total_questions += len(converted_questions)
        print(f"  已转换: {len(converted_questions)}题")
    
    # 合并所有分类到一个文件
    region_dir = os.path.join(target_dir, '全国卷')
    os.makedirs(region_dir, exist_ok=True)
    
    target_file = os.path.join(region_dir, '2024_HighMATH.json')
    
    output_data = {
        'year': 2024,
        'region': '全国卷',
        'total_questions': len(all_converted_questions),
        'questions': all_converted_questions
    }
    
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存: {target_file} ({len(all_converted_questions)}题)")
    
    return total_questions

if __name__ == '__main__':
    source_dir = r'e:\AI-Educator\temp_gaokao_data\HighMATH_2024'
    target_dir = r'e:\AI-Educator\dataset\高考\数学\高考数学真题'
    
    print("=" * 60)
    print("HighMATH 2024年数据集转换")
    print("=" * 60)
    
    total = convert_highmath_to_target_format(source_dir, target_dir)
    print(f"\n转换完成! 共 {total} 道题目")
