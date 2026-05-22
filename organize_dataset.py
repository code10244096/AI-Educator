"""
高考真题数据集整理脚本
功能：
1. 去重与合并（新课标系列、全国卷系列等）
2. 格式整理（.txt转.json）
3. 按省份重新组织文件夹结构
"""

import os
import json
import shutil
from pathlib import Path
from collections import defaultdict
import re

# 基础路径
BASE_DIR = Path(r"e:\AI-Educator\dataset\高考\数学")
OUTPUT_DIR = BASE_DIR / "整理后"

# 文件夹名称映射（去重合并规则）- 使用简洁名称
FOLDER_MAPPING = {
    # 新课标系列合并 - 使用简洁名称
    "新课标Ⅰ": "新课标I",
    "新课标I": "新课标I",
    "新课标 I": "新课标I",
    "新课标Ⅰ卷": "新课标I",
    "新课标Ⅱ": "新课标II",
    "新课标II": "新课标II",
    "新课标Ⅱ卷": "新课标II",
    "新课标卷": "新课标I",  # 早期新课标合并到新课标I
    "新课标Ⅲ": "新课标III",
    "新课标Ⅲ卷": "新课标III",
    # 全国卷系列
    "全国卷数学真题": "全国卷",
    "全国甲卷": "全国甲卷",
    "全国甲卷卷": "全国甲卷",
    "全国乙卷": "全国乙卷",
    "全国汇总卷": "全国卷",
    # 省份卷 - 使用简洁名称
    "上海卷": "上海",
    "北京卷": "北京",
    "天津卷": "天津",
}

# 地区名称标准化 - 使用简洁名称
REGION_MAPPING = {
    "（新课标ⅰ）": "新课标I",
    "（新课标）": "新课标I",
    "新课标": "新课标I",
    "新课标I": "新课标I",
    "新课标 I": "新课标I",
    "（新课标ⅱ）": "新课标II",
    "（新课标Ⅱ）": "新课标II",
    "新课标Ⅱ": "新课标II",
    "新课标II": "新课标II",
    "（新课标ⅲ）": "新课标III",
    "（新课标Ⅲ）": "新课标III",
    "新课标Ⅲ": "新课标III",
    "（全国甲卷）": "全国甲卷",
    "全国甲卷": "全国甲卷",
    "（全国乙卷）": "全国乙卷",
    "全国乙卷": "全国乙卷",
    "全国卷": "全国卷",
    "上海卷": "上海",
    "上海": "上海",
    "北京卷": "北京",
    "北京": "北京",
    "天津卷": "天津",
    "天津": "天津",
}


def normalize_region(region_str):
    """标准化地区名称"""
    if not region_str:
        return ""
    region_str = region_str.strip()
    # 先尝试直接映射
    if region_str in REGION_MAPPING:
        return REGION_MAPPING[region_str]
    # 尝试去掉括号
    clean = region_str.replace("（", "").replace("）", "").replace("(", "").replace(")", "").strip()
    if clean in REGION_MAPPING:
        return REGION_MAPPING[clean]
    # 尝试小写匹配
    lower = region_str.lower()
    for key, value in REGION_MAPPING.items():
        if key.lower() == lower:
            return value
    return region_str


def load_json_file(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"  加载失败 {file_path}: {e}")
        return None


def extract_questions_from_json(data, source_region=None):
    """从JSON数据中提取题目列表"""
    questions = []
    
    if isinstance(data, list):
        # 直接是题目列表
        for q in data:
            if isinstance(q, dict) and 'question_text' in q:
                if source_region:
                    q['region'] = normalize_region(q.get('region', source_region))
                questions.append(q)
    elif isinstance(data, dict):
        # 包含questions字段
        if 'questions' in data:
            region = data.get('region', source_region)
            year = data.get('year')
            for q in data['questions']:
                if isinstance(q, dict) and 'question_text' in q:
                    q['region'] = normalize_region(q.get('region', region))
                    if year and 'year' not in q:
                        q['year'] = year
                    questions.append(q)
        # 或者本身就是单条题目
        elif 'question_text' in data:
            if source_region:
                data['region'] = normalize_region(data.get('region', source_region))
            questions.append(data)
    
    return questions


def is_duplicate_question(q1, q2):
    """判断两道题是否重复（基于题目文本）"""
    # 清理题目文本进行比较
    def clean_text(text):
        if not text:
            return ""
        # 移除题号前缀
        text = re.sub(r'^\d+[\.\、\s]+', '', text.strip())
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        return text[:200]  # 只比较前200字符
    
    text1 = clean_text(q1.get('question_text', ''))
    text2 = clean_text(q2.get('question_text', ''))
    
    # 如果题目文本相似度很高，认为是重复
    if text1 and text2:
        # 简单的前缀匹配
        min_len = min(len(text1), len(text2))
        if min_len > 50:
            common = sum(1 for a, b in zip(text1[:100], text2[:100]) if a == b)
            similarity = common / 100
            return similarity > 0.85
    
    return False


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


def parse_txt_questions(txt_content, region, year):
    """从txt文件解析题目（简单解析）"""
    questions = []
    
    lines = txt_content.split('\n')
    
    current_question = None
    current_type = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检测题号 - 支持多种格式
        # 格式1: "1. " 或 "1、" 或 "1 "
        # 格式2: "1．（4分）" 或 "1.(4分)"
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
                'region': normalize_region(region),
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


def organize_dataset():
    """主函数：整理数据集"""
    print("=" * 60)
    print("开始整理高考真题数据集")
    print("=" * 60)
    
    # 创建输出目录
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 统计信息
    stats = defaultdict(lambda: {'years': set(), 'total_questions': 0})
    
    # 1. 收集所有JSON文件
    print("\n【步骤1】收集所有JSON文件...")
    all_json_files = list(BASE_DIR.rglob('*.json'))
    print(f"  找到 {len(all_json_files)} 个JSON文件")
    
    # 2. 按目标文件夹分组
    print("\n【步骤2】按目标文件夹分组...")
    folder_questions = defaultdict(list)
    
    for json_file in all_json_files:
        # 跳过省份索引和输出目录
        if json_file.name == '省份索引.json':
            continue
        if '整理后' in str(json_file):
            continue
        
        # 确定目标文件夹
        rel_path = json_file.relative_to(BASE_DIR)
        parts = rel_path.parts
        
        # 找到第一级文件夹名称
        first_folder = parts[0] if len(parts) > 0 else ''
        target_folder = FOLDER_MAPPING.get(first_folder, first_folder)
        
        if not target_folder:
            continue
        
        print(f"  处理: {json_file.name} -> {target_folder}")
        
        # 加载数据
        data = load_json_file(json_file)
        if data is None:
            continue
        
        # 提取题目
        questions = extract_questions_from_json(data, source_region=target_folder)
        folder_questions[target_folder].extend(questions)
    
    # 3. 处理raw文件夹
    print("\n【步骤3】处理raw文件夹...")
    for raw_dir in BASE_DIR.rglob('raw'):
        # 确定父文件夹的目标名称
        parent = raw_dir.parent
        parent_name = parent.name
        target_folder = FOLDER_MAPPING.get(parent_name, parent_name)
        
        print(f"  处理raw: {parent_name} -> {target_folder}")
        
        questions = process_raw_folder(raw_dir, target_folder)
        folder_questions[target_folder].extend(questions)
    
    # 4. 去重并保存
    print("\n【步骤4】去重并保存...")
    for folder_name, questions in folder_questions.items():
        print(f"\n  处理文件夹: {folder_name}")
        print(f"    原始题目数: {len(questions)}")
        
        # 去重
        merged = merge_questions(questions)
        print(f"    去重后题目数: {len(merged)}")
        
        # 按年份分组
        by_year = defaultdict(list)
        for q in merged:
            year = q.get('year', 0)
            if year:
                by_year[year].append(q)
                stats[folder_name]['years'].add(year)
        
        stats[folder_name]['total_questions'] = len(merged)
        
        # 创建文件夹
        folder_path = OUTPUT_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # 保存每年的题目
        for year, year_questions in sorted(by_year.items()):
            output_file = folder_path / f"{year}.json"
            
            output_data = {
                'year': year,
                'region': folder_name,
                'total_questions': len(year_questions),
                'questions': year_questions
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"    保存 {year}.json ({len(year_questions)}题)")
    
    # 5. 生成统计报告
    print("\n【步骤5】生成统计报告...")
    report = {}
    for folder_name, info in stats.items():
        report[folder_name] = {
            'years': sorted(list(info['years'])),
            'total_questions': info['total_questions']
        }
    
    with open(OUTPUT_DIR / '整理报告.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("整理完成！")
    print("=" * 60)
    print(f"\n输出目录: {OUTPUT_DIR}")
    print(f"\n统计信息:")
    for folder_name, info in sorted(report.items()):
        print(f"  {folder_name}: {info['total_questions']}题, 年份{info['years']}")
    
    total = sum(info['total_questions'] for info in report.values())
    print(f"\n总计: {total}道题目")
    
    # 6. 删除原始混乱的文件夹
    print("\n【步骤6】清理原始混乱文件夹...")
    folders_to_delete = [
        "新课标", "新课标I", "新课标 I", "新课标Ⅰ卷",
        "新课标", "新课标II", "新课标Ⅱ卷", "新课标卷",
        "新课标Ⅲ", "新课标Ⅲ卷",
        "全国卷数学真题", "全国甲卷卷", "全国汇总卷",
        "上海卷", "北京卷", "天津卷",
    ]
    
    for folder_name in folders_to_delete:
        folder_path = BASE_DIR / folder_name
        if folder_path.exists():
            try:
                shutil.rmtree(folder_path)
                print(f"  已删除: {folder_name}")
            except Exception as e:
                print(f"  删除失败 {folder_name}: {e}")
        else:
            print(f"  不存在: {folder_name}")
    
    print("\n清理完成！")


if __name__ == '__main__':
    organize_dataset()
