import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'backend', 'teaching_assistant.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查作业表中的total_students
cursor.execute("SELECT id, title, total_students FROM homework_assignments WHERE class_id = 1")
homeworks = cursor.fetchall()
print("作业列表:")
for hw in homeworks:
    print(f"  ID: {hw[0]}, 标题: {hw[1]}, total_students: {hw[2]}")

conn.close()