"""题库检索/浏览使用的学科与学段。

教师档案可选学科见 routers.auth.STAGE_SUBJECTS（小学含科学，与题库对齐）。
大学卷尚未入库，RAG 对大学学段直接跳过。
"""

BANK_SUBJECTS = ("语文", "数学", "英语", "科学")
BANK_STAGES = ("小学", "初中", "高中")
