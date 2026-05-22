"""
高考真题数据集最终整理脚本
基于现有数据整理成简洁的文件夹结构
"""

import os
import json
import shutil
from pathlib import Path

# 基础路径
BASE_DIR = Path(r"e:\AI-Educator\dataset\高考\数学")
CURRENT_DIR = BASE_DIR / "最终整理"
FINAL_DIR = BASE_DIR / "高考数学真题"

# 文件夹名称映射 - 使用简洁名称
FOLDER_NAME_MAPPING = {
    "全国卷": "全国卷",
    "全国甲卷": "全国甲卷",
    "全国乙卷": "全国乙卷",
    "新课标I": "新课标I",
    "新课标II": "新课标II",
    "新课标III": "新课标III",
    "上海": "上海",
    "北京": "北京",
    "天津": "天津",
}


def load_json_file(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"  加载失败 {file_path}: {e}")
        return None


def organize_final():
    """最终整理"""
    print("=" * 60)
    print("开始最终整理高考真题数据集")
    print("=" * 60)
    
    # 创建最终输出目录
    if FINAL_DIR.exists():
        shutil.rmtree(FINAL_DIR)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    
    # 统计信息
    stats = {}
    total_questions = 0
    
    # 从当前文件夹读取数据
    print("\n【步骤1】整理现有数据...")
    
    for folder in CURRENT_DIR.iterdir():
        if not folder.is_dir() or folder.name == '统计报告.json':
            continue
        
        folder_name = folder.name
        target_name = FOLDER_NAME_MAPPING.get(folder_name, folder_name)
        
        print(f"\n  处理: {folder_name} -> {target_name}")
        
        # 创建目标文件夹
        target_folder = FINAL_DIR / target_name
        target_folder.mkdir(parents=True, exist_ok=True)
        
        folder_stats = {'years': [], 'total_questions': 0}
        
        # 复制所有JSON文件
        for json_file in sorted(folder.glob('*.json')):
            data = load_json_file(json_file)
            if data is None:
                continue
            
            # 更新region字段
            if isinstance(data, dict):
                data['region'] = target_name
                for q in data.get('questions', []):
                    if isinstance(q, dict):
                        q['region'] = target_name
                
                # 保存文件
                output_file = target_folder / json_file.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 统计
                year = data.get('year', 0)
                total = data.get('total_questions', 0)
                if year:
                    folder_stats['years'].append(year)
                    folder_stats['total_questions'] += total
                    total_questions += total
                    print(f"    复制 {json_file.name} ({total}题)")
        
        stats[target_name] = folder_stats
    
    # 生成最终统计报告
    print("\n【步骤2】生成最终统计报告...")
    
    report = {
        '整理时间': '2026-05-17',
        '总计题目数': total_questions,
        '各卷统计': stats
    }
    
    with open(FINAL_DIR / '统计报告.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("最终整理完成！")
    print("=" * 60)
    print(f"\n输出目录: {FINAL_DIR}")
    print(f"\n统计信息:")
    for folder_name, info in sorted(stats.items()):
        print(f"  {folder_name}: {info['total_questions']}题, 年份{sorted(info['years'])}")
    
    print(f"\n总计: {total_questions}道题目")
    
    # 清理旧文件夹
    print("\n【步骤3】清理旧文件夹...")
    folders_to_clean = [
        CURRENT_DIR,
        BASE_DIR / "新课标",
    ]
    
    for folder_path in folders_to_clean:
        if folder_path.exists():
            try:
                if folder_path.is_file():
                    folder_path.unlink()
                    print(f"  已删除文件: {folder_path.name}")
                else:
                    shutil.rmtree(folder_path)
                    print(f"  已删除文件夹: {folder_path.name}")
            except Exception as e:
                print(f"  删除失败 {folder_path.name}: {e}")
    
    print("\n清理完成！")


if __name__ == '__main__':
    organize_final()
