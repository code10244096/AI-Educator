"""
高考数学PDF真题识别工具
使用多模态大模型识别PDF中的数学题目并转换为JSON格式
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("请安装PyMuPDF: pip install PyMuPDF")


def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 300) -> List[str]:
    """将PDF文件转换为图片"""
    os.makedirs(output_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    image_paths = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        image_path = os.path.join(output_dir, f"page_{page_num+1:03d}.png")
        pix.save(image_path)
        image_paths.append(image_path)
        print(f"已转换第 {page_num+1}/{len(doc)} 页")
    
    doc.close()
    return image_paths


def recognize_question_with_llm(image_path: str, api_key: str, year: int, region: str) -> Optional[Dict]:
    """
    使用多模态大模型识别图片中的数学题目
    
    参数:
        image_path: 图片路径
        api_key: API密钥
        year: 年份
        region: 地区/试卷类型
    
    返回:
        识别后的题目字典，如果识别失败返回None
    """
    # 这里需要替换为实际的大模型API调用
    # 示例使用OpenAI兼容的多模态API
    
    """
    示例代码（需要根据实际使用的API调整）:
    
    from openai import OpenAI
    
    client = OpenAI(api_key=api_key, base_url="你的API地址")
    
    prompt = """
    请识别这张图片中的高考数学题目，并按照以下JSON格式返回结果：
    {
        "question_text": "题目内容（使用纯文本，数学公式用LaTeX格式）",
        "answer": "答案",
        "solution": "详细解析过程",
        "question_type": "选择题/填空题/解答题",
        "knowledge_points": ["知识点1", "知识点2"],
        "difficulty": 3,
        "score": 5.0
    }
    
    注意:
    1. 数学公式请使用LaTeX格式
    2. 选择题请包含所有选项
    3. 难度范围1-5
    4. 如果图片中没有题目，返回null
    """
    
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    response = client.chat.completions.create(
        model="gpt-4o",  # 或其他多模态模型
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(image_data).decode()}"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return result
    """
    
    print(f"识别图片: {image_path}")
    print("注意: 需要配置实际的大模型API调用")
    return None


def process_pdf_to_json(
    pdf_path: str, 
    output_dir: str, 
    year: int, 
    region: str,
    api_key: str,
    temp_image_dir: Optional[str] = None
) -> Dict:
    """
    处理PDF文件，识别所有题目并保存为JSON
    
    参数:
        pdf_path: PDF文件路径
        output_dir: 输出JSON的目录
        year: 年份
        region: 地区/试卷类型
        api_key: API密钥
        temp_image_dir: 临时图片目录（可选）
    
    返回:
        统计信息字典
    """
    # 创建临时目录
    if temp_image_dir is None:
        temp_image_dir = os.path.join(output_dir, "temp_images")
    
    # 1. PDF转图片
    print(f"正在转换PDF: {pdf_path}")
    image_paths = pdf_to_images(pdf_path, temp_image_dir)
    print(f"共转换 {len(image_paths)} 页图片")
    
    # 2. 识别每页的题目
    all_questions = []
    
    for image_path in image_paths:
        question = recognize_question_with_llm(image_path, api_key, year, region)
        if question:
            all_questions.append(question)
    
    # 3. 保存为JSON
    output_data = {
        "year": year,
        "region": region,
        "total_questions": len(all_questions),
        "questions": all_questions
    }
    
    output_file = os.path.join(output_dir, f"{year}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"已保存 {len(all_questions)} 道题目到: {output_file}")
    
    return {
        "year": year,
        "region": region,
        "total_questions": len(all_questions),
        "output_file": output_file
    }


def batch_process_pdfs(
    pdf_dir: str,
    output_dir: str,
    api_key: str,
    year_region_map: Optional[Dict[str, tuple]] = None
) -> List[Dict]:
    """
    批量处理PDF文件
    
    参数:
        pdf_dir: PDF文件目录
        output_dir: 输出JSON的目录
        api_key: API密钥
        year_region_map: 文件名到(年份, 地区)的映射字典
                        如果为None，则尝试从文件名解析
    
    返回:
        所有处理结果列表
    """
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    pdf_files = list(Path(pdf_dir).glob("*.pdf"))
    
    for pdf_file in pdf_files:
        filename = pdf_file.stem
        
        # 尝试从文件名解析年份和地区
        if year_region_map and filename in year_region_map:
            year, region = year_region_map[filename]
        else:
            # 尝试从文件名解析，例如 "2009年全国卷I理科数学.pdf"
            # 这里需要根据实际文件名格式调整
            year = None
            region = "未知"
            
            # 简单解析逻辑
            if filename.startswith("20"):
                year = int(filename[:4])
                if "全国卷" in filename:
                    if "I" in filename or "1" in filename:
                        region = "全国卷I"
                    elif "II" in filename or "2" in filename:
                        region = "全国卷II"
        
        if year is None:
            print(f"无法解析文件名: {filename}，跳过")
            continue
        
        print(f"\n处理: {filename} ({year} {region})")
        
        result = process_pdf_to_json(
            str(pdf_file),
            output_dir,
            year,
            region,
            api_key
        )
        results.append(result)
    
    return results


if __name__ == "__main__":
    # 配置参数
    PDF_DIR = r"e:\AI-Educator\temp_gaokao_data\PDF真题汇编"
    OUTPUT_DIR = r"e:\AI-Educator\dataset\高考\数学\高考数学真题"
    API_KEY = "你的API密钥"  # 替换为实际的API密钥
    
    # 检查PDF目录是否存在
    if not os.path.exists(PDF_DIR):
        print(f"PDF目录不存在: {PDF_DIR}")
        print("请先将PDF文件放入该目录")
        exit(1)
    
    # 批量处理
    print("=" * 60)
    print("高考数学PDF真题识别工具")
    print("=" * 60)
    
    # 示例：手动指定文件名映射
    year_region_map = {
        # "2009年全国卷I理科数学": (2009, "全国卷I"),
        # "2009年全国卷I文科数学": (2009, "全国卷I"),
    }
    
    results = batch_process_pdfs(
        PDF_DIR,
        OUTPUT_DIR,
        API_KEY,
        year_region_map
    )
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("处理完成汇总")
    print("=" * 60)
    
    total_questions = 0
    for result in results:
        print(f"  {result['year']} {result['region']}: {result['total_questions']}题")
        total_questions += result['total_questions']
    
    print(f"\n总计: {total_questions}题")
