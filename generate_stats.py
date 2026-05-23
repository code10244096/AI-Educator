import json
import os
from pathlib import Path
from collections import defaultdict

def generate_statistics(target_dir):
    """生成数据集统计报告"""
    
    stats = {
        "total_regions": 0,
        "total_files": 0,
        "total_questions": 0,
        "year_range": {"min": 9999, "max": 0},
        "regions": {},
        "year_distribution": defaultdict(int),
        "question_type_distribution": defaultdict(int),
    }
    
    target_path = Path(target_dir)
    
    for region_dir in sorted(target_path.iterdir()):
        if not region_dir.is_dir():
            continue
        
        region_name = region_dir.name
        region_stats = {
            "files": 0,
            "questions": 0,
            "years": []
        }
        
        for json_file in sorted(region_dir.glob("*.json")):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            year = data.get('year', 0)
            questions = data.get('questions', [])
            total_q = len(questions)
            
            region_stats["files"] += 1
            region_stats["questions"] += total_q
            region_stats["years"].append(year)
            
            stats["total_files"] += 1
            stats["total_questions"] += total_q
            stats["year_range"]["min"] = min(stats["year_range"]["min"], year)
            stats["year_range"]["max"] = max(stats["year_range"]["max"], year)
            stats["year_distribution"][year] += total_q
            
            # 统计题型
            for q in questions:
                q_type = q.get('question_type', '未知')
                stats["question_type_distribution"][q_type] += 1
        
        if region_stats["files"] > 0:
            stats["total_regions"] += 1
            stats["regions"][region_name] = region_stats
    
    # 生成报告
    report = []
    report.append("=" * 70)
    report.append("高考数学真题数据集统计报告")
    report.append("=" * 70)
    report.append("")
    report.append(f"数据覆盖范围:")
    report.append(f"  - 年份范围: {stats['year_range']['min']} - {stats['year_range']['max']}")
    report.append(f"  - 省份/试卷类型: {stats['total_regions']} 个")
    report.append(f"  - 总文件数: {stats['total_files']} 个")
    report.append(f"  - 总题目数: {stats['total_questions']} 道")
    report.append("")
    
    report.append("各省份/试卷类型分布:")
    report.append("-" * 70)
    for region, r_stats in sorted(stats["regions"].items()):
        years_str = ", ".join(map(str, sorted(r_stats["years"])))
        report.append(f"  {region:15s}: {r_stats['files']:3d}个文件, {r_stats['questions']:4d}题 [{years_str}]")
    report.append("")
    
    report.append("年份分布:")
    report.append("-" * 70)
    for year in sorted(stats["year_distribution"].keys()):
        count = stats["year_distribution"][year]
        bar = "█" * (count // 5)
        report.append(f"  {year}: {count:4d}题 {bar}")
    report.append("")
    
    report.append("题型分布:")
    report.append("-" * 70)
    for q_type, count in sorted(stats["question_type_distribution"].items()):
        percentage = (count / stats["total_questions"]) * 100
        report.append(f"  {q_type:10s}: {count:4d}题 ({percentage:.1f}%)")
    report.append("")
    
    report.append("=" * 70)
    report.append("数据来源: GAOKAO-Bench (复旦大学)")
    report.append("整理时间: 2026-05-23")
    report.append("=" * 70)
    
    return "\n".join(report), stats

if __name__ == "__main__":
    target_dir = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"
    
    report, stats = generate_statistics(target_dir)
    print(report)
    
    # 保存统计报告
    report_file = os.path.join(target_dir, "统计报告_GAOKAO-Bench.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n统计报告已保存到: {report_file}")
