import json
import os

base = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"

print("检查'新课标'文件夹中各年份的region标记:")
print("=" * 60)

folder = os.path.join(base, "新课标")
for fp in sorted(os.listdir(folder)):
    if fp.endswith(".json"):
        data = json.load(open(os.path.join(folder, fp), 'r', encoding='utf-8'))
        print(f"{fp}: region={data.get('region')}, questions={data.get('total_questions')}")
