import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'backend', 'teaching_assistant.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查班级1的学生数量
cursor.execute("SELECT COUNT(*) FROM class_members WHERE class_id = 1")
count = cursor.fetchone()[0]
print(f"班级1的学生数量: {count}")

# 检查班级表中的total_students
cursor.execute("SELECT total_students FROM classes WHERE id = 1")
total = cursor.fetchone()[0]
print(f"班级1的total_students: {total}")

# 获取班级1的所有学生名字
cursor.execute("SELECT name FROM class_members WHERE class_id = 1 ORDER BY order_index")
names = [row[0] for row in cursor.fetchall()]
print(f"班级1的学生名字: {names}")

conn.close()