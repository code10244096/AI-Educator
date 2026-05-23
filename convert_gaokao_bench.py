import json
import os
import re
from pathlib import Path

def clean_latex(text):
    """将LaTeX公式转换为更易读的文本格式"""
    if not text:
        return ''
    
    # 移除LaTeX标记
    text = text.replace('$', '')
    text = text.replace('\\(', '').replace('\\)', '')
    text = text.replace('\\[', '').replace('\\]', '')
    
    # 转换常见符号
    replacements = {
        '\\leqslant': '≤',
        '\\geqslant': '≥',
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
        '\\sqrt': '√',
        '\\sum': 'Σ',
        '\\int': '∫',
        '\\quad': '  ',
        '\\qquad': '    ',
    }
    
    for latex, plain in replacements.items():
        text = text.replace(latex, plain)
    
    # 处理上下标
    text = re.sub(r'\^\{([^}]+)\}', r'^(\1)', text)
    text = re.sub(r'_\{([^}]+)\}', r'_(\1)', text)
    text = re.sub(r'\^([a-zA-Z0-9])', r'^\1', text)
    text = re.sub(r'_([a-zA-Z0-9])', r'_\1', text)
    
    # 处理分数
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
    
    # 处理集合
    text = text.replace('\\{', '{').replace('\\}', '}')
    
    # 处理向量
    text = text.replace('\\vec{', '向量').replace('}', '')
    
    # 处理数学环境
    text = re.sub(r'\\begin\{[^}]+\}', '', text)
    text = re.sub(r'\\end\{[^}]+\}', '', text)
    text = text.replace('\\\\', '\n')
    
    # 清理多余空格
    text = re.sub(r'  +', ' ', text)
    
    return text.strip()

def map_category_to_region(category):
    """将试卷类别映射到地区/试卷类型"""
    category = category.strip()
    
    mapping = {
        '（新课标）': '新课标',
        '（新课标Ⅰ）': '新课标I卷',
        '（新课标Ⅱ）': '新课标II卷',
        '（新课标Ⅲ）': '新课标III卷',
        '（全国Ⅰ卷）': '全国I卷',
        '（全国Ⅱ卷）': '全国II卷',
        '（全国Ⅲ卷）': '全国III卷',
        '（全国甲卷）': '全国甲卷',
        '（全国乙卷）': '全国乙卷',
        '（北京卷）': '北京',
        '（天津卷）': '天津',
        '（上海卷）': '上海',
        '（江苏卷）': '江苏',
        '（浙江卷）': '浙江',
        '（山东卷）': '山东',
        '（广东卷）': '广东',
        '（湖南卷）': '湖南',
        '（湖北卷）': '湖北',
        '（四川卷）': '四川',
        '（重庆卷）': '重庆',
        '（福建卷）': '福建',
        '（安徽卷）': '安徽',
        '（江西卷）': '江西',
        '（河南卷）': '河南',
        '（河北卷）': '河北',
        '（山西卷）': '山西',
        '（陕西卷）': '陕西',
        '（辽宁卷）': '辽宁',
        '（吉林卷）': '吉林',
        '（黑龙江卷）': '黑龙江',
        '（云南卷）': '云南',
        '（贵州卷）': '贵州',
        '（广西卷）': '广西',
        '（西藏卷）': '西藏',
        '（甘肃卷）': '甘肃',
        '（青海卷）': '青海',
        '（宁夏卷）': '宁夏',
        '（新疆卷）': '新疆',
        '（内蒙古卷）': '内蒙古',
        '（海南卷）': '海南',
    }
    
    return mapping.get(category, category.strip('（）'))

def determine_question_type(question_text, file_keywords):
    """判断题目类型"""
    if 'MCQ' in file_keywords or '选择题' in question_text:
        return '选择题'
    elif 'Fill-in-the-Blank' in file_keywords or '填空题' in question_text:
        return '填空题'
    elif 'Open-ended' in file_keywords or '解答题' in question_text:
        return '解答题'
    else:
        # 根据题目内容判断
        if question_text.strip().endswith('(  )') or '（）' in question_text:
            return '选择题'
        elif '______' in question_text or '____' in question_text:
            return '填空题'
        else:
            return '解答题'

def convert_gaokao_bench_to_target_format(objective_dir, subjective_dir, target_dir):
    """转换GAOKAO-Bench数据为目标格式"""
    
    # 数学相关文件
    math_files = [
        '2010-2022_Math_I_MCQs.json',
        '2010-2022_Math_II_MCQs.json',
        '2010-2022_Math_I_Fill-in-the-Blank.json',
        '2010-2022_Math_II_Fill-in-the-Blank.json',
        '2010-2022_Math_I_Open-ended_Questions.json',
        '2010-2022_Math_II_Open-ended_Questions.json',
    ]
    
    # 按年份和地区组织数据
    data_by_year_region = {}
    
    # 处理客观题和主观题目录
    for source_dir, dir_label in [(objective_dir, "客观题"), (subjective_dir, "主观题")]:
        if not os.path.exists(source_dir):
            print(f"目录不存在: {source_dir}")
            continue
        
        print(f"\n处理{dir_label}目录: {source_dir}")
        
        for filename in math_files:
            filepath = os.path.join(source_dir, filename)
            if not os.path.exists(filepath):
                continue
            
            print(f"  处理文件: {filename}")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_keywords = data.get('keywords', '')
            examples = data.get('example', [])
            
            for item in examples:
                year = int(item.get('year', 0))
                category = item.get('category', '（新课标）')
                region = map_category_to_region(category)
                
                if year < 2000:
                    continue
                
                # 创建年份-地区键
                key = (year, region)
                if key not in data_by_year_region:
                    data_by_year_region[key] = []
                
                # 转换题目
                question_text = clean_latex(item.get('question', ''))
                answer = item.get('answer', '')
                analysis = item.get('analysis', '')
                
                # 处理答案格式
                if isinstance(answer, list):
                    answer_str = ', '.join(answer)
                else:
                    answer_str = clean_latex(str(answer))
                
                # 确定题目类型
                question_type = determine_question_type(question_text, file_keywords)
                
                question_obj = {
                    "question_text": question_text,
                    "answer": answer_str,
                    "solution": f"【解析】\n{clean_latex(analysis)}" if analysis else "",
                    "question_type": question_type,
                    "subject": "数学",
                    "education_level": "高中",
                    "exam_type": "高考",
                    "year": year,
                    "region": region,
                    "knowledge_points": [],
                    "difficulty": 3,
                    "score": float(item.get('score', 0)),
                    "source_url": "",
                    "teaching_tips": "",
                    "common_mistakes": ""
                }
                
                data_by_year_region[key].append(question_obj)
    
    # 写入目标文件
    print(f"\n开始写入目标文件...")
    total_files = 0
    total_questions = 0
    
    for (year, region), questions in data_by_year_region.items():
        # 按题目序号排序
        questions.sort(key=lambda q: q['question_text'])
        
        # 创建目标目录
        region_dir = os.path.join(target_dir, region)
        os.makedirs(region_dir, exist_ok=True)
        
        # 创建目标文件
        target_file = os.path.join(region_dir, f"{year}.json")
        
        output_data = {
            "year": year,
            "region": region,
            "total_questions": len(questions),
            "questions": questions
        }
        
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        total_files += 1
        total_questions += len(questions)
        print(f"  已创建: {region}/{year}.json ({len(questions)}题)")
    
    print(f"\n转换完成!")
    print(f"  共创建 {total_files} 个文件")
    print(f"  共转换 {total_questions} 道题目")

if __name__ == "__main__":
    # 源数据目录
    source_dir = r"e:\AI-Educator\temp_gaokao_bench\Data"
    
    # 目标数据目录
    target_dir = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"
    
    # 创建Objective和Subjective的完整路径
    objective_dir = os.path.join(source_dir, "Objective_Questions")
    subjective_dir = os.path.join(source_dir, "Subjective_Questions")
    
    print("=" * 60)
    print("高考数学真题数据转换工具")
    print("=" * 60)
    print(f"源数据目录: {source_dir}")
    print(f"目标目录: {target_dir}")
    print()
    
    # 合并两个目录的数据
    all_math_files = []
    for subdir in [objective_dir, subjective_dir]:
        if os.path.exists(subdir):
            for f in os.listdir(subdir):
                if 'Math' in f and f.endswith('.json'):
                    all_math_files.append(os.path.join(subdir, f))
    
    print(f"找到 {len(all_math_files)} 个数学相关JSON文件:")
    for f in all_math_files:
        print(f"  - {os.path.basename(f)}")
    print()
    
    # 执行转换
    convert_gaokao_bench_to_target_format(objective_dir, subjective_dir, target_dir)
