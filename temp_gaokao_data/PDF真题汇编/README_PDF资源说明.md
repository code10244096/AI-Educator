# 高考数学真题数据集 - PDF资源整理说明

## 当前数据覆盖情况

### 已整理完成 (JSON格式)
- **2010-2024年**: 约5582道题目
  - 全国卷/新课标: 2010-2024年
  - 新高考I卷/II卷: 2020-2024年
  - 全国甲卷/乙卷: 2021-2024年
  - 北京/上海/天津: 2024年
  - HighMATH 2024: 4399题 (8个知识点分类)

### 待处理 (PDF格式)
- **2000-2009年**: 全国卷I/II、各省份自主命题
- **省份独立命题**: 江苏、浙江、山东、湖北、湖南等

## PDF资源来源

### 1. 高考数学真题汇编 (1977-2021)
- 包含599套试卷
- 格式: PDF
- 来源: B站文档分享
- 百度网盘链接: https://pan.baidu.com/s/1ku1c5-fJii31VXTmgO3KIA (提取码: 2345)

### 2. 2009-2001全国卷真题
- 格式: PDF (82页)
- 包含全国I卷文理科数学

### 3. 各省份真题网站
- gaokao.com: 提供2009年各省份真题下载链接
- 各省教育考试院官网

## 后续处理方案

### 方案一: 大模型辅助识别 (推荐)
对于PDF/图片格式的真题，可以使用大模型进行识别和结构化：

1. **PDF转图片**: 使用PyMuPDF或pdf2image将PDF转为图片
2. **大模型识别**: 调用多模态大模型识别题目内容
3. **结构化输出**: 将识别结果转换为JSON格式

示例代码框架:
```python
# 伪代码示例
import fitz  # PyMuPDF

def pdf_to_images(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        pix.save(f"{output_dir}/page_{page_num+1}.png")

def recognize_with_llm(image_path):
    # 调用多模态大模型识别图片内容
    # 返回结构化的题目JSON
    pass
```

### 方案二: 手动整理
- 适合少量真题
- 准确性高但效率低

## 数据集格式规范

每个JSON文件包含以下字段:
```json
{
  "year": 2024,
  "region": "全国卷",
  "questions": [
    {
      "question_text": "题目内容",
      "answer": "答案",
      "solution": "解析",
      "question_type": "选择题/填空题/解答题",
      "knowledge_points": ["知识点1", "知识点2"],
      "difficulty": 3,
      "score": 5.0
    }
  ]
}
```

## 目录结构
```
dataset/高考/数学/高考数学真题/
├── 全国卷/
│   └── 2024_HighMATH.json
├── 新课标/
│   ├── 2010.json
│   └── ...
├── 新高考I卷/
├── 新高考II卷/
├── 全国甲卷/
├── 全国乙卷/
├── 北京/
├── 上海/
├── 天津/
└── 统计报告_GAOKAO-Bench.json

temp_gaokao_data/
├── HighMATH_2024/  (原始JSONL文件)
└── PDF真题汇编/    (待处理的PDF资源)
```

## 更新日期
2026-05-23
