"""
分析当前数据集覆盖情况
"""

import json
import os
from collections import defaultdict

BASE_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

def main():
    print("=" * 60)
    print("当前数据集覆盖情况分析")
    print("=" * 60)
    
    coverage = defaultdict(list)
    total_questions = 0
    
    for folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        
        for file in sorted(os.listdir(folder_path)):
            if file.endswith('.json'):
                filepath = os.path.join(folder_path, file)
                try:
                    data = json.load(open(filepath, 'r', encoding='utf-8'))
                    year = data.get('year', 0)
                    region = data.get('region', folder)
                    questions = data.get('questions', [])
                    count = len(questions)
                    
                    coverage[region].append({
                        'year': year,
                        'file': file,
                        'questions': count
                    })
                    total_questions += count
                except Exception as e:
                    print(f"  警告: 无法读取 {filepath}: {e}")
    
    # 按地区统计
    print("\n按地区/试卷类型统计:")
    print("-" * 60)
    
    all_years = set()
    for region, files in sorted(coverage.items()):
        years = [f['year'] for f in files]
        total_q = sum(f['questions'] for f in files)
        all_years.update(years)
        years_str = ", ".join(map(str, sorted(years)))
        print(f"{region:15s}: {total_q:4d}题  年份: [{years_str}]")
    
    print("-" * 60)
    print(f"\n总题目数: {total_questions}")
    print(f"覆盖年份: {min(all_years)} - {max(all_years)}")
    print(f"覆盖年份列表: {', '.join(map(str, sorted(all_years)))}")
    
    # 分析缺失
    print("\n" + "=" * 60)
    print("需要补充的数据:")
    print("=" * 60)
    
    # 2000-2012年完全缺失
    print("\n1. 2000-2012年数据（完全缺失）")
    print("   - 全国卷（大纲版）")
    print("   - 北京卷、上海卷、天津卷等自主命题省份")
    print("   - 江苏、浙江、山东、广东等省份")
    
    # 2013-2022年部分缺失
    print("\n2. 2013-2022年数据（部分缺失）")
    print("   - 部分省份的独立命题数据")
    print("   - 新高考改革后的新高考I卷、II卷数据不全")
    
    # 2023-2024年部分缺失
    print("\n3. 2023-2024年数据（部分缺失）")
    print("   - 更多省份的新高考试卷")


if __name__ == "__main__":
    main()
