import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'backend', 'teaching_assistant.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查班级1的所有学生
cursor.execute("SELECT id, name, order_index FROM class_members WHERE class_id = 1 ORDER BY order_index")
members = cursor.fetchall()
print(f"班级1的学生列表（共{len(members)}人）：")
for m in members:
    print(f"  ID: {m[0]}, 姓名: {m[1]}, 序号: {m[2]}")

conn.close()