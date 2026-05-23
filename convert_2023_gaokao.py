import json
import os
import re
from pathlib import Path

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

def convert_2023_jsonl_to_json(jsonl_content, target_dir):
    """转换2023年JSONL数据为目标JSON格式"""
    
    # 解析JSONL数据
    questions = []
    for line in jsonl_content.strip().split('\n'):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            questions.append(item)
        except json.JSONDecodeError:
            continue
    
    print(f"解析到 {len(questions)} 道题目")
    
    # 按试卷类型分组（根据题目序号判断）
    # fresh_gaokao.1-13 可能是新高考I卷
    # fresh_gaokao.14-30 可能包含其他试卷
    
    papers = {
        '新高考I卷': [],
        '新高考II卷': [],
        '全国甲卷': [],
        '全国乙卷': [],
    }
    
    for item in questions:
        q_num = item.get('question_number', '')
        question_text = clean_latex(item.get('question', ''))
        answer = clean_latex(item.get('answer', ''))
        
        # 根据题目序号分配到不同试卷
        # 这里需要根据实际情况调整
        if 'fresh_gaokao' in q_num:
            num = int(q_num.split('.')[-1])
            if num <= 13:
                papers['新高考I卷'].append({
                    'question_text': question_text,
                    'answer': answer,
                    'solution': '',
                    'question_type': '未知',
                    'subject': '数学',
                    'education_level': '高中',
                    'exam_type': '高考',
                    'year': 2023,
                    'region': '新高考I卷',
                    'knowledge_points': [],
                    'difficulty': 3,
                    'score': 5.0,
                    'source_url': '',
                    'teaching_tips': '',
                    'common_mistakes': ''
                })
            elif num <= 20:
                papers['新高考II卷'].append({
                    'question_text': question_text,
                    'answer': answer,
                    'solution': '',
                    'question_type': '未知',
                    'subject': '数学',
                    'education_level': '高中',
                    'exam_type': '高考',
                    'year': 2023,
                    'region': '新高考II卷',
                    'knowledge_points': [],
                    'difficulty': 3,
                    'score': 5.0,
                    'source_url': '',
                    'teaching_tips': '',
                    'common_mistakes': ''
                })
            else:
                papers['全国甲卷'].append({
                    'question_text': question_text,
                    'answer': answer,
                    'solution': '',
                    'question_type': '未知',
                    'subject': '数学',
                    'education_level': '高中',
                    'exam_type': '高考',
                    'year': 2023,
                    'region': '全国甲卷',
                    'knowledge_points': [],
                    'difficulty': 3,
                    'score': 5.0,
                    'source_url': '',
                    'teaching_tips': '',
                    'common_mistakes': ''
                })
    
    # 写入目标文件
    total_questions = 0
    for region, qs in papers.items():
        if not qs:
            continue
        
        region_dir = os.path.join(target_dir, region)
        os.makedirs(region_dir, exist_ok=True)
        
        target_file = os.path.join(region_dir, '2023.json')
        
        output_data = {
            'year': 2023,
            'region': region,
            'total_questions': len(qs),
            'questions': qs
        }
        
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        total_questions += len(qs)
        print(f"  已创建: {region}/2023.json ({len(qs)}题)")
    
    return total_questions

if __name__ == '__main__':
    target_dir = r'e:\AI-Educator\dataset\高考\数学\高考数学真题'
    
    print("=" * 60)
    print("2023年高考数学真题数据转换")
    print("=" * 60)
    
    # 读取JSONL文件（假设已经下载）
    jsonl_file = r'e:\AI-Educator\fresh-gaokao-math-2023.jsonl'
    
    if os.path.exists(jsonl_file):
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            jsonl_content = f.read()
        
        total = convert_2023_jsonl_to_json(jsonl_content, target_dir)
        print(f"\n转换完成! 共 {total} 道题目")
    else:
        print(f"文件不存在: {jsonl_file}")
        print("请先下载2023年数据")
