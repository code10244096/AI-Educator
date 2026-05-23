import json
import os

base = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

# 检查2013年新课标和新课标ⅰ的数据
print("检查2013年数据重复情况:")
print("=" * 60)

# 新课标 2013
file1 = os.path.join(base, "新课标", "2013.json")
data1 = json.load(open(file1, 'r', encoding='utf-8'))
print(f"\n新课标/2013.json:")
print(f"  region: {data1.get('region')}")
print(f"  total_questions: {data1.get('total_questions')}")
print(f"  第1题: {data1['questions'][0]['question_text'][:80]}...")

# 新课标ⅰ 2013
file2 = os.path.join(base, "新课标ⅰ", "2013.json")
data2 = json.load(open(file2, 'r', encoding='utf-8'))
print(f"\n新课标ⅰ/2013.json:")
print(f"  region: {data2.get('region')}")
print(f"  total_questions: {data2.get('total_questions')}")
print(f"  第1题: {data2['questions'][0]['question_text'][:80]}...")

# 检查是否有相同的题目
print("\n\n检查题目是否重复:")
q1_texts = set()
for q in data1['questions']:
    # 简化题目文本
    text = q['question_text'].split('.', 1)[-1].strip()[:50]
    q1_texts.add(text)

q2_texts = set()
for q in data2['questions']:
    text = q['question_text'].split('.', 1)[-1].strip()[:50]
    q2_texts.add(text)

common = q1_texts & q2_texts
print(f"  新课标题目数: {len(q1_texts)}")
print(f"  新课标ⅰ题目数: {len(q2_texts)}")
print(f"  重复题目数: {len(common)}")

if common:
    print(f"\n  重复题目示例:")
    for i, t in enumerate(list(common)[:3]):
        print(f"    {i+1}. {t}...")
