"""
整理PDF/图片资源到对应省份目录
"""

import os
import shutil
from pathlib import Path

BASE_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"
PDF_SOURCE = r"e:\AI-Educator\temp_gaokao_data"

def organize_pdf_resources():
    """整理PDF和图片资源到对应目录"""
    
    print("=" * 60)
    print("整理PDF/图片资源到对应省份目录")
    print("=" * 60)
    
    # 创建PDF资源总目录
    pdf_base = os.path.join(BASE_DIR, "PDF资源")
    os.makedirs(pdf_base, exist_ok=True)
    
    # 1. 整理2024年新高考数学PDF
    print("\n1. 整理2024年新高考I卷PDF资源")
    gaokao_2024_dir = os.path.join(pdf_base, "2024年新高考I卷")
    os.makedirs(gaokao_2024_dir, exist_ok=True)
    
    source_2024 = os.path.join(PDF_SOURCE, "2024_Gaokao_Math")
    if os.path.exists(source_2024):
        for f in os.listdir(source_2024):
            if f.endswith(('.pdf', '.jpg', '.png', '.tex')):
                src = os.path.join(source_2024, f)
                dst = os.path.join(gaokao_2024_dir, f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    print(f"  复制: {f}")
    
    # 2. 整理已有的PDF真题汇编
    print("\n2. 整理PDF真题汇编资源")
    pdf_assembly = os.path.join(PDF_SOURCE, "PDF真题汇编")
    if os.path.exists(pdf_assembly):
        # 复制到PDF资源目录
        for f in os.listdir(pdf_assembly):
            src = os.path.join(pdf_assembly, f)
            dst = os.path.join(pdf_base, f)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
                print(f"  复制: {f}")
    
    # 3. 按年份整理PDF资源
    print("\n3. 按年份组织PDF资源索引")
    
    # 创建索引文件
    index_file = os.path.join(pdf_base, "PDF资源索引.json")
    index_data = {
        "description": "高考数学真题PDF资源索引",
        "resources": [
            {
                "year": 2024,
                "region": "新高考I卷",
                "files": ["main.pdf", "main.tex", "20240608-1.pdf", "20240608-1.jpg"],
                "source": "https://github.com/ajsadhotmail/2024-China-Gaokao-Math",
                "note": "适用于: 广东、福建、湖南、湖北、浙江、江苏、山东、河北"
            },
            {
                "year": "2000-2009",
                "region": "全国卷I/II",
                "files": ["2009-2001高考全国卷数学真题及答案精编整理.pdf"],
                "source": "网络资源整理",
                "note": "包含2001-2009年全国卷I/II文理科数学真题"
            },
            {
                "year": "1978-2010",
                "region": "全国卷",
                "files": ["中国高考真题全编-理科数学(1978-2010年).pdf"],
                "source": "网络资源整理",
                "note": "包含1978-2010年理科数学真题汇编"
            }
        ],
        "processing_notes": [
            "PDF文件需要使用OCR或大模型进行解析",
            "可使用recognize_gaokao_pdf.py脚本进行批量识别",
            "解析后的数据将转换为JSON格式存入对应年份目录"
        ]
    }
    
    import json
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"  创建索引文件: PDF资源索引.json")
    
    # 4. 列出最终资源
    print("\n" + "=" * 60)
    print("PDF资源目录结构:")
    print("=" * 60)
    for root, dirs, files in os.walk(pdf_base):
        level = root.replace(pdf_base, '').count(os.sep)
        indent = '  ' * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = '  ' * (level + 1)
        for file in files:
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            size_str = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
            print(f"{subindent}{file} ({size_str})")

if __name__ == "__main__":
    organize_pdf_resources()
