"""题库检索/浏览使用的学科与学段。

教师档案可选学科见 routers.auth.STAGE_SUBJECTS（小学含科学，与题库对齐）。
大学卷尚未入库，RAG 对大学学段直接跳过。
"""

BANK_SUBJECTS = ("语文", "数学", "英语", "科学")
BANK_STAGES = ("小学", "初中", "高中")

# 题库搜索主题同义词。命中 key 时，列表内任一词匹配即可。
# SQLite LIKE 对 ASCII 默认不区分大小写（除非 PRAGMA case_sensitive_like=ON）。
SEARCH_SYNONYMS = {
    "三角函数": ["三角函数", "三角", "正弦", "余弦", "正切", "sin", "cos", "tan"],
    "导数": ["导数", "微分", "f'(x)", "切线"],
    "二次函数": ["二次函数", "抛物线"],
    "立体几何": ["立体几何", "三视图", "空间向量"],
    "数列": ["数列", "等差", "等比"],
    "概率": ["概率", "排列组合", "古典概型"],
}

# 中文年级 / 别称 → 数字年级（1–12）
_CN_GRADE = {
    "一年级": 1, "二年级": 2, "三年级": 3, "四年级": 4, "五年级": 5, "六年级": 6,
    "七年级": 7, "八年级": 8, "九年级": 9,
    "十年级": 10, "十一年级": 11, "十二年级": 12,
    "初一": 7, "初二": 8, "初三": 9,
    "高一": 10, "高二": 11, "高三": 12,
}


def parse_grade_number(grade_str):
    """把「三年级 / 初一 / 高一 / 12」解析为 1–12；无法解析返回 None。"""
    if grade_str is None:
        return None
    text = str(grade_str).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if text in _CN_GRADE:
        return _CN_GRADE[text]
    for name in sorted(_CN_GRADE, key=len, reverse=True):
        if name in text:
            return _CN_GRADE[name]
    return None


def grade_to_education_level(grade_num):
    """数字年级 → 学段：1–6 小学 / 7–9 初中 / 10–12 高中。"""
    if grade_num is None:
        return None
    try:
        n = int(grade_num)
    except (TypeError, ValueError):
        return None
    if 1 <= n <= 6:
        return "小学"
    if 7 <= n <= 9:
        return "初中"
    if 10 <= n <= 12:
        return "高中"
    return None
