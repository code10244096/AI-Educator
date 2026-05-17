"""
各省份高考数学真题爬虫 v3
从多个数据源尝试获取题目内容
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


class ProvinceGaokaoCrawlerV3:
    """省份高考题目爬虫 v3"""
    
    # 数据源配置
    SOURCES = [
        {
            'name': 'gaokao.com',
            'base_url': 'https://www.gaokao.com',
            'urls': [
                # 2024年北京卷
                {
                    'url': 'https://www.gaokao.com/e/20240607/北京卷数学真题',
                    'province': '北京',
                    'year': 2024,
                    'title': '2024年北京卷数学真题'
                },
                # 2024年上海卷
                {
                    'url': 'https://www.gaokao.com/e/20240607/上海卷数学真题',
                    'province': '上海',
                    'year': 2024,
                    'title': '2024年上海卷数学真题'
                },
                # 2024年天津卷
                {
                    'url': 'https://www.gaokao.com/e/20240607/天津卷数学真题',
                    'province': '天津',
                    'year': 2024,
                    'title': '2024年天津卷数学真题'
                },
            ]
        }
    ]
    
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
            follow_redirects=True,
            verify=False  # 跳过SSL验证
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def get_province_dir(self, province: str) -> str:
        """获取省份输出目录"""
        return os.path.join(self.output_dir, f"{province}卷", "raw")
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """获取网页内容"""
        try:
            print(f"    正在获取: {url[:80]}...")
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    ✗ 获取页面失败: {str(e)[:100]}")
            return None
    
    async def search_and_fetch(self, province: str, year: int):
        """搜索并获取指定省份年份的试卷"""
        print(f"\n  搜索 {province} {year}年高考数学试卷...")
        
        # 尝试多个搜索引擎和网站
        search_queries = [
            f"{province} {year}年高考数学真题及答案",
            f"{province}卷 {year} 数学 高考试题",
        ]
        
        for query in search_queries:
            # 使用百度搜索
            baidu_url = f"https://www.baidu.com/s?wd={query}"
            html = await self.fetch_page(baidu_url)
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # 提取搜索结果链接
                results = []
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    text = a.get_text().strip()
                    
                    if any(keyword in text for keyword in [province, str(year), '数学']):
                        results.append({
                            'url': href,
                            'title': text
                        })
                
                if results:
                    print(f"    ✓ 找到 {len(results)} 个相关结果")
                    return results[:5]  # 返回前5个
        
        return []
    
    async def crawl_all(self):
        """爬取所有省份"""
        provinces = ["北京", "上海", "天津"]
        years = [2024, 2023, 2022]
        
        print("="*60)
        print("开始爬取各省份高考数学真题")
        print("="*60)
        
        for province in provinces:
            for year in years:
                try:
                    results = await self.search_and_fetch(province, year)
                    
                    if results:
                        print(f"    📋 搜索结果:")
                        for r in results:
                            print(f"       - {r['title'][:50]}")
                    
                except Exception as e:
                    print(f"  ✗ 爬取失败: {str(e)[:100]}")
                
                await asyncio.sleep(2)  # 避免请求过快
        
        print("\n" + "="*60)
        print("搜索完成!")
        print("="*60)


async def main():
    """主函数"""
    async with ProvinceGaokaoCrawlerV3() as crawler:
        await crawler.crawl_all()


if __name__ == "__main__":
    asyncio.run(main())
