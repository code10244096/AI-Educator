"""
优化JSON格式，使其更适合教案模型检索使用
"""

import json
import re
from pathlib import Path

# 基础路径
BASE_DIR = Path(r"e:\AI-Educator\dataset\高考\数学\高考数学真题")


def detect_question_type(question_text, answer):
    """根据题目内容检测题目类型"""
    text = question_text.lower()
    
    # 选择题特征
    if re.search(r'[A-D][\.\、\s]', text) or re.search(r'选项|选择', text):
        return '选择题'
    
    # 填空题特征
    if '______' in text or '____' in text or '填空' in text:
        return '填空题'
    
    # 解答题特征
    if re.search(r'解答|证明|求解|计算', text):
        return '解答题'
    
    # 根据答案判断
    if answer and len(answer) <= 5:
        if re.match(r'^[A-D]$', answer.strip()):
            return '选择题'
        return '填空题'
    
    return '解答题'


def optimize_question(question):
    """优化单道题目"""
    # 检测题目类型
    question_type = detect_question_type(
        question.get('question_text', ''),
        question.get('answer', '')
    )
    question['question_type'] = question_type
    
    # 确保region字段存在
    if 'region' not in question:
        question['region'] = '未知'
    
    # 确保knowledge_points是列表
    if not question.get('knowledge_points'):
        question['knowledge_points'] = []
    
    # 清理空白字符
    for field in ['question_text', 'answer', 'solution']:
        if field in question and question[field]:
            question[field] = question[field].strip()
    
    return question


def optimize_file(file_path):
    """优化单个JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or 'questions' not in data:
            return False
        
        # 优化每道题目
        optimized_count = 0
        for question in data['questions']:
            if isinstance(question, dict):
                optimize_question(question)
                optimized_count += 1
        
        # 保存优化后的数据
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"  优化 {file_path.name}: {optimized_count}道题")
        return True
        
    except Exception as e:
        print(f"  优化失败 {file_path}: {e}")
        return False


def optimize_all():
    """优化所有JSON文件"""
    print("=" * 60)
    print("开始优化JSON格式")
    print("=" * 60)
    
    total_files = 0
    total_questions = 0
    
    # 遍历所有文件夹
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir():
            continue
        
        print(f"\n【处理】{folder.name}")
        
        # 遍历所有JSON文件
        for json_file in folder.glob('*.json'):
            if json_file.name == '统计报告.json':
                continue
            
            if optimize_file(json_file):
                total_files += 1
                # 统计题目数
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    total_questions += data.get('total_questions', 0)
                except:
                    pass
    
    print("\n" + "=" * 60)
    print("优化完成！")
    print("=" * 60)
    print(f"  优化文件数: {total_files}")
    print(f"  优化题目数: {total_questions}")


if __name__ == '__main__':
    optimize_all()
