"""
高考数学真题数据集去重脚本
"""

import json
import os
import shutil

BASE_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

def main():
    print("=" * 60)
    print("高考数学真题数据集去重整理")
    print("=" * 60)
    
    # 1. 删除"新课标"文件夹（数据与新课标ⅱ重复）
    print("\n步骤1: 删除重复的'新课标'文件夹")
    xinkebiao_path = os.path.join(BASE_DIR, "新课标")
    if os.path.exists(xinkebiao_path):
        # 统计题目数
        total_q = 0
        for fp in os.listdir(xinkebiao_path):
            if fp.endswith(".json"):
                data = json.load(open(os.path.join(xinkebiao_path, fp), 'r', encoding='utf-8'))
                total_q += data.get('total_questions', 0)
        print(f"  删除'新课标'文件夹 (包含 {total_q} 题，与新课标ⅱ重复)")
        shutil.rmtree(xinkebiao_path)
    else:
        print("  '新课标'文件夹不存在，跳过")
    
    # 2. 重命名文件夹
    print("\n步骤2: 统一文件夹命名")
    
    renames = [
        ("新课标ⅰ", "新课标I卷"),
        ("新课标ⅱ", "新课标II卷"),
        ("新课标ⅲ", "新课标III卷"),
        ("全国卷Ⅲ", "全国卷III"),
    ]
    
    for old_name, new_name in renames:
        old_path = os.path.join(BASE_DIR, old_name)
        new_path = os.path.join(BASE_DIR, new_name)
        
        if os.path.exists(old_path):
            if os.path.exists(new_path):
                # 合并内容
                print(f"  合并 {old_name} -> {new_name}")
                for file in os.listdir(old_path):
                    src = os.path.join(old_path, file)
                    dst = os.path.join(new_path, file)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
                shutil.rmtree(old_path)
            else:
                os.rename(old_path, new_path)
                print(f"  重命名 {old_name} -> {new_name}")
        else:
            print(f"  {old_name} 不存在，跳过")
    
    # 3. 统计最终结果
    print("\n步骤3: 统计最终结果")
    print("-" * 60)
    
    total_regions = 0
    total_files = 0
    total_questions = 0
    year_range = {"min": 9999, "max": 0}
    regions_info = {}
    
    for folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        
        total_regions += 1
        folder_questions = 0
        folder_years = []
        
        for file in sorted(os.listdir(folder_path)):
            if file.endswith('.json'):
                total_files += 1
                filepath = os.path.join(folder_path, file)
                try:
                    data = json.load(open(filepath, 'r', encoding='utf-8'))
                    year = data.get('year', 0)
                    questions = data.get('questions', [])
                    count = len(questions)
                    
                    folder_questions += count
                    folder_years.append(year)
                    total_questions += count
                    
                    if year > 0:
                        year_range["min"] = min(year_range["min"], year)
                        year_range["max"] = max(year_range["max"], year)
                except Exception as e:
                    print(f"  警告: 无法读取 {filepath}: {e}")
        
        if folder_questions > 0:
            years_str = ", ".join(map(str, sorted(set(folder_years))))
            print(f"  {folder:15s}: {folder_questions:4d}题 [{years_str}]")
            regions_info[folder] = {
                "questions": folder_questions,
                "years": sorted(set(folder_years))
            }
    
    print("-" * 60)
    print(f"\n总计:")
    print(f"  地区/试卷类型: {total_regions} 个")
    print(f"  文件数: {total_files} 个")
    print(f"  题目数: {total_questions} 道")
    print(f"  年份范围: {year_range['min']} - {year_range['max']}")
    
    # 保存统计信息
    stats = {
        "total_regions": total_regions,
        "total_files": total_files,
        "total_questions": total_questions,
        "year_range": year_range,
        "regions": regions_info
    }
    
    stats_file = os.path.join(BASE_DIR, "统计报告.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n统计报告已保存到: {stats_file}")
    print("\n" + "=" * 60)
    print("去重整理完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
