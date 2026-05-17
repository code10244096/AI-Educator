"""
各省份高考数学真题原始内容爬虫
先爬取原始HTML/文本内容保存到文件，后续再转换格式
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


class ProvinceRawContentCrawler:
    """省份高考题目原始内容爬虫"""
    
    BASE_URL = "https://www.gk100.com"
    
    PROVINCES = ["北京", "上海", "天津"]
    
    YEARS = range(2020, 2026)
    
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
        return os.path.join(self.output_dir, f"{province}卷", "raw")
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """获取网页内容"""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    ✗ 获取页面失败: {url} - {str(e)}")
            return None
    
    async def search_gaokao_papers(self, province: str, year: int) -> List[Dict]:
        """搜索高考试卷链接"""
        print(f"  搜索 {province} {year}年高考数学试卷...")
        
        # 尝试多个搜索URL模式
        search_urls = [
            f"{self.BASE_URL}/search/?q={province}+{year}+数学+高考",
            f"{self.BASE_URL}/soft/{province.lower()}{year}math.html",
        ]
        
        found_links = []
        
        for search_url in search_urls:
            html = await self.fetch_page(search_url)
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # 匹配包含省份、年份、数学的链接
                if province in text and str(year) in text and '数学' in text:
                    if href.startswith('/'):
                        href = self.BASE_URL + href
                    
                    found_links.append({
                        'url': href,
                        'title': text
                    })
        
        if found_links:
            print(f"    ✓ 找到 {len(found_links)} 个相关链接")
        else:
            print(f"    ⚠ 未找到相关链接")
        
        return found_links
    
    async def fetch_paper_content(self, url: str, title: str) -> Optional[Dict]:
        """获取试卷详细内容"""
        print(f"    获取试卷内容: {title}")
        
        html = await self.fetch_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取主要内容
        content_div = (
            soup.find('div', class_='content') or 
            soup.find('div', id='content') or 
            soup.find('article') or
            soup.find('div', class_='article-content') or
            soup.find('div', class_='soft-content')
        )
        
        if not content_div:
            content_div = soup.find('body')
        
        if not content_div:
            return None
        
        # 保存原始HTML和文本
        raw_html = str(content_div)
        raw_text = content_div.get_text('\n', strip=True)
        
        # 尝试提取下载链接
        download_links = []
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            text = a.get_text().strip()
            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.zip']):
                if href.startswith('/'):
                    href = self.BASE_URL + href
                download_links.append({
                    'url': href,
                    'text': text
                })
        
        return {
            'url': url,
            'title': title,
            'raw_html': raw_html,
            'raw_text': raw_text,
            'download_links': download_links,
            'crawl_time': datetime.now().isoformat()
        }
    
    async def save_raw_content(self, province: str, year: int, content: Dict):
        """保存原始内容到文件"""
        province_dir = self.get_province_dir(province)
        os.makedirs(province_dir, exist_ok=True)
        
        # 保存原始文本
        text_file = os.path.join(province_dir, f"{year}_{content['title']}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"标题: {content['title']}\n")
            f.write(f"URL: {content['url']}\n")
            f.write(f"爬取时间: {content['crawl_time']}\n")
            f.write("="*60 + "\n\n")
            f.write(content['raw_text'])
        
        # 保存原始HTML
        html_file = os.path.join(province_dir, f"{year}_{content['title']}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content['raw_html'])
        
        # 保存元数据
        meta_file = os.path.join(province_dir, f"{year}_{content['title']}_meta.json")
        meta_data = {
            'url': content['url'],
            'title': content['title'],
            'download_links': content['download_links'],
            'crawl_time': content['crawl_time'],
            'text_file': text_file,
            'html_file': html_file
        }
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
        
        print(f"    💾 已保存: {text_file}")
    
    async def crawl_province_year(self, province: str, year: int):
        """爬取指定省份指定年份"""
        # 搜索相关链接
        links = await self.search_gaokao_papers(province, year)
        
        if not links:
            return
        
        # 获取每个链接的内容
        for link in links[:3]:  # 限制最多3个链接
            content = await self.fetch_paper_content(link['url'], link['title'])
            
            if content:
                await self.save_raw_content(province, year, content)
            
            # 避免请求过快
            await asyncio.sleep(1)
    
    async def crawl_all(self):
        """爬取所有省份所有年份"""
        print("="*60)
        print("开始爬取各省份高考数学真题原始内容")
        print("="*60)
        
        success_count = 0
        
        for province in self.PROVINCES:
            for year in self.YEARS:
                try:
                    await self.crawl_province_year(province, year)
                    success_count += 1
                except Exception as e:
                    print(f"  ✗ {province} {year}年爬取失败: {str(e)}")
                
                # 避免请求过快
                await asyncio.sleep(0.5)
        
        print("\n" + "="*60)
        print(f"爬取完成!")
        print(f"成功: {success_count} 个省份/年份")
        print("="*60)


async def main():
    """主函数"""
    async with ProvinceRawContentCrawler() as crawler:
        await crawler.crawl_all()


if __name__ == "__main__":
    asyncio.run(main())
