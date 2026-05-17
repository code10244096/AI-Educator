"""
各省份高考数学真题爬虫 v4
直接访问教育网站获取题目内容
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


class ProvinceGaokaoCrawlerV4:
    """省份高考题目爬虫 v4"""
    
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
            verify=False
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
    
    async def fetch_from_zxxk(self, province: str, year: int):
        """从学科网获取试卷"""
        print(f"\n  从学科网获取 {province} {year}年高考数学试卷...")
        
        # 学科网URL模式
        urls = [
            f"https://www.zxxk.com/soft/{province.lower()}{year}math.html",
            f"https://www.zxxk.com/soft/{province}{year}数学.html",
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                content = soup.get_text()
                if len(content) > 500:
                    print(f"    ✓ 获取成功 ({len(content)} 字符)")
                    return content
        
        return None
    
    async def fetch_from_gaokao_com(self, province: str, year: int):
        """从gaokao.com获取试卷"""
        print(f"\n  从gaokao.com获取 {province} {year}年高考数学试卷...")
        
        # gaokao.com URL模式
        urls = [
            f"https://www.gaokao.com/e/{year}06/{province}math.shtml",
            f"https://www.gaokao.com/e/{year}0607/{province}math.shtml",
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                content = soup.get_text()
                if len(content) > 500:
                    print(f"    ✓ 获取成功 ({len(content)} 字符)")
                    return content
        
        return None
    
    async def fetch_from_51jiaoxi(self, province: str, year: int):
        """从51jiaoxi.com获取试卷"""
        print(f"\n  从51jiaoxi.com获取 {province} {year}年高考数学试卷...")
        
        urls = [
            f"https://www.51jiaoxi.com/{province}{year}math.html",
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                content = soup.get_text()
                if len(content) > 500:
                    print(f"    ✓ 获取成功 ({len(content)} 字符)")
                    return content
        
        return None
    
    async def save_raw_content(self, province: str, year: int, content: str, source: str):
        """保存原始内容"""
        province_dir = self.get_province_dir(province)
        os.makedirs(province_dir, exist_ok=True)
        
        text_file = os.path.join(province_dir, f"{year}_{province}卷数学真题_{source}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"省份: {province}\n")
            f.write(f"年份: {year}\n")
            f.write(f"来源: {source}\n")
            f.write(f"爬取时间: {datetime.now().isoformat()}\n")
            f.write("="*80 + "\n\n")
            f.write(content)
        
        print(f"    💾 已保存: {text_file}")
    
    async def crawl_all(self):
        """爬取所有省份"""
        provinces = ["北京", "上海", "天津"]
        years = [2024, 2023, 2022]
        
        print("="*60)
        print("开始爬取各省份高考数学真题")
        print("="*60)
        
        for province in provinces:
            for year in years:
                # 尝试多个数据源
                for source_name, fetch_func in [
                    ("学科网", self.fetch_from_zxxk),
                    ("gaokao.com", self.fetch_from_gaokao_com),
                    ("51jiaoxi", self.fetch_from_51jiaoxi),
                ]:
                    content = await fetch_func(province, year)
                    
                    if content:
                        await self.save_raw_content(province, year, content, source_name)
                        break
                
                await asyncio.sleep(1)
        
        print("\n" + "="*60)
        print("爬取完成!")
        print("="*60)


async def main():
    """主函数"""
    async with ProvinceGaokaoCrawlerV4() as crawler:
        await crawler.crawl_all()


if __name__ == "__main__":
    asyncio.run(main())
