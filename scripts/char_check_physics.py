# -*- coding: utf-8 -*-
"""物理题库字符级全面体检（只读）。"""
import json, re, unicodedata
from collections import Counter

FILES = [
    'dataset/题库/初中/物理/8年级.json',
    'dataset/题库/初中/物理/9年级.json',
    'dataset/题库/高中/物理/10年级.json',
    'dataset/题库/高中/物理/11年级.json',
    'dataset/题库/高中/物理/12年级.json',
    'dataset/题库/高中/物理/选择性必修.json',
]
ALL_FIELDS = ['question_text','answer','solution','question_type','subject',
              'education_level','grade','exam_type','knowledge_points',
              'difficulty','source_url','teaching_tips']

c = Counter()
weird = Counter()
samples = {}

BS = chr(92)  # backslash

def walk(x, path):
    if isinstance(x, str):
        yield x, path
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f'{path}[{i}]')
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f'{path}.{k}')

for f in FILES:
    data = json.load(open(f, encoding='utf-8'))
    for qi, q in enumerate(data):
        for k in ALL_FIELDS:
            if k not in q:
                c[f'missing:{k}'] += 1
            elif q[k] is None:
                c[f'null:{k}'] += 1
        for t, path in walk(q, f'q{qi}'):
            if BS in t:
                c['has_backslash'] += 1
                samples.setdefault('backslash', (f, qi, path, t[:100]))
            if '$' in t:
                c['has_dollar'] += 1
            if '�' in t:
                c['has_ufffd'] += 1
            if re.search(r'&[a-zA-Z#0-9]+;', t):
                c['has_entity'] += 1
                samples.setdefault('entity', (f, qi, path, t[:100]))
            if re.search(r'&nbsp|&amp|&lt|&gt', t):
                c['entity_common'] += 1
            for m in re.finditer(r'<[a-zA-Z/][^>]*>', t):
                tag = m.group(0).lower()
                if tag not in ('<br>', '</br>', '<br/>', '<br />'):
                    c['html_tag_other'] += 1
                    samples.setdefault('html_' + tag, (f, qi, path, t[max(0,m.start()-25):m.end()+25]))
            for ch in t:
                o = ord(ch)
                cat = unicodedata.category(ch)
                if cat in ('Cc', 'Cs') and ch not in '\n\t':
                    weird[repr(ch)] += 1
                    samples.setdefault('ctrl_' + repr(ch), (f, qi, path, t[:80]))
                if cat == 'Sk':
                    weird[ch] += 1
                if 0xE000 <= o <= 0xF8FF or 0xFFF0 <= o <= 0xFFFF:
                    weird[ch] += 1
                    samples.setdefault('pua_' + ch, (f, qi, path, t[:80]))
                if ch in 'ÃÂâ€™Âéè':
                    weird['mojibake_' + ch] += 1
                    idx = t.find(ch)
                    samples.setdefault('mojibake_' + ch, (f, qi, path, t[max(0,idx-25):idx+25]))

print('字段问题统计:', dict(c))
print('异常字符:', dict(weird))
print()
for k, v in samples.items():
    print(k, '=>', v)
