"""
地方卷数据整理脚本
将上海、北京、天津卷的txt文件转换为JSON格式并整合
"""

import os
import json
import shutil
from pathlib import Path
import re

# 基础路径
BASE_DIR = Path(r"e:\AI-Educator\dataset\高考\数学")
RAW_BASE = BASE_DIR
TARGET_DIR = BASE_DIR / "高考数学真题"

# 省份映射
PROVINCE_MAPPING = {
    "上海卷": "上海",
    "北京卷": "北京",
    "天津卷": "天津",
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


def parse_txt_questions(txt_content, region, year):
    """从txt文件解析题目"""
    questions = []
    
    lines = txt_content.split('\n')
    
    current_question = None
    current_type = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检测题号 - 支持多种格式
        match = re.match(r'^(\d+)[\.\、\．]\s*(?:\(\d+分\))?\s*(.+)$', line)
        if match and len(line) < 300:
            # 保存上一题
            if current_question:
                questions.append(current_question)
            
            current_question = {
                'question_text': line,
                'answer': '',
                'solution': '',
                'question_type': '未知',
                'subject': '数学',
                'education_level': '高中',
                'exam_type': '高考',
                'year': year,
                'region': region,
                'knowledge_points': [],
                'difficulty': 3,
                'score': 5.0,
                'source_url': '',
                'teaching_tips': '',
                'common_mistakes': ''
            }
            current_type = 'question'
        elif current_question:
            # 检测答案
            if '【答案】' in line or line.startswith('答案'):
                current_type = 'answer'
                current_question['answer'] = line.replace('【答案】', '').replace('答案', '').strip()
            elif '【解析】' in line or line.startswith('解析') or '【分析】' in line or '【解答】' in line:
                current_type = 'solution'
                current_question['solution'] += '\n' + line
            elif current_type == 'answer':
                current_question['answer'] += ' ' + line
            elif current_type == 'solution':
                current_question['solution'] += '\n' + line
            else:
                current_question['question_text'] += '\n' + line
    
    # 保存最后一题
    if current_question:
        questions.append(current_question)
    
    return questions


def process_raw_folder(raw_dir, target_region):
    """处理raw文件夹，将txt转换为json"""
    all_questions = []
    
    for txt_file in raw_dir.glob('*.txt'):
        # 从文件名提取年份
        filename = txt_file.stem
        year_match = re.search(r'(\d{4})', filename)
        year = int(year_match.group(1)) if year_match else 2024
        
        print(f"  处理 {txt_file.name} (年份: {year})")
        
        try:
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 跳过404错误页面
            if '404' in content[:500]:
                print(f"    跳过404页面")
                continue
            
            # 解析题目
            questions = parse_txt_questions(content, target_region, year)
            all_questions.extend(questions)
            print(f"    解析到 {len(questions)} 道题目")
            
        except Exception as e:
            print(f"    处理失败: {e}")
    
    return all_questions


def merge_questions(questions_list):
    """合并题目列表，去除重复"""
    merged = []
    seen_texts = set()
    
    for q in questions_list:
        # 生成题目特征
        text = q.get('question_text', '')
        # 清理文本
        clean = re.sub(r'^\d+[\.\、\s]+', '', text.strip())[:100]
        
        # 检查是否重复
        is_dup = False
        for seen in seen_texts:
            if clean[:50] and seen[:50] and clean[:50] == seen[:50]:
                is_dup = True
                break
        
        if not is_dup:
            merged.append(q)
            seen_texts.add(clean)
    
    return merged


def organize_province_data():
    """整理地方卷数据"""
    print("=" * 60)
    print("开始整理地方卷数据")
    print("=" * 60)
    
    # 统计信息
    stats = {}
    
    # 处理每个省份
    for province_folder, target_name in PROVINCE_MAPPING.items():
        province_path = RAW_BASE / province_folder
        if not province_path.exists():
            print(f"\n  跳过: {province_folder} (不存在)")
            continue
        
        print(f"\n【处理】{province_folder} -> {target_name}")
        
        # 查找raw文件夹
        raw_dir = province_path / "raw"
        if not raw_dir.exists():
            print(f"  跳过: 没有找到raw文件夹")
            continue
        
        # 处理raw文件夹
        questions = process_raw_folder(raw_dir, target_name)
        
        if not questions:
            print(f"  没有解析到题目")
            continue
        
        # 去重
        merged = merge_questions(questions)
        print(f"  去重后: {len(merged)} 道题目")
        
        # 按年份分组
        by_year = {}
        for q in merged:
            year = q.get('year', 0)
            if year:
                if year not in by_year:
                    by_year[year] = []
                by_year[year].append(q)
        
        # 创建目标文件夹
        target_folder = TARGET_DIR / target_name
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # 保存每年的题目
        province_stats = {'years': [], 'total_questions': 0}
        
        for year, year_questions in sorted(by_year.items()):
            output_file = target_folder / f"{year}.json"
            
            output_data = {
                'year': year,
                'region': target_name,
                'total_questions': len(year_questions),
                'questions': year_questions
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"    保存 {year}.json ({len(year_questions)}题)")
            
            province_stats['years'].append(year)
            province_stats['total_questions'] += len(year_questions)
        
        stats[target_name] = province_stats
    
    # 更新统计报告
    print("\n【更新统计报告】")
    report_file = TARGET_DIR / "统计报告.json"
    
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
    else:
        report = {
            '整理时间': '2026-05-17',
            '总计题目数': 0,
            '各卷统计': {}
        }
    
    # 合并统计信息
    for province_name, province_stats in stats.items():
        report['各卷统计'][province_name] = province_stats
    
    # 重新计算总计
    total = sum(info['total_questions'] for info in report['各卷统计'].values())
    report['总计题目数'] = total
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("地方卷整理完成！")
    print("=" * 60)
    print(f"\n统计信息:")
    for folder_name, info in sorted(report['各卷统计'].items()):
        print(f"  {folder_name}: {info['total_questions']}题, 年份{sorted(info['years'])}")
    
    print(f"\n总计: {report['总计题目数']}道题目")


if __name__ == '__main__':
    organize_province_data()
