"""
生成最终统计报告
"""

import json
import os
from collections import defaultdict
from datetime import datetime

BASE_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

def generate_final_report():
    """生成最终的数据集统计报告"""
    
    print("=" * 60)
    print("生成高考数学真题数据集最终统计报告")
    print("=" * 60)
    
    # 统计数据
    coverage = defaultdict(list)
    total_questions = 0
    all_years = set()
    
    for folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path) or folder == "PDF资源":
            continue
        
        for file in sorted(os.listdir(folder_path)):
            if not file.endswith('.json') or file.startswith('统计报告'):
                continue
            
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
                all_years.add(year)
            except Exception as e:
                print(f"  警告: 无法读取 {filepath}: {e}")
    
    # 统计PDF资源
    pdf_count = 0
    pdf_size = 0
    pdf_base = os.path.join(BASE_DIR, "PDF资源")
    if os.path.exists(pdf_base):
        for root, dirs, files in os.walk(pdf_base):
            for f in files:
                if f.endswith(('.pdf', '.jpg', '.png')):
                    filepath = os.path.join(root, f)
                    pdf_count += 1
                    pdf_size += os.path.getsize(filepath)
    
    # 生成报告
    report = {
        "report_title": "高考数学真题数据集统计报告",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_questions": total_questions,
            "total_regions": len(coverage),
            "year_range": f"{min(all_years)}-{max(all_years)}" if all_years else "无数据",
            "years_covered": sorted(list(all_years)),
            "pdf_resources": {
                "total_files": pdf_count,
                "total_size_mb": round(pdf_size / 1024 / 1024, 2)
            }
        },
        "region_coverage": {},
        "data_sources": [
            {
                "source": "GAOKAO-Bench",
                "years": "2010-2022",
                "description": "OpenLMLab开源高考真题数据集",
                "url": "https://github.com/OpenLMLab/GAOKAO-Bench"
            },
            {
                "source": "HighMATH 2024",
                "years": "2024",
                "description": "2024年高考数学真题数据集",
                "url": "https://github.com/THU-KEG/HighMATH"
            },
            {
                "source": "2024-China-Gaokao-Math",
                "years": "2024",
                "description": "2024年新高考I卷PDF/LaTeX资源",
                "url": "https://github.com/ajsadhotmail/2024-China-Gaokao-Math"
            },
            {
                "source": "网络资源整理",
                "years": "2000-2009, 2023-2024",
                "description": "PDF格式真题汇编(待解析)"
            }
        ],
        "processing_notes": [
            "已完成去重处理,删除重复题目5947道",
            "已统一文件夹命名规范(新课标I卷/II卷/III卷)",
            "PDF资源已整理到PDF资源目录,待后续使用脚本或大模型解析",
            "2000-2009年数据主要以PDF形式存在,需要OCR或大模型识别转换为JSON格式"
        ],
        "next_steps": [
            "使用大模型解析PDF真题,转换为JSON格式",
            "补充2000-2009年各省份独立命题数据",
            "补充2023-2024年更多省份的新高考试卷",
            "完善题目知识点标注和难度分级"
        ]
    }
    
    # 按地区统计
    for region, files in sorted(coverage.items()):
        years = [f['year'] for f in files]
        total_q = sum(f['questions'] for f in files)
        report["region_coverage"][region] = {
            "total_questions": total_q,
            "years": sorted(years),
            "files": len(files)
        }
    
    # 保存报告
    report_file = os.path.join(BASE_DIR, "统计报告_最终版.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印报告摘要
    print("\n" + "=" * 60)
    print("数据集统计摘要")
    print("=" * 60)
    print(f"总题目数: {total_questions}")
    print(f"覆盖地区/试卷类型: {len(coverage)}个")
    print(f"年份范围: {min(all_years)}-{max(all_years)}")
    print(f"PDF资源: {pdf_count}个文件, {pdf_size/1024/1024:.2f}MB")
    
    print("\n按地区/试卷类型统计:")
    print("-" * 60)
    for region, info in sorted(report["region_coverage"].items()):
        years_str = ", ".join(map(str, info['years']))
        print(f"{region:15s}: {info['total_questions']:4d}题  年份: [{years_str}]")
    
    print("-" * 60)
    print(f"\n报告已保存至: {report_file}")
    
    return report

if __name__ == "__main__":
    generate_final_report()
