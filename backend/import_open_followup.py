"""补进两份许可清楚、能按年级归类的题，不覆盖已有的年级文件。

- weitianwen/cmath 测试集：CC BY 4.0，小学 1–6 年级应用题。
- ChinaTextbookStudyFree 的英语单元练习：仓库 MIT。只收练习 JSON，不收课文。
重复运行按 source_url 跳过已入库的题。
"""
import asyncio
import json
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))

from database import init_db
from import_open_math import BANK_DIR, import_bank, rebuild_index

RAW = BANK_DIR / "_原始下载"
CMATH_TIP = "来源 XiaoMi/cmath 测试集（weitianwen/cmath），许可 CC BY 4.0。小学应用题，使用前请老师核对。"
ENGLISH_TIP = "来源 ChinaTextbookStudyFree 单元练习，仓库许可 MIT。题目由模型按单元生成，未逐题审核，不含课文原文，使用前请老师核对。"
CMATH_URL = "https://hf-mirror.com/datasets/weitianwen/cmath/resolve/main/cmath_test.jsonl"
QUIZ_PREFIXES = (
    "义务教育教科书·英语（PEP）（三年级起点）",
    "义务教育教科书·英语（三年级起点）",
)
GRADE_WORD = {3: "三", 4: "四", 5: "五", 6: "六"}


def download(url, dest, timeout=60):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    request = urllib.request.Request(url, headers={"User-Agent": "ai-educator"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except Exception as error:
        print(f"失败 {dest.name} {type(error).__name__}", flush=True)
        return False
    if not payload:
        return False
    dest.write_bytes(payload)
    print(f"完成 {dest.name} {len(payload)}", flush=True)
    return True


def quiz_jobs():
    jobs = []
    for grade in (3, 4, 5):
        for semester in ("上", "下"):
            jobs.extend((grade, semester, unit) for unit in range(1, 7))
    jobs.extend((6, "上", unit) for unit in range(1, 8))
    jobs.extend((6, "下", unit) for unit in range(1, 6))
    return jobs


def fetch_quiz(grade, semester, unit):
    for prefix in QUIZ_PREFIXES:
        filename = f"{prefix}{GRADE_WORD[grade]}年级{semester}册_unit{unit}.json"
        dest = RAW / "english_quizzes" / filename
        raw_url = (
            "https://raw.githubusercontent.com/wuwangzhang1216/ChinaTextbookStudyFree/main/output/english/quizzes/"
            + quote(filename)
        )
        for url in ("https://gh-proxy.com/" + raw_url, raw_url):
            if download(url, dest):
                return dest
    return None


def fetch_quizzes():
    saved = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_quiz, *job) for job in quiz_jobs()]
        for future in as_completed(futures):
            path = future.result()
            if path:
                saved.append(path)
    print(f"英语单元文件 {len(saved)}/{len(quiz_jobs())}", flush=True)
    return saved


def stem(text):
    return "".join((text or "").split())


def existing_math_stems():
    found = set()
    folder = BANK_DIR / "小学" / "数学"
    if not folder.exists():
        return found
    for path in folder.glob("*.json"):
        if path.name.endswith("-cmath.json"):
            continue
        for row in json.loads(path.read_text(encoding="utf-8")):
            found.add(stem(row.get("question_text")))
    return found


def cmath_records():
    path = RAW / "cmath_test.jsonl"
    download(CMATH_URL, path, timeout=90)
    seen = existing_math_stems()
    grouped = defaultdict(list)
    skipped = 0
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        item = json.loads(line)
        question = (item.get("question") or "").strip()
        answer = str(item.get("golden") or "").strip()
        grade = item.get("grade")
        if not question or not answer or not isinstance(grade, int) or not 1 <= grade <= 6:
            skipped += 1
            continue
        if stem(question) in seen:
            skipped += 1
            continue
        seen.add(stem(question))
        grouped[grade].append({
            "question_text": question,
            "answer": answer,
            "solution": "",
            "question_type": "解答题",
            "subject": "数学",
            "education_level": "小学",
            "grade": grade,
            "exam_type": "应用题",
            "knowledge_points": [f"{grade}年级应用题"],
            "difficulty": 1 if grade <= 2 else 2 if grade <= 4 else 3,
            "source_url": f"https://huggingface.co/datasets/weitianwen/cmath#test-{index}",
            "teaching_tips": CMATH_TIP,
        })
    for grade, items in grouped.items():
        target = BANK_DIR / "小学" / "数学" / f"{grade}年级-cmath.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"数学 {grade}年级-cmath {len(items)}", flush=True)
    print(f"数学测试集跳过 {skipped}", flush=True)
    return sum(len(items) for items in grouped.values())


def format_english(item):
    question = (item.get("question") or "").strip()
    answer = str(item.get("answer") or "").strip()
    options = item.get("options") or []
    kind = item.get("type") or ""
    names = {"choice": "选择题", "true_false": "判断题", "fill": "填空题", "text_fill": "填空题", "matching": "填空题"}
    if options:
        lines = [question]
        letters = "ABCDEFGH"
        matched = ""
        for index, option in enumerate(options):
            if index >= len(letters):
                break
            text = str(option).strip()
            lines.append(f"{letters[index]}. {text}")
            if answer.lower() == text.lower():
                matched = f"{letters[index]}. {text}"
        question = "\n".join(lines)
        if matched:
            answer = matched
    return question, answer, names.get(kind, "填空题" if answer else "解答题")


def english_records(paths):
    grouped = defaultdict(list)
    skipped = 0
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"无法解析 {path.name}", flush=True)
            continue
        name = path.name
        grade = None
        semester = None
        for number, word in GRADE_WORD.items():
            if f"{word}年级上册" in name:
                grade, semester = number, "上"
            elif f"{word}年级下册" in name:
                grade, semester = number, "下"
        if grade is None:
            skipped += 1
            continue
        unit = payload.get("unit") or ""
        for section, exam_type in (("unit_test", "单元小测"), ("exam", "单元综合")):
            block = payload.get(section) or {}
            questions = block.get("questions") if isinstance(block, dict) else []
            for item in questions or []:
                question, answer, qtype = format_english(item)
                if not question or not answer:
                    skipped += 1
                    continue
                point = item.get("knowledge_point") or unit or "英语"
                grouped[(grade, semester)].append({
                    "question_text": question,
                    "answer": answer,
                    "solution": (item.get("explanation") or "").strip(),
                    "question_type": qtype,
                    "subject": "英语",
                    "education_level": "小学",
                    "grade": grade,
                    "exam_type": exam_type,
                    "knowledge_points": [text for text in (point, unit) if text],
                    "difficulty": item.get("difficulty") if isinstance(item.get("difficulty"), int) else 2,
                    "source_url": f"https://github.com/wuwangzhang1216/ChinaTextbookStudyFree#g{grade}{semester}-u{payload.get('unit_number')}-{section}-{item.get('id')}",
                    "teaching_tips": ENGLISH_TIP,
                })
    for (grade, semester), items in sorted(grouped.items()):
        target = BANK_DIR / "小学" / "英语" / f"{grade}年级{semester}.json"
        target.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"英语 {grade}年级{semester} {len(items)}", flush=True)
    print(f"英语跳过 {skipped}", flush=True)
    return sum(len(items) for items in grouped.values())


async def main():
    math_count = cmath_records()
    quizzes = fetch_quizzes()
    english_count = english_records(quizzes)
    print(f"新文件 数学 {math_count} 英语 {english_count}", flush=True)
    await init_db()
    total, added, updated = await import_bank()
    rebuild_index()
    print(f"题库文件 {total} 道，新导入 {added} 道，补上年段 {updated} 道", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
