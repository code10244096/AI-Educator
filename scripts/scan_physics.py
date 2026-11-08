# -*- coding: utf-8 -*-
"""扫描物理题库各种乱码/损坏模式，仅读取不修改。"""
import json, re, sys
from collections import defaultdict, Counter

FILES = [
    'dataset/题库/初中/物理/8年级.json',
    'dataset/题库/初中/物理/9年级.json',
    'dataset/题库/高中/物理/10年级.json',
    'dataset/题库/高中/物理/11年级.json',
    'dataset/题库/高中/物理/12年级.json',
    'dataset/题库/高中/物理/选择性必修.json',
]
TEXT_FIELDS = ['question_text', 'answer', 'solution', 'teaching_tips', 'knowledge_points']

# 模式定义
PATTERNS = {
    # a. 分式错位 \frac{a},{b}
    'frac_comma': re.compile(r'\\frac\{[^{}]*\}\s*,\s*\{'),
    # 更宽的 \frac{...} 后紧跟逗号+括号
    'frac_comma_wide': re.compile(r'\\frac\{.*?\}\s*,\s*\{'),
    # b. sqrt 参数后逗号
    'sqrt_comma': re.compile(r'\\sqrt\{[^{}]*\}\s*,\s*\{'),
    # left 无配对 right (逐字段统计)
    # c. UTF-8 乱码
    'ufffd': re.compile('\ufffd'),
    'mojibake': re.compile(r'Ã.|â€.|Â.|\xc3|\xe2\x80'),
    # d. HTML 残留
    'html_tag': re.compile(r'<\s*(br|div|p|span|sup|sub|table|tr|td|li|ul|font|img)[^>]*>', re.I),
    'html_entity': re.compile(r'&\w+;|&#\d+;'),
    # f. $$ 不成对
}

def walk_text(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, list):
        for i in x:
            yield from walk_text(i)
    elif isinstance(x, dict):
        for v in x.values():
            yield from walk_text(v)

stats = defaultdict(list)   # pattern -> list of (file, qidx, field, snippet)
totals = Counter()

for f in FILES:
    data = json.load(open(f, encoding='utf-8'))
    totals[f] = len(data)
    for qi, q in enumerate(data):
        for fld in TEXT_FIELDS:
            v = q.get(fld)
            if v is None:
                if fld in ('question_text', 'answer'):
                    stats['empty_field'].append((f, qi, fld, 'None'))
                continue
            texts = list(walk_text(v)) if not isinstance(v, str) else [v]
            for t in texts:
                if fld in ('question_text', 'answer', 'solution') and not t.strip():
                    stats['empty_field'].append((f, qi, fld, 'empty'))
                    continue
                for name, rx in PATTERNS.items():
                    for m in rx.finditer(t):
                        s = max(0, m.start() - 30)
                        stats[name].append((f, qi, fld, t[s:m.end() + 30].replace('\n', ' ')))
                # $$ 配对
                if t.count('$$') % 2 != 0:
                    stats['dollar_unpaired'].append((f, qi, fld, t[:80].replace('\n', ' ')))
                # \left \right 配对
                nl, nr = len(re.findall(r'\\left\b', t)), len(re.findall(r'\\right\b', t))
                if nl != nr:
                    stats['leftright_unpaired'].append((f, qi, fld, f'left={nl} right={nr} :: ' + t[:80].replace('\n', ' ')))
                # 下标/上标后裸逗号分组错位 ^{a},{b} 或 _{a},{b}
                for m in re.finditer(r'[\^_]\{[^{}]*\}\s*,\s*\{[^{}]*\}', t):
                    stats['sub_sup_comma'].append((f, qi, fld, t[max(0,m.start()-20):m.end()+20].replace('\n',' ')))

print('=== 题量 ===')
for f, n in totals.items():
    print(f'{f}: {n}')
print('总数:', sum(totals.values()))

print('\n=== 各模式命中条数 ===')
for k, v in sorted(stats.items(), key=lambda kv: -len(kv[1])):
    print(f'{k}: {len(v)}')

print('\n=== 各模式抽样（前 12 条） ===')
for k, v in sorted(stats.items()):
    print(f'\n--- {k} ({len(v)}) ---')
    seen = set()
    cnt = 0
    for f, qi, fld, snip in v:
        key = snip
        if key in seen:
            continue
        seen.add(key)
        print(f'[{f} q{qi} {fld}] {snip}')
        cnt += 1
        if cnt >= 12:
            break
