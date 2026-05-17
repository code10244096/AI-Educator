"""
按省份重新组织高考数学真题数据
将现有的全国卷数据按卷别分类，并保存到以省份命名的文件夹下
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List


# 卷别到省份的映射
REGION_TO_PROVINCE = {
    "全国甲卷": ["四川", "陕西", "内蒙古", "宁夏", "青海"],
    "全国乙卷": ["河南", "山西", "江西", "安徽", "甘肃", "黑龙江"],
    "新课标Ⅰ": ["山东", "广东", "湖南", "湖北", "河北", "江苏", "福建", "浙江"],
    "新课标Ⅱ": ["辽宁", "重庆", "海南", "吉林", "黑龙江", "山西", "云南", "广西"],
    "新课标Ⅲ": ["四川", "云南", "贵州", "广西", "西藏"],
}

# 卷别名称标准化
REGION_NAME_MAP = {
    "（全国乙卷）": "全国乙卷",
    "（全国甲卷）": "全国甲卷",
    "（新课标Ⅰ）": "新课标Ⅰ",
    "（新课标Ⅱ）": "新课标Ⅱ",
    "（新课标Ⅲ）": "新课标Ⅲ",
    "（新课标ⅰ）": "新课标Ⅰ",
    "（新课标ⅱ）": "新课标Ⅱ",
    "（新课标ⅲ）": "新课标Ⅲ",
    "（新课标）": "新课标Ⅰ",
    "（全国卷Ⅲ）": "新课标Ⅲ",
}


def get_base_dir() -> str:
    """获取基础目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_source_dir() -> str:
    """获取源数据目录"""
    return os.path.join(
        get_base_dir(),
        "dataset",
        "高考",
        "数学",
        "全国卷数学真题"
    )


def get_target_dir() -> str:
    """获取目标数据目录"""
    return os.path.join(
        get_base_dir(),
        "dataset",
        "高考",
        "数学"
    )


def normalize_region(region: str) -> str:
    """标准化卷别名称"""
    return REGION_NAME_MAP.get(region, region)


def reorganize_data():
    """重新组织数据"""
    source_dir = get_source_dir()
    target_dir = get_target_dir()
    
    print("="*60)
    print("开始按省份重新组织高考数学真题数据")
    print("="*60)
    
    # 获取所有年份的JSON文件
    json_files = sorted([
        f for f in os.listdir(source_dir)
        if f.endswith('.json') and f[:4].isdigit()
    ])
    
    print(f"\n找到 {len(json_files)} 个年份文件\n")
    
    # 按卷别组织数据
    region_data = {}
    
    for filename in json_files:
        filepath = os.path.join(source_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            year = data.get('year', filename[:4])
            questions = data.get('questions', [])
            
            # 按卷别分组
            for question in questions:
                region = normalize_region(question.get('region', '未知卷别'))
                
                if region not in region_data:
                    region_data[region] = {}
                
                if year not in region_data[region]:
                    region_data[region][year] = []
                
                region_data[region][year].append(question)
            
            print(f"✓ 处理 {filename}: {len(questions)} 道题")
            
        except Exception as e:
            print(f"✗ 处理 {filename} 失败: {str(e)}")
    
    # 保存到以卷别命名的文件夹
    print("\n" + "="*60)
    print("保存数据到各省份文件夹")
    print("="*60 + "\n")
    
    for region, years_data in region_data.items():
        # 创建卷别文件夹
        region_dir = os.path.join(target_dir, region)
        os.makedirs(region_dir, exist_ok=True)
        
        total_questions = 0
        
        for year, questions in years_data.items():
            # 保存该年份的数据
            output_file = os.path.join(region_dir, f"{year}.json")
            
            output_data = {
                "year": int(year) if str(year).isdigit() else year,
                "region": region,
                "total_questions": len(questions),
                "questions": questions
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            total_questions += len(questions)
            print(f"  ✓ {region} {year}年: {len(questions)} 道题")
        
        print(f"  📊 {region} 总计: {total_questions} 道题\n")
    
    # 创建省份索引文件
    print("\n" + "="*60)
    print("创建省份索引文件")
    print("="*60 + "\n")
    
    province_index = {}
    
    for region, provinces in REGION_TO_PROVINCE.items():
        if region in region_data:
            for province in provinces:
                province_index[province] = {
                    "region": region,
                    "years": sorted(region_data[region].keys()),
                    "total_questions": sum(len(qs) for qs in region_data[region].values())
                }
    
    # 保存索引文件
    index_file = os.path.join(target_dir, "省份索引.json")
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(province_index, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 省份索引已保存到: {index_file}")
    
    # 打印统计信息
    print("\n" + "="*60)
    print("数据统计")
    print("="*60 + "\n")
    
    total_all = 0
    for region, years_data in sorted(region_data.items()):
        total = sum(len(qs) for qs in years_data.values())
        total_all += total
        years = sorted([str(y) for y in years_data.keys()])
        print(f"  {region}: {total} 道题 ({', '.join(years)}年)")
    
    print(f"\n  总计: {total_all} 道题")
    print(f"  卷别数: {len(region_data)}")
    print(f"  省份数: {len(province_index)}")


if __name__ == "__main__":
    reorganize_data()
