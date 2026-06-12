import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'backend', 'teaching_assistant.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 更新班级1所有作业的total_students为2
cursor.execute("UPDATE homework_assignments SET total_students = 2 WHERE class_id = 1")
updated = cursor.rowcount
print(f"更新了 {updated} 个作业的total_students为2")

conn.commit()
conn.close()
print("完成！")