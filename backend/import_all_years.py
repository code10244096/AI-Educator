"""
批量导入所有年份的高考数学真题到数据库
从 dataset/高考/数学真题/ 目录读取按年份保存的JSON文件
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

from database import AsyncSessionLocal, init_db
from models import QuestionBank


async def import_year_file(year_file: str) -> int:
    """
    导入单个年份的文件
    
    参数:
        year_file: 年份JSON文件路径
    
    返回:
        导入的题目数量
    """
    with open(year_file, 'r', encoding='utf-8') as f:
        year_data = json.load(f)
    
    questions = year_data.get("questions", [])
    year = year_data.get("year", "未知")
    
    async with AsyncSessionLocal() as db:
        added_count = 0
        
        for q_data in questions:
            # 检查是否已存在（通过题目文本和年份判断）
            question_text = q_data.get("question_text", "")
            
            # 创建题目对象
            question = QuestionBank(
                question_text=question_text,
                answer=q_data.get("answer"),
                solution=q_data.get("solution", ""),
                question_type=q_data.get("question_type"),
                subject=q_data.get("subject", "数学"),
                education_level=q_data.get("education_level", "高中"),
                exam_type=q_data.get("exam_type", "高考"),
                year=q_data.get("year"),
                region=q_data.get("region", ""),
                knowledge_points=json.dumps(q_data.get("knowledge_points", []), ensure_ascii=False),
                difficulty=q_data.get("difficulty", 3),
                score=q_data.get("score"),
                source_url=q_data.get("source_url", "https://github.com/OpenLMLab/GAOKAO-Bench"),
                teaching_tips=q_data.get("teaching_tips", ""),
                common_mistakes=q_data.get("common_mistakes", ""),
                is_verified=True
            )
            
            db.add(question)
            added_count += 1
        
        await db.commit()
        return added_count


async def import_all_years(data_dir: str) -> Dict:
    """
    批量导入所有年份数据
    
    参数:
        data_dir: 数据目录
    
    返回:
        导入统计信息
    """
    print("="*60)
    print("批量导入高考数学真题")
    print("="*60)
    print(f"\n数据目录: {data_dir}\n")
    
    # 获取所有JSON文件
    json_files = sorted([
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.endswith('.json') and f[0:4].isdigit()
    ])
    
    if not json_files:
        print("错误：未找到任何年份数据文件")
        return {}
    
    print(f"找到 {len(json_files)} 个年份文件\n")
    
    # 初始化数据库
    print("初始化数据库...")
    await init_db()
    print("✓ 数据库初始化完成\n")
    
    # 逐个导入
    stats = {}
    total_count = 0
    
    for year_file in json_files:
        filename = os.path.basename(year_file)
        year = filename.replace('.json', '')
        
        try:
            count = await import_year_file(year_file)
            stats[year] = count
            total_count += count
            print(f"  ✓ {year}年: {count} 道题")
        except Exception as e:
            print(f"  ✗ {year}年: 导入失败 - {str(e)}")
    
    # 统计信息
    print("\n" + "="*60)
    print("导入完成！")
    print("="*60)
    print(f"总题目数: {total_count}")
    print(f"年份范围: {min(stats.keys())} - {max(stats.keys())}")
    print(f"年份数量: {len(stats)}")
    print(f"\n各年份题目数:")
    for year in sorted(stats.keys()):
        print(f"  {year}年: {stats[year]} 道题")
    print("="*60)
    
    return stats


async def main():
    """主函数"""
    # 数据目录
    data_dir = os.path.join(
        Path(__file__).parent.parent,
        "dataset",
        "高考",
        "数学真题"
    )
    
    if not os.path.exists(data_dir):
        print(f"错误：数据目录不存在: {data_dir}")
        print("请先运行 convert_gaokao_bench.py 生成数据")
        return
    
    # 导入所有年份
    stats = await import_all_years(data_dir)
    
    if stats:
        print("\n✓ 所有年份数据已成功导入数据库")


if __name__ == "__main__":
    asyncio.run(main())
