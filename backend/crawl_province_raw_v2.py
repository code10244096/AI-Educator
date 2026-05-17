"""
各省份高考数学真题原始内容爬虫 v2
直接从已知的具体页面链接爬取
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


class ProvinceRawContentCrawlerV2:
    """省份高考题目原始内容爬虫 v2"""
    
    BASE_URL = "https://www.gk100.com"
    
    # 已知的具体页面URL
    KNOWN_URLS = [
        # 2024年各卷
        {
            'url': 'https://www.gk100.com/read_31319598.htm',
            'title': '2024年全国高考数学真题及答案汇总',
            'province': '全国汇总',
            'year': 2024
        },
        # 北京卷
        {
            'url': 'https://www.gk100.com/read_551667.htm',
            'title': '2024年高考北京卷数学真题及答案解析',
            'province': '北京',
            'year': 2024
        },
        # 上海卷
        {
            'url': 'https://www.gk100.com/read_1184462.htm',
            'title': '2024年高考上海卷数学真题及答案解析',
            'province': '上海',
            'year': 2024
        },
        # 天津卷
        {
            'url': 'https://www.gk100.com/read_10848498.htm',
            'title': '2024年高考天津卷数学真题及答案解析',
            'province': '天津',
            'year': 2024
        },
        # 新课标Ⅰ卷
        {
            'url': 'https://www.gk100.com/read_24945943.htm',
            'title': '2024年新高考一卷数学真题及答案解析',
            'province': '新课标Ⅰ',
            'year': 2024
        },
        # 新课标Ⅱ卷
        {
            'url': 'https://www.gk100.com/read_25152979.htm',
            'title': '2024年新高考二卷数学真题及答案解析',
            'province': '新课标Ⅱ',
            'year': 2024
        },
        # 全国甲卷
        {
            'url': 'https://www.gk100.com/read_22729695.htm',
            'title': '2024年高考全国甲卷数学真题及答案解析',
            'province': '全国甲卷',
            'year': 2024
        },
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
            print(f"    正在获取: {url}")
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    ✗ 获取页面失败: {str(e)}")
            return None
    
    async def fetch_and_save(self, url_info: Dict):
        """获取并保存单个页面"""
        url = url_info['url']
        title = url_info['title']
        province = url_info['province']
        year = url_info['year']
        
        print(f"\n  爬取: {title}")
        
        html = await self.fetch_page(url)
        if not html:
            return False
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种选择器提取主要内容
        content_div = None
        selectors = [
            {'class_': 'content'},
            {'id': 'content'},
            {'name': 'article'},
            {'class_': 'article-content'},
            {'class_': 'soft-content'},
            {'class_': 'detail-content'},
            {'class_': 'paper-content'},
        ]
        
        for selector in selectors:
            content_div = soup.find(**selector)
            if content_div:
                break
        
        if not content_div:
            # 尝试查找包含"试题"或"答案"的div
            for div in soup.find_all('div'):
                text = div.get_text()
                if '试题' in text or '答案' in text or '数学' in text:
                    content_div = div
                    break
        
        if not content_div:
            content_div = soup.find('body')
        
        if not content_div:
            print(f"    ✗ 无法提取内容")
            return False
        
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
        
        # 保存目录
        province_dir = self.get_province_dir(province)
        os.makedirs(province_dir, exist_ok=True)
        
        # 保存原始文本
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        text_file = os.path.join(province_dir, f"{year}_{safe_title}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"标题: {title}\n")
            f.write(f"URL: {url}\n")
            f.write(f"爬取时间: {datetime.now().isoformat()}\n")
            f.write(f"省份: {province}\n")
            f.write(f"年份: {year}\n")
            f.write("="*80 + "\n\n")
            f.write(raw_text)
        
        # 保存原始HTML
        html_file = os.path.join(province_dir, f"{year}_{safe_title}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(raw_html)
        
        # 保存元数据
        meta_file = os.path.join(province_dir, f"{year}_{safe_title}_meta.json")
        meta_data = {
            'url': url,
            'title': title,
            'province': province,
            'year': year,
            'download_links': download_links,
            'crawl_time': datetime.now().isoformat(),
            'text_file': text_file,
            'html_file': html_file,
            'text_length': len(raw_text),
        }
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
        
        print(f"    ✓ 已保存文本 ({len(raw_text)} 字符)")
        print(f"    ✓ 已保存HTML")
        print(f"    ✓ 已保存元数据")
        
        if download_links:
            print(f"    📎 发现 {len(download_links)} 个下载链接")
            for link in download_links:
                print(f"       - {link['text']}: {link['url']}")
        
        return True
    
    async def crawl_all(self):
        """爬取所有已知URL"""
        print("="*60)
        print("开始爬取各省份高考数学真题原始内容")
        print("="*60)
        
        success_count = 0
        total_count = len(self.KNOWN_URLS)
        
        for url_info in self.KNOWN_URLS:
            try:
                result = await self.fetch_and_save(url_info)
                if result:
                    success_count += 1
            except Exception as e:
                print(f"  ✗ 爬取失败: {str(e)}")
            
            # 避免请求过快
            await asyncio.sleep(1)
        
        print("\n" + "="*60)
        print(f"爬取完成!")
        print(f"成功: {success_count}/{total_count}")
        print("="*60)


async def main():
    """主函数"""
    async with ProvinceRawContentCrawlerV2() as crawler:
        await crawler.crawl_all()


if __name__ == "__main__":
    asyncio.run(main())
