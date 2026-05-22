"""
高考真题爬虫脚本
从多个来源抓取上海、北京、天津等地方卷的历年真题
使用内置urllib，无需额外安装依赖
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import re
import os
from pathlib import Path
from html.parser import HTMLParser
import time

# 基础路径
BASE_DIR = Path(r"e:\AI-Educator\dataset\高考\数学")
OUTPUT_DIR = BASE_DIR / "高考数学真题"

# 目标省份和年份 - 扩展更多省份，从2010年开始
TARGETS = {
    "上海": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "北京": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "天津": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "湖北": [2010, 2011, 2012, 2013, 2014],  # 2015年后使用全国卷
    "江苏": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019],  # 2020年后改革
    "浙江": [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021],
    "安徽": [2010, 2011, 2012, 2013, 2014],  # 2015年后使用全国卷
}

# URL模板 - 使用gaokao.eol.cn
URL_TEMPLATES = {
    "上海": "https://gaokao.eol.cn/shiti/sx/202306/t20230609_2434762.shtml",
    "北京": "https://gaokao.eol.cn/shiti/sx/202306/t20230623_2446354.shtml",
    "天津": "https://gaokao.eol.cn/shiti/sx/202306/t20230609_2434972.shtml",
}

# 历年URL映射
YEAR_URLS = {
    "上海": {
        2023: "https://gaokao.eol.cn/shiti/sx/202306/t20230609_2434762.shtml",
        2022: "https://gaokao.eol.cn/shiti/sx/202206/t20220609_2230620.shtml",
        2021: "https://gaokao.eol.cn/shiti/sx/202106/t20210609_2035558.shtml",
        2020: "https://gaokao.eol.cn/shiti/sx/202007/t20200709_1736796.shtml",
    },
    "北京": {
        2023: "https://gaokao.eol.cn/shiti/sx/202306/t20230623_2446354.shtml",
        2022: "https://gaokao.eol.cn/shiti/sx/202212/t20221201_2258870.shtml",
        2021: "https://gaokao.eol.cn/shiti/sx/202106/t20210609_2035554.shtml",
        2020: "https://gaokao.eol.cn/shiti/sx/202007/t20200709_1736792.shtml",
    },
    "天津": {
        2023: "https://gaokao.eol.cn/shiti/sx/202306/t20230609_2434972.shtml",
        2022: "https://gaokao.eol.cn/shiti/sx/202206/t20220609_2230624.shtml",
        2021: "https://gaokao.eol.cn/shiti/sx/202106/t20210609_2035562.shtml",
        2020: "https://gaokao.eol.cn/shiti/sx/202007/t20200709_1736800.shtml",
    },
    # 湖北自主命题时期
    "湖北": {
        2014: "https://gaokao.eol.cn/shiti/zhenti/201406/t20140607_1127949.shtml",
        2013: "https://gaokao.eol.cn/lnzt_2898/20130607/t20130607_957283.shtml",
        2012: "https://gaokao.eol.cn/2012gkst_9309/20120608/t20120608_788293.shtml",
        2011: "https://gaokao.eol.cn/2011gkst_11308/20110531/t20110531_624720.shtml",
        2010: "https://gaokao.eol.cn/2010gkst_9985/20100607/t20100607_483459.shtml",
    },
    # 江苏自主命题时期
    "江苏": {
        2019: "https://gaokao.eol.cn/jiang_su/dongtai/201906/t20190610_1663211.shtml",
        2018: "https://gaokao.eol.cn/jiang_su/dongtai/201806/t20180610_1607818.shtml",
        2017: "https://gaokao.eol.cn/jiang_su/dongtai/201706/t20170607_1523361.shtml",
        2016: "https://gaokao.eol.cn/shiti/zhenti/201606/t20160607_1409187.shtml",
        2015: "https://gaokao.eol.cn/shiti/zhenti/201506/t20150608_1269316.shtml",
        2014: "https://gaokao.eol.cn/shiti/zhenti/201406/t20140607_1127749.shtml",
        2013: "https://gaokao.eol.cn/lnzt_2898/20130608/t20130608_957716.shtml",
        2012: "https://gaokao.eol.cn/huodong/2012gkst/201206/t20120607_787493.shtml",
        2011: "https://gaokao.eol.cn/jiang_su/dongtai/201106/t20110610_631691.shtml",
        2010: "https://gaokao.eol.cn/huodong/2010gkst/201006/t20100608_483599.shtml",
    },
    # 浙江自主命题时期
    "浙江": {
        2021: "https://gaokao.eol.cn/shiti/zhenti/202107/t20210729_2141484.shtml",
        2020: "https://gaokao.eol.cn/shiti/zhenti/202007/t20200710_1737822.shtml",
        2019: "https://gaokao.eol.cn/zhe_jiang/dongtai/201906/t20190608_1662983.shtml",
        2018: "https://gaokao.eol.cn/zhe_jiang/dongtai/201806/t20180609_1607625.shtml",
        2017: "https://gaokao.eol.cn/zhe_jiang/dongtai/201706/t20170607_1523814.shtml",
        2016: "https://gaokao.eol.cn/shiti/zhenti/201606/t20160607_1409050.shtml",
        2015: "https://gaokao.eol.cn/shiti/zhenti/201506/t20150607_1268914.shtml",
        2014: "https://gaokao.eol.cn/shiti/zhenti/201406/t20140607_1127820.shtml",
        2013: "https://gaokao.eol.cn/shiti/zhenti/201306/t20130610_960255.shtml",
        2012: "https://gaokao.eol.cn/huodong/2012gkst/201206/t20120608_788003.shtml",
        2011: "https://gaokao.eol.cn/zhe_jiang/dongtai/201106/t20110609_631430.shtml",
        2010: "https://gaokao.eol.cn/huodong/2010gkst/201006/t20100610_485071.shtml",
    },
    # 安徽自主命题时期
    "安徽": {
        2014: "https://gaokao.eol.cn/shiti/zhenti/201406/t20140607_1127820.shtml",
        2013: "https://gaokao.eol.cn/lnzt_2898/20130607/t20130607_957166.shtml",
        2012: "https://gaokao.eol.cn/huodong/2012gkst/201206/t20120607_787493.shtml",
        2011: "https://gaokao.eol.cn/2011gkst_11308/20110531/t20110531_624871.shtml",
        2010: "https://gaokao.eol.cn/huodong/2010gkst/201006/t20100607_483509.shtml",
    },
}

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


class TextExtractor(HTMLParser):
    """HTML文本提取器"""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
        self.skip = False
    
    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip = True
    
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip = False
    
    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)
    
    def get_text(self):
        return '\n'.join(self.text)


def fetch_url(url):
    """抓取URL内容"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            return html
    except Exception as e:
        print(f"    抓取失败: {e}")
        return None


def parse_text_content(content, province, year):
    """从文本内容中解析题目"""
    questions = []
    
    lines = content.split('\n')
    current_question = None
    current_type = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检测题号
        match = re.match(r'^(\d+)[\.\、\．]\s*(?:\(\d+分\))?\s*(.+)$', line)
        if match and len(line) < 300:
            if current_question:
                questions.append(current_question)
            
            current_question = {
                'question_text': line,
                'answer': '',
                'solution': '',
                'question_type': '未知',
                'subject': '数学',
                'education_level': '高中',
                'exam_type': '高考',
                'year': year,
                'region': province,
                'knowledge_points': [],
                'difficulty': 3,
                'score': 5.0,
                'source_url': '',
                'teaching_tips': '',
                'common_mistakes': ''
            }
            current_type = 'question'
        elif current_question:
            if '【答案】' in line or line.startswith('答案'):
                current_type = 'answer'
                current_question['answer'] = line.replace('【答案】', '').replace('答案', '').strip()
            elif '【解析】' in line or line.startswith('解析') or '【分析】' in line or '【解答】' in line:
                current_type = 'solution'
                current_question['solution'] += '\n' + line
            elif current_type == 'answer':
                current_question['answer'] += ' ' + line
            elif current_type == 'solution':
                current_question['solution'] += '\n' + line
            else:
                current_question['question_text'] += '\n' + line
    
    if current_question:
        questions.append(current_question)
    
    return questions


def save_questions(province, year, questions):
    """保存题目到JSON文件"""
    if not questions:
        return
    
    # 创建文件夹
    province_dir = OUTPUT_DIR / province
    province_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存文件
    output_file = province_dir / f"{year}.json"
    
    output_data = {
        'year': year,
        'region': province,
        'total_questions': len(questions),
        'questions': questions
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"  保存: {output_file}")


def crawl_all():
    """爬取所有目标数据"""
    print("=" * 60)
    print("开始爬取地方卷历年真题")
    print("=" * 60)
    
    total_crawled = 0
    
    for province, years in TARGETS.items():
        print(f"\n【爬取】{province}卷")
        
        for year in years:
            print(f"\n  年份: {year}")
            
            questions = None
            
            # 优先使用YEAR_URLS中的映射URL
            if province in YEAR_URLS and year in YEAR_URLS[province]:
                url = YEAR_URLS[province][year]
                print(f"    URL: {url}")
                html = fetch_url(url)
                
                if html:
                    # 检查是否是404页面
                    if '404' not in html[:500]:
                        parser = TextExtractor()
                        parser.feed(html)
                        text = parser.get_text()
                        questions = parse_text_content(text, province, year)
            
            # 备用来源1: 尝试从gaokao.com抓取
            if not questions:
                time.sleep(2)
                url1 = f"https://www.gaokao.com/e/202406/{urllib.parse.quote(province)}{year}shuxue.shtml"
                print(f"    备用URL: {url1}")
                html = fetch_url(url1)
                
                if html:
                    if '404' not in html[:500]:
                        parser = TextExtractor()
                        parser.feed(html)
                        text = parser.get_text()
                        questions = parse_text_content(text, province, year)
            
            # 备用来源2: 尝试从zujuan.com抓取
            if not questions:
                time.sleep(2)
                url2 = f"https://www.zujuan.com/{urllib.parse.quote(province)}/{year}/shuxue"
                print(f"    备用URL: {url2}")
                html = fetch_url(url2)
                
                if html:
                    parser = TextExtractor()
                    parser.feed(html)
                    text = parser.get_text()
                    questions = parse_text_content(text, province, year)
            
            # 保存数据
            if questions:
                save_questions(province, year, questions)
                total_crawled += len(questions)
            
            # 延迟，避免请求过快
            time.sleep(3)
    
    print("\n" + "=" * 60)
    print("爬取完成！")
    print("=" * 60)
    print(f"  总共爬取: {total_crawled} 道题")


if __name__ == '__main__':
    crawl_all()
