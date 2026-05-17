"""
创建北京卷、上海卷、天津卷的高考数学题目数据
由于这些自主命题省份没有现成的结构化JSON数据集，
这里创建示例数据文件，后续可以手动补充真实题目
"""

import json
import os
from typing import Dict, List


def get_base_dir() -> str:
    """获取基础目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_target_dir() -> str:
    """获取目标数据目录"""
    return os.path.join(
        get_base_dir(),
        "dataset",
        "高考",
        "数学"
    )


def create_beijing_sample_data() -> Dict:
    """创建北京卷示例数据"""
    return {
        "year": 2024,
        "province": "北京卷",
        "total_questions": 10,
        "crawl_time": "2024-06-08T00:00:00",
        "questions": [
            {
                "question_text": "1. 已知集合 $A=\\{x|-3<x<1\\}$，$B=\\{x|-1\\leq x<4\\}$，则 $A\\cup B=$（  ）\nA. $\\{x|-3<x<4\\}$\nB. $\\{x|-1\\leq x<1\\}$\nC. $\\{x|-3<x<1\\}$\nD. $\\{x|-1\\leq x<4\\}$",
                "answer": "A",
                "solution": "【详解】由集合的并集定义，$A\\cup B=\\{x|-3<x<1\\}\\cup\\{x|-1\\leq x<4\\}=\\{x|-3<x<4\\}$\n故选：A",
                "question_type": "选择题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "北京卷",
                "knowledge_points": ["集合"],
                "difficulty": 2,
                "score": 4.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查集合的并集运算，建议结合数轴理解集合的运算。",
                "common_mistakes": "1. 混淆并集与交集的概念；2. 忽略端点的开闭情况"
            },
            {
                "question_text": "2. 在复平面内，复数 $z$ 对应的点的坐标是 $(1,2)$，则 $i\\cdot z=$（  ）\nA. $1+2i$\nB. $-2+i$\nC. $1-2i$\nD. $-2-i$",
                "answer": "B",
                "solution": "【详解】由题意得 $z=1+2i$，\n则 $i\\cdot z=i(1+2i)=i+2i^2=i-2=-2+i$\n故选：B",
                "question_type": "选择题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "北京卷",
                "knowledge_points": ["复数"],
                "difficulty": 2,
                "score": 4.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查复数的乘法运算，重点掌握 $i^2=-1$ 的应用。",
                "common_mistakes": "1. 复数乘法运算错误；2. $i^2=-1$ 的符号处理错误"
            },
            {
                "question_text": "3. 圆 $x^2+y^2-2x+6y=0$ 的圆心到直线 $x-y+2=0$ 的距离为（  ）\nA. $\\sqrt{2}$\nB. $2$\nC. $3$\nD. $3\\sqrt{2}$",
                "answer": "A",
                "solution": "【详解】圆的方程化为标准形式：$(x-1)^2+(y+3)^2=10$，\n圆心为 $(1,-3)$，半径为 $\\sqrt{10}$\n圆心到直线的距离 $d=\\frac{|1-(-3)+2|}{\\sqrt{1^2+(-1)^2}}=\\frac{6}{\\sqrt{2}}=3\\sqrt{2}$\n故选：D",
                "question_type": "选择题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "北京卷",
                "knowledge_points": ["解析几何", "圆"],
                "difficulty": 3,
                "score": 4.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查圆的标准方程和点到直线的距离公式。",
                "common_mistakes": "1. 圆的标准方程配方错误；2. 点到直线距离公式记错"
            }
        ]
    }


def create_shanghai_sample_data() -> Dict:
    """创建上海卷示例数据"""
    return {
        "year": 2024,
        "province": "上海卷",
        "total_questions": 12,
        "crawl_time": "2024-06-08T00:00:00",
        "questions": [
            {
                "question_text": "1. 已知全集 $U=\\{x|2\\leq x\\leq 5, x\\in R\\}$，集合 $A=\\{x|2\\leq x<4, x\\in R\\}$，则 $\\bar{A}=$______",
                "answer": "[4,5]",
                "solution": "【解析】由题意，$\\bar{A}=\\{x|4\\leq x\\leq 5\\}=[4,5]$",
                "question_type": "填空题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "上海卷",
                "knowledge_points": ["集合"],
                "difficulty": 2,
                "score": 4.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查集合的补集运算，注意全集的范围限制。",
                "common_mistakes": "1. 忽略全集的范围；2. 区间端点开闭判断错误"
            },
            {
                "question_text": "2. 不等式 $\\frac{x-1}{x-3}<0$ 的解集为______",
                "answer": "(1,3)",
                "solution": "【解析】由题意，$(x-3)(x-1)<0 \\Rightarrow x\\in(1,3)$",
                "question_type": "填空题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "上海卷",
                "knowledge_points": ["不等式"],
                "difficulty": 2,
                "score": 4.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查分式不等式的解法，注意分母不能为零。",
                "common_mistakes": "1. 忽略分母不为零的条件；2. 不等号方向判断错误"
            },
            {
                "question_text": "3. 等差数列 $\\{a_n\\}$，$a_1=-3$，公差 $d=2$，则 $S_6=$______",
                "answer": "12",
                "solution": "【解析】由题意，$a_6=a_1+5d=-3+10=7 \\Rightarrow S_6=\\frac{6(a_1+a_6)}{2}=\\frac{6(-3+7)}{2}=12$",
                "question_type": "填空题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "上海卷",
                "knowledge_points": ["数列"],
                "difficulty": 2,
                "score": 4.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查等差数列的通项公式和前n项和公式。",
                "common_mistakes": "1. 等差数列求和公式记错；2. 计算错误"
            }
        ]
    }


def create_tianjin_sample_data() -> Dict:
    """创建天津卷示例数据"""
    return {
        "year": 2024,
        "province": "天津卷",
        "total_questions": 10,
        "crawl_time": "2024-06-08T00:00:00",
        "questions": [
            {
                "question_text": "1. 已知集合 $A=\\{1,2,3\\}$，$B=\\{2,3,4\\}$，则 $A\\cap B=$（  ）\nA. $\\{1,2,3,4\\}$\nB. $\\{2,3\\}$\nC. $\\{1,4\\}$\nD. $\\emptyset$",
                "answer": "B",
                "solution": "【详解】由集合的交集定义，$A\\cap B=\\{1,2,3\\}\\cap\\{2,3,4\\}=\\{2,3\\}$\n故选：B",
                "question_type": "选择题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "天津卷",
                "knowledge_points": ["集合"],
                "difficulty": 1,
                "score": 5.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查集合的交集运算，是基础题型。",
                "common_mistakes": "1. 混淆交集与并集的概念"
            },
            {
                "question_text": "2. 已知 $i$ 是虚数单位，复数 $z=\\frac{2i}{1-i}$，则 $|z|=$（  ）\nA. $1$\nB. $\\sqrt{2}$\nC. $2$\nD. $2\\sqrt{2}$",
                "answer": "B",
                "solution": "【详解】$z=\\frac{2i}{1-i}=\\frac{2i(1+i)}{(1-i)(1+i)}=\\frac{2i+2i^2}{1-i^2}=\\frac{2i-2}{2}=-1+i$\n$|z|=\\sqrt{(-1)^2+1^2}=\\sqrt{2}$\n故选：B",
                "question_type": "选择题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "天津卷",
                "knowledge_points": ["复数"],
                "difficulty": 3,
                "score": 5.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查复数的除法运算和模的计算。",
                "common_mistakes": "1. 复数除法运算错误；2. 模的计算公式记错"
            },
            {
                "question_text": "3. 在 $(x+\\frac{1}{x})^6$ 的展开式中，$x^2$ 的系数为（  ）\nA. 15\nB. 20\nC. 30\nD. 45",
                "answer": "A",
                "solution": "【详解】由二项式定理，$T_{r+1}=C_6^r x^{6-r}(\\frac{1}{x})^r=C_6^r x^{6-2r}$\n令 $6-2r=2$，得 $r=2$\n所以 $x^2$ 的系数为 $C_6^2=15$\n故选：A",
                "question_type": "选择题",
                "subject": "数学",
                "education_level": "高中",
                "exam_type": "高考",
                "year": 2024,
                "region": "天津卷",
                "knowledge_points": ["二项式定理"],
                "difficulty": 3,
                "score": 5.0,
                "source_url": "待补充",
                "teaching_tips": "本题主要考查二项式定理的应用，重点掌握通项公式。",
                "common_mistakes": "1. 通项公式记错；2. 指数计算错误"
            }
        ]
    }


def create_sample_data():
    """创建示例数据文件"""
    target_dir = get_target_dir()
    
    print("="*60)
    print("创建北京卷、上海卷、天津卷示例数据")
    print("="*60)
    
    # 创建北京卷数据
    beijing_dir = os.path.join(target_dir, "北京卷")
    os.makedirs(beijing_dir, exist_ok=True)
    
    beijing_data = create_beijing_sample_data()
    with open(os.path.join(beijing_dir, "2024.json"), 'w', encoding='utf-8') as f:
        json.dump(beijing_data, f, ensure_ascii=False, indent=2)
    print(f"✓ 北京卷 2024年: {beijing_data['total_questions']} 道题")
    
    # 创建上海卷数据
    shanghai_dir = os.path.join(target_dir, "上海卷")
    os.makedirs(shanghai_dir, exist_ok=True)
    
    shanghai_data = create_shanghai_sample_data()
    with open(os.path.join(shanghai_dir, "2024.json"), 'w', encoding='utf-8') as f:
        json.dump(shanghai_data, f, ensure_ascii=False, indent=2)
    print(f"✓ 上海卷 2024年: {shanghai_data['total_questions']} 道题")
    
    # 创建天津卷数据
    tianjin_dir = os.path.join(target_dir, "天津卷")
    os.makedirs(tianjin_dir, exist_ok=True)
    
    tianjin_data = create_tianjin_sample_data()
    with open(os.path.join(tianjin_dir, "2024.json"), 'w', encoding='utf-8') as f:
        json.dump(tianjin_data, f, ensure_ascii=False, indent=2)
    print(f"✓ 天津卷 2024年: {tianjin_data['total_questions']} 道题")
    
    print("\n" + "="*60)
    print("创建完成！")
    print("="*60)
    print("\n注意：这些是示例数据，请根据实际情况补充真实题目。")
    print("数据文件位置：")
    print(f"  {beijing_dir}")
    print(f"  {shanghai_dir}")
    print(f"  {tianjin_dir}")


if __name__ == "__main__":
    create_sample_data()
