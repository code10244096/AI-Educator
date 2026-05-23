"""
对新增数据进行去重筛选,避免与已有数据重复
"""

import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

BASE_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

def normalize_text(text):
    """标准化题目文本用于比较"""
    if not text:
        return ""
    # 移除题号前缀
    text = text.strip()
    # 移除开头的数字和点
    import re
    text = re.sub(r'^\d+\.\s*', '', text)
    # 移除LaTeX标记
    text = text.replace('\\', '').replace('{', '').replace('}', '')
    text = text.replace('$', '').replace('_', '')
    # 取前150个字符作为比较键
    return text[:150].lower().strip()

def load_existing_questions():
    """加载已有的所有题目"""
    existing = set()
    existing_details = []
    
    for folder in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        
        for file in os.listdir(folder_path):
            if not file.endswith('.json') or file.startswith('统计报告'):
                continue
            
            filepath = os.path.join(folder_path, file)
            try:
                data = json.load(open(filepath, 'r', encoding='utf-8'))
                year = data.get('year', 0)
                region = data.get('region', folder)
                
                for q in data.get('questions', []):
                    q_text = q.get('question_text', '')
                    normalized = normalize_text(q_text)
                    if normalized:
                        existing.add(normalized)
                        existing_details.append({
                            'year': year,
                            'region': region,
                            'file': file,
                            'question': q_text[:100]
                        })
            except Exception as e:
                print(f"  警告: 无法读取 {filepath}: {e}")
    
    return existing, existing_details

def process_new_files(existing_set):
    """处理新增文件,去重"""
    stats = {
        'total_new_files': 0,
        'total_new_questions': 0,
        'duplicate_questions': 0,
        'unique_questions': 0,
        'files_with_duplicates': [],
        'files_removed': [],
        'files_updated': []
    }
    
    for folder in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        
        for file in os.listdir(folder_path):
            if not file.endswith('.json') or file.startswith('统计报告'):
                continue
            
            filepath = os.path.join(folder_path, file)
            mod_time = os.path.getmtime(filepath)
            
            # 只处理最近修改的文件(新转换的)
            # 这里我们处理所有文件,但记录哪些是新增的
            
            try:
                data = json.load(open(filepath, 'r', encoding='utf-8'))
                year = data.get('year', 0)
                region = data.get('region', folder)
                questions = data.get('questions', [])
                
                stats['total_new_files'] += 1
                stats['total_new_questions'] += len(questions)
                
                # 检查重复
                unique_questions = []
                duplicates = 0
                
                for q in questions:
                    q_text = q.get('question_text', '')
                    normalized = normalize_text(q_text)
                    
                    if normalized and normalized in existing_set:
                        duplicates += 1
                    else:
                        unique_questions.append(q)
                        if normalized:
                            existing_set.add(normalized)
                
                stats['duplicate_questions'] += duplicates
                stats['unique_questions'] += len(unique_questions)
                
                if duplicates > 0:
                    stats['files_with_duplicates'].append({
                        'file': f"{folder}/{file}",
                        'total': len(questions),
                        'duplicates': duplicates,
                        'unique': len(unique_questions)
                    })
                    
                    # 更新文件,只保留不重复的题目
                    if len(unique_questions) == 0:
                        # 全部重复,删除文件
                        os.remove(filepath)
                        stats['files_removed'].append(f"{folder}/{file}")
                        print(f"  删除: {folder}/{file} (全部{duplicates}题重复)")
                    else:
                        # 部分重复,更新文件
                        data['questions'] = unique_questions
                        data['total_questions'] = len(unique_questions)
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        stats['files_updated'].append(f"{folder}/{file}")
                        print(f"  更新: {folder}/{file} (删除{duplicates}题重复, 保留{len(unique_questions)}题)")
                
            except Exception as e:
                print(f"  警告: 处理 {filepath} 时出错: {e}")
    
    return stats

def main():
    print("=" * 60)
    print("高考数学真题数据去重筛选")
    print("=" * 60)
    
    # 加载已有题目
    print("\n步骤1: 加载已有题目...")
    existing_set, existing_details = load_existing_questions()
    print(f"  已加载 {len(existing_set)} 道题目")
    
    # 处理新文件
    print("\n步骤2: 处理新增文件并去重...")
    stats = process_new_files(existing_set)
    
    # 输出统计
    print("\n" + "=" * 60)
    print("去重结果统计")
    print("=" * 60)
    print(f"处理文件数: {stats['total_new_files']}")
    print(f"新增题目总数: {stats['total_new_questions']}")
    print(f"重复题目数: {stats['duplicate_questions']}")
    print(f"唯一题目数: {stats['unique_questions']}")
    print(f"删除文件数: {len(stats['files_removed'])}")
    print(f"更新文件数: {len(stats['files_updated'])}")
    
    if stats['files_with_duplicates']:
        print("\n有重复的文件:")
        for f in stats['files_with_duplicates']:
            print(f"  {f['file']}: {f['duplicates']}/{f['total']} 题重复")

if __name__ == "__main__":
    main()
