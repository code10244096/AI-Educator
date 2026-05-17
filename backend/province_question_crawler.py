"""
各省份高考数学真题爬虫
爬取北京卷、上海卷、天津卷等自主命题省份的高考数学题目
数据保存到 dataset/高考/数学/省份卷数学真题/ 目录下
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


class ProvinceQuestionCrawler:
    """省份高考题目爬虫"""
    
    # 目标网站配置
    BASE_URL = "https://www.gk100.com"
    
    # 省份配置：省份名称 -> 目录名
    PROVINCES = {
        "北京卷": "北京",
        "上海卷": "上海",
        "天津卷": "天津",
        "江苏卷": "江苏",
        "浙江卷": "浙江",
        "山东卷": "山东",
        "湖北卷": "湖北",
        "湖南卷": "湖南",
        "广东卷": "广东",
        "福建卷": "福建",
        "重庆卷": "重庆",
        "河北卷": "河北",
        "辽宁卷": "辽宁",
    }
    
    # 年份范围
    YEARS = range(2015, 2026)
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "dataset",
                "高考",
                "数学"
            )
        self.output_dir = output_dir
        self.client = None
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            follow_redirects=True
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def get_province_dir(self, province: str) -> str:
        """获取省份输出目录"""
        province_name = self.PROVINCES.get(province, province.replace("卷", ""))
        return os.path.join(self.output_dir, f"{province_name}卷数学真题")
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """获取网页内容"""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    ✗ 获取页面失败: {url} - {str(e)}")
            return None
    
    def parse_questions_from_html(self, html: str, year: int, province: str) -> List[Dict]:
        """从HTML中解析题目"""
        questions = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 尝试提取题目内容
            content_div = soup.find('div', class_='content') or soup.find('div', id='content') or soup.find('article')
            
            if not content_div:
                content_div = soup.find('body')
            
            if not content_div:
                return questions
            
            content_text = content_div.get_text()
            
            # 使用正则表达式提取题目
            # 匹配选择题模式：题号. 题目内容 A. 选项 B. 选项 ...
            question_patterns = [
                r'(\d+)[\.、]\s*(.+?)(?=\d+[\.、]|\Z)',
            ]
            
            for pattern in question_patterns:
                matches = re.finditer(pattern, content_text, re.DOTALL)
                
                for match in matches:
                    question_num = match.group(1)
                    question_content = match.group(2).strip()
                    
                    if len(question_content) < 10:
                        continue
                    
                    # 判断题型
                    question_type = self.determine_question_type(question_content)
                    
                    # 提取答案
                    answer = self.extract_answer(question_content)
                    
                    question = {
                        "question_text": f"{question_num}. {question_content}",
                        "answer": answer,
                        "solution": "",
                        "question_type": question_type,
                        "subject": "数学",
                        "education_level": "高中",
                        "exam_type": "高考",
                        "year": year,
                        "region": province,
                        "knowledge_points": self.extract_knowledge_points(question_content),
                        "difficulty": 3,
                        "score": 5.0 if question_type == "选择题" else (5.0 if question_type == "填空题" else 12.0),
                        "source_url": "https://www.gk100.com",
                        "teaching_tips": self.generate_teaching_tips(question_content),
                        "common_mistakes": "请参考教材和历年真题"
                    }
                    
                    questions.append(question)
            
        except Exception as e:
            print(f"    ✗ 解析题目失败: {str(e)}")
        
        return questions
    
    def determine_question_type(self, content: str) -> str:
        """判断题型"""
        content_lower = content.lower()
        
        # 选择题特征
        if re.search(r'[A-D][\.、]', content) or re.search(r'选项|选择', content):
            return "选择题"
        
        # 填空题特征
        if '____' in content or '______' in content or '填空' in content:
            return "填空题"
        
        # 解答题特征
        if re.search(r'解答|证明|计算|求.*值|求.*范围', content):
            return "解答题"
        
        return "选择题"  # 默认
    
    def extract_answer(self, content: str) -> str:
        """提取答案"""
        # 尝试匹配答案
        answer_match = re.search(r'【答案】\s*([A-D]+)', content)
        if answer_match:
            return answer_match.group(1)
        
        answer_match = re.search(r'答案[：:]\s*([A-D]+)', content)
        if answer_match:
            return answer_match.group(1)
        
        return ""
    
    def extract_knowledge_points(self, content: str) -> List[str]:
        """提取知识点"""
        knowledge_points = []
        
        # 常见数学知识点关键词
        keywords = {
            "集合": r'集合|∪|∩|⊆|∈',
            "函数": r'函数|f\(x\)|单调|奇偶|周期',
            "三角函数": r'sin|cos|tan|三角',
            "向量": r'向量|→|⋅',
            "数列": r'数列|等差|等比|a_n|S_n',
            "不等式": r'不等式|≥|≤|>|<',
            "立体几何": r'棱柱|棱锥|球|体积|表面积',
            "解析几何": r'椭圆|双曲线|抛物线|直线与圆',
            "概率统计": r'概率|统计|分布|期望',
            "导数": r'导数|切线|极值|最值',
            "复数": r'复数|虚数|i',
            "排列组合": r'排列|组合|C|P',
            "二项式定理": r'二项式|展开',
            "算法": r'算法|程序框图',
        }
        
        for point, pattern in keywords.items():
            if re.search(pattern, content, re.IGNORECASE):
                knowledge_points.append(point)
        
        return knowledge_points if knowledge_points else ["综合"]
    
    def generate_teaching_tips(self, content: str) -> str:
        """生成教学建议"""
        knowledge_points = self.extract_knowledge_points(content)
        
        if not knowledge_points:
            return "本题为高考真题，建议结合教材系统复习相关知识点。"
        
        points_str = "、".join(knowledge_points)
        return f"本题主要考查{points_str}知识点，建议结合教材和历年真题进行系统训练。"
    
    async def crawl_province_year(self, province: str, year: int) -> List[Dict]:
        """爬取指定省份指定年份的题目"""
        print(f"  爬取 {province} {year}年...")
        
        # 构建搜索URL
        search_url = f"{self.BASE_URL}/search/?q={province}+{year}+数学+高考真题"
        
        html = await self.fetch_page(search_url)
        if not html:
            return []
        
        # 解析搜索结果
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        
        target_urls = []
        for link in links:
            href = link.get('href', '')
            text = link.get_text()
            
            # 匹配包含省份、年份、数学的链接
            if all(keyword in text for keyword in [province.replace("卷", ""), str(year), "数学"]):
                if href.startswith('/'):
                    href = self.BASE_URL + href
                target_urls.append(href)
        
        if not target_urls:
            print(f"    ⚠ 未找到 {province} {year}年的题目页面")
            return []
        
        # 爬取目标页面
        all_questions = []
        for url in target_urls[:2]:  # 限制最多爬取2个页面
            html = await self.fetch_page(url)
            if html:
                questions = self.parse_questions_from_html(html, year, province)
                all_questions.extend(questions)
        
        print(f"    ✓ 获取 {len(all_questions)} 道题目")
        return all_questions
    
    async def save_questions(self, province: str, year: int, questions: List[Dict]):
        """保存题目到文件"""
        if not questions:
            return
        
        province_dir = self.get_province_dir(province)
        os.makedirs(province_dir, exist_ok=True)
        
        output_file = os.path.join(province_dir, f"{year}.json")
        
        data = {
            "year": year,
            "province": province,
            "total_questions": len(questions),
            "crawl_time": datetime.now().isoformat(),
            "questions": questions
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"    💾 保存到 {output_file}")
    
    async def crawl_all(self):
        """爬取所有省份所有年份"""
        print("="*60)
        print("开始爬取各省份高考数学真题")
        print("="*60)
        
        tasks = []
        
        for province in self.PROVINCES.keys():
            for year in self.YEARS:
                task = self.crawl_province_year(province, year)
                tasks.append((province, year, task))
        
        # 并发爬取
        success_count = 0
        total_questions = 0
        
        for province, year, task in tasks:
            try:
                questions = await task
                
                if questions:
                    await self.save_questions(province, year, questions)
                    success_count += 1
                    total_questions += len(questions)
                
            except Exception as e:
                print(f"  ✗ {province} {year}年爬取失败: {str(e)}")
        
        print("\n" + "="*60)
        print(f"爬取完成!")
        print(f"成功: {success_count} 个省份/年份")
        print(f"总题目数: {total_questions}")
        print("="*60)


async def main():
    """主函数"""
    async with ProvinceQuestionCrawler() as crawler:
        await crawler.crawl_all()


if __name__ == "__main__":
    asyncio.run(main())
