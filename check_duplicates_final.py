"""
检查数据集重复情况
"""

import json
import os
from collections import defaultdict

BASE_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

def main():
    print("=" * 60)
    print("检查数据集重复情况")
    print("=" * 60)
    
    # 收集所有题目
    all_questions = []
    folder_stats = {}
    
    for folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        
        folder_questions = []
        
        for file in sorted(os.listdir(folder_path)):
            if file.endswith('.json'):
                filepath = os.path.join(folder_path, file)
                try:
                    data = json.load(open(filepath, 'r', encoding='utf-8'))
                    questions = data.get('questions', [])
                    for q in questions:
                        q['_source_folder'] = folder
                        q['_source_file'] = file
                        folder_questions.append(q)
                        all_questions.append(q)
                except Exception as e:
                    print(f"  警告: 无法读取 {filepath}: {e}")
        
        folder_stats[folder] = len(folder_questions)
        print(f"\n{folder}: {len(folder_questions)}题")
    
    # 检查重复
    print("\n" + "=" * 60)
    print("检查重复题目...")
    print("=" * 60)
    
    # 使用题目文本进行去重
    question_map = defaultdict(list)
    
    for q in all_questions:
        q_text = q.get('question_text', '')
        # 简化文本用于比较
        simplified = q_text.split('.', 1)[-1].strip()[:100] if '.' in q_text else q_text[:100]
        question_map[simplified].append(q)
    
    # 找出重复
    duplicates = {k: v for k, v in question_map.items() if len(v) > 1}
    
    print(f"\n总题目数: {len(all_questions)}")
    print(f"唯一题目数: {len(question_map)}")
    print(f"重复题目组数: {len(duplicates)}")
    
    if duplicates:
        print("\n重复示例:")
        for i, (text, qs) in enumerate(list(duplicates.items())[:5]):
            print(f"\n{i+1}. {text[:50]}...")
            for q in qs:
                print(f"   - {q['_source_folder']}/{q['_source_file']}")
    
    print("\n" + "=" * 60)
    print("检查完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
