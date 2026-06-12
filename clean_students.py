import sqlite3
import os

# 数据库路径
db_path = os.path.join(os.path.dirname(__file__), 'backend', 'teaching_assistant.db')

print(f"连接数据库: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取高三1班的ID
cursor.execute("SELECT id FROM classes WHERE class_name = '高三1班'")
class1_id = cursor.fetchone()[0]
print(f"高三1班ID: {class1_id}")

# 获取高三1班当前的学生数量
cursor.execute("SELECT COUNT(*) FROM class_members WHERE class_id = ?", (class1_id,))
current_count = cursor.fetchone()[0]
print(f"当前学生数量: {current_count}")

# 获取前2名学生的ID（保留）
cursor.execute("SELECT id FROM class_members WHERE class_id = ? ORDER BY order_index LIMIT 2", (class1_id,))
keep_ids = [row[0] for row in cursor.fetchall()]
print(f"保留的学生ID: {keep_ids}")

# 删除其他学生
if keep_ids:
    placeholders = ','.join('?' * len(keep_ids))
    cursor.execute(f"DELETE FROM class_members WHERE class_id = ? AND id NOT IN ({placeholders})", (class1_id,) + tuple(keep_ids))
    deleted = cursor.rowcount
    print(f"删除了 {deleted} 名学生")
    
    # 更新班级的总学生数
    cursor.execute("UPDATE classes SET total_students = 2 WHERE id = ?", (class1_id,))
    print("更新班级总学生数为 2")

conn.commit()
conn.close()
print("清理完成！")