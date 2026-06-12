import sqlite3, os
db_path = os.path.join(os.path.dirname(__file__), 'backend', 'teaching_assistant.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, class_name, total_students FROM classes")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, 班级: {row[1]}, 学生数: {row[2]}")
conn.close()
