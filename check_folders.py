import json
import os
from pathlib import Path

base = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

folders_to_check = [
    "新课标", "新课标", "新课标ⅱ", "新课标ⅲ",
    "新课标I卷", "新课标II卷", "全国卷Ⅲ"
]

print("各文件夹包含的年份:")
print("=" * 60)

for folder in folders_to_check:
    folder_path = os.path.join(base, folder)
    if os.path.isdir(folder_path):
        years = []
        total_q = 0
        for fp in os.listdir(folder_path):
            if fp.endswith(".json"):
                try:
                    data = json.load(open(os.path.join(folder_path, fp), 'r', encoding='utf-8'))
                    years.append(data.get('year', '?'))
                    total_q += len(data.get('questions', []))
                except:
                    pass
        years_str = ", ".join(map(str, sorted(years)))
        print(f"{folder:15s}: 年份[{years_str}] 共{total_q}题")
