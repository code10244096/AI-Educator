"""第三批开源题：ChinaTextbookStudyFree（语文/数学/英语/科学 小学）+ TAL-SCQ5K-EN + CMATH。

仿照 import_open_round3：复用 write_bank / import_bank / rebuild_index / format_choices。
原始数据在 dataset/题库/_原始下载/<数据集名>/。本批许可：
  - ChinaTextbookStudyFree：仓库 MIT；题目为 AI 生成、未经教师逐题审核（teaching_tips 注明）。
  - TAL-SCQ5K-EN：MIT。英文竞赛选择题，作为数学（英文）拓展题。
  - CMATH（XiaoMi）：数据集 CC BY 4.0（需署名），人工校验的小学数学样本。
重复运行按 source_url 幂等；写盘文件带数据集后缀，避免覆盖已有年级文件。

用法：
  python import_open_round4.py           # 规范化写盘并入库（需已下载原始数据）
  python import_open_round4.py --selftest  # 手工 3 条小 JSON 走 normalize，不触网不写库
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import func, select

from database import AsyncSessionLocal, init_db
from import_open_math import (
    BANK_DIR,
    format_choices,
    import_bank,
    rebuild_index,
    write_bank,
)
from import_open_round3 import dedupe_records, file_label, load_json_records, stage_of
from models import QuestionBank

RAW = BANK_DIR / "_原始下载"
CSF_REPO = "https://github.com/wuwangzhang1216/ChinaTextbookStudyFree"
TAL_REPO = "https://github.com/math-eval/TAL-SCQ5K"
CMATH_REPO = "https://github.com/XiaoMi/cmath"

CSF_TIP = (
    "来源 ChinaTextbookStudyFree，仓库许可 MIT。题目为 AI 生成、未经教师逐题审核，"
    "使用前请老师核对。"
)
TAL_EN_TIP = "来源 TAL-SCQ5K-EN，许可 MIT。英文竞赛题，可作拓展/双语教学材料，使用前请老师核对。"
CMATH_TIP = "来源 CMATH（小米），数据集 CC BY 4.0（需署名）。人工校验样本，使用前请老师核对。"

CSF_SUBJECT = {"chinese": "语文", "math": "数学", "english": "英语", "science": "科学"}
CSF_QTYPE = {
    "true_false": "判断题",
    "choice": "选择题",
    "fill_blank": "填空题",
    "fill_blank_text": "填空题",
    "calculation": "计算题",
    "matching": "连线题",
    "word_order": "排序题",
}
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
GRADE_RE = re.compile(r"([一二三四五六])年级")


def parse_csf_grade(filename: str) -> int:
    m = GRADE_RE.search(filename)
    return CN_NUM[m.group(1)] if m else 0


def csf_answer_choice(answer: str, options: list[str]) -> str:
    """choice 题 answer 是选项全文 → 找到序号生成 'A. Her' 形式；找不到就原文返回。"""
    answer = (answer or "").strip()
    for idx, opt in enumerate(options or []):
        if str(opt).strip() == answer:
            key = chr(ord("A") + idx)
            return f"{key}. {answer}"
    return answer


def csf_options_block(options) -> list[dict]:
    return [{"key": chr(ord("A") + i), "text": str(opt).strip()}
            for i, opt in enumerate(options or []) if str(opt).strip()]


def normalize_csf_question(q: dict, subject: str, grade: int,
                           textbook: str, unit: str, exam_type: str,
                           source_url: str) -> dict | None:
    question = (q.get("question") or "").strip()
    answer_raw = str(q.get("answer") or "").strip()
    qtype_raw = q.get("type") or ""
    if not question or not answer_raw or qtype_raw not in CSF_QTYPE:
        return None
    options = csf_options_block(q.get("options"))
    if qtype_raw == "choice" and options:
        question_text = format_choices(question, options)
        answer = csf_answer_choice(answer_raw, [o["text"] for o in options])
    elif options:
        # matching / word_order 等：选项无标准字母键，拍平进题干
        opts_text = "；".join(f"({chr(ord('A') + i)}) {o['text']}" for i, o in enumerate(options))
        question_text = f"{question}\n选项：{opts_text}"
        answer = answer_raw
    else:
        question_text = question
        answer = answer_raw
    kp = (q.get("knowledge_point") or "").strip()
    try:
        difficulty = max(1, min(5, int(q.get("difficulty") or 3)))
    except (TypeError, ValueError):
        difficulty = 3
    return {
        "question_text": question_text,
        "answer": answer,
        "solution": (q.get("explanation") or "").strip(),
        "question_type": CSF_QTYPE[qtype_raw],
        "subject": subject,
        "education_level": stage_of(grade),
        "grade": grade,
        "exam_type": exam_type,
        "knowledge_points": [kp] if kp else [],
        "difficulty": difficulty,
        "source_url": source_url,
        "teaching_tips": CSF_TIP,
        "_file": (stage_of(grade), subject, file_label(grade, "csf")),
    }


def csf_records() -> list[dict]:
    folder = RAW / "ChinaTextbookStudyFree"
    records: list[dict] = []
    skipped = Counter()
    for key, subject in CSF_SUBJECT.items():
        quiz_dir = folder / "output" / key / "quizzes"
        if not quiz_dir.is_dir():
            print(f"缺少 {quiz_dir}", flush=True)
            continue
        for path in sorted(quiz_dir.glob("*.json")):
            grade = parse_csf_grade(path.name)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(f"解析失败 {path.name}: {exc}", flush=True)
                continue
            textbook = str(data.get("textbook") or path.name)
            unit = str(data.get("unit") or "")
            for section, exam_type in (("unit_test", "单元测验"), ("exam", "综合卷")):
                sec = data.get(section)
                questions = sec.get("questions") if isinstance(sec, dict) else None
                for q in questions or []:
                    url = f"{CSF_REPO}#{'/'.join(path.relative_to(folder).parts)}#{q.get('id')}"
                    row = normalize_csf_question(q, subject, grade, textbook, unit,
                                                 exam_type, url)
                    if row is None:
                        skipped[q.get("type")] += 1
                        continue
                    records.append(row)
            print(f"CSF {subject} 读取 {path.name}", flush=True)
    if skipped:
        print(f"CSF 跳过题型分布: {dict(skipped)}", flush=True)
    return dedupe_records(records)


def normalize_tal_en_item(item: dict) -> dict | None:
    """TAL-SCQ5K-EN：schema 与 CN 完全一致，年级从 competition_source_list 的英文标签解析。"""
    from import_open_round3 import map_tal_difficulty, tal_choices, choice_answer_text, flatten_knowledge_routes  # noqa: E402

    en_grade = {
        "grade 1": 1, "grade 2": 2, "grade 3": 3, "grade 4": 4,
        "grade 5": 5, "grade 6": 6, "grade 7": 7, "grade 8": 8, "grade 9": 9,
        "grade 10": 10, "grade 11": 11, "grade 12": 12,
        "primary": 5, "elementary": 5, "middle school": 8, "junior": 8,
        "high school": 11, "senior": 11,
    }
    problem = (item.get("problem") or "").strip()
    answer_letter = str(item.get("answer_value") or "").strip()
    if not problem or not answer_letter:
        return None
    choices = tal_choices(item.get("answer_option_list"))
    question = format_choices(problem, choices) if choices else problem
    answer = choice_answer_text(answer_letter, choices)
    analysis = item.get("answer_analysis") or []
    if isinstance(analysis, list):
        solution = "\n".join(str(p).strip() for p in analysis if str(p).strip())
    else:
        solution = str(analysis).strip()
    grade = None
    blob = " ".join(str(s) for s in (item.get("competition_source_list") or [])).lower()
    for label, num in sorted(en_grade.items(), key=lambda kv: -len(kv[0])):
        if label in blob:
            grade = num
            break
    stage = stage_of(grade)
    que_id = item.get("queId") or item.get("qid") or ""
    return {
        "question_text": question,
        "answer": answer,
        "solution": solution,
        "question_type": "选择题",
        "subject": "数学",
        "education_level": stage,
        "grade": grade,  # None 表示未分级
        "exam_type": "竞赛",
        "knowledge_points": flatten_knowledge_routes(item.get("knowledge_point_routes")),
        "difficulty": map_tal_difficulty(item.get("difficulty")),
        "source_url": f"{TAL_REPO}#en-{que_id}",
        "teaching_tips": TAL_EN_TIP,
        "_file": (stage, "数学", file_label(grade, "tal-en")),
    }


def tal_en_records() -> list[dict]:
    folder = RAW / "TAL-SCQ5K-EN"
    records: list[dict] = []
    for path in sorted(folder.glob("en_single_choice_*.jsonl")):
        for item in load_json_records(path):
            row = normalize_tal_en_item(item)
            if row:
                records.append(row)
        print(f"TAL-EN 读取 {path.name}", flush=True)
    return dedupe_records(records)


def normalize_cmath_item(item: dict, index: int) -> dict | None:
    question = (item.get("input") or "").strip()
    answer = str(item.get("golden") or "").strip()
    if not question or not answer:
        return None
    grade = item.get("grade")
    grade = grade if isinstance(grade, int) and 1 <= grade <= 6 else 0
    steps = item.get("reasoning_step")
    try:
        # reasoning_step 1–4+ → 难度 1–5：步数越多越难，封顶 5
        difficulty = max(1, min(5, int(steps) + 1))
    except (TypeError, ValueError):
        difficulty = 3
    return {
        "question_text": question,
        "answer": answer,
        "solution": "",
        "question_type": "解答题",
        "subject": "数学",
        "education_level": "小学",
        "grade": grade,
        "exam_type": "应用题",
        "knowledge_points": ["小学应用题"],
        "difficulty": difficulty,
        "source_url": f"{CMATH_REPO}#cmath-dev-{index}",
        "teaching_tips": CMATH_TIP,
        "_file": ("小学", "数学", file_label(grade, "cmath")),
    }


def cmath_records() -> list[dict]:
    folder = RAW / "cmath"
    records: list[dict] = []
    for path in sorted(folder.glob("**/cmath_dev.jsonl")):
        for index, item in enumerate(load_json_records(path)):
            row = normalize_cmath_item(item, index)
            if row:
                records.append(row)
        print(f"CMATH 读取 {path}", flush=True)
    return dedupe_records(records)


def print_group_stats(records: list[dict]) -> None:
    counter: Counter = Counter()
    for row in records:
        stage = row.get("education_level") or "?"
        grade = row.get("grade")
        grade_key = "未分级" if grade in (None, 0) else f"{grade}年级"
        counter[(row.get("subject") or "?", stage, grade_key, row.get("question_type") or "?")] += 1
    print("按 学科/学段/年级/题型：", flush=True)
    for (subject, stage, grade_key, qtype), n in sorted(counter.items()):
        print(f"  {subject}/{stage}/{grade_key}/{qtype}: {n}", flush=True)


async def table_count() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(QuestionBank))
        return int(result.scalar() or 0)


def selftest() -> int:
    """手工构造小样本验证 normalize，不读写磁盘题库、不连库。"""
    csf_choice = {
        "id": 1, "type": "choice", "score": 5, "difficulty": 2,
        "knowledge_point": "物主代词",
        "question": "My friend is a girl. ______ name is Amy.",
        "options": ["His", "Her", "She", "He"],
        "answer": "Her",
        "explanation": "name 前用形容词性物主代词 her。",
    }
    csf_tf = {
        "id": 2, "type": "true_false", "score": 2, "difficulty": 1,
        "knowledge_point": "拼音", "question": "‘天’的拼音是 tiān。", "options": [],
        "answer": "对", "explanation": "",
    }
    tal_en_sample = {
        "queId": "en-self-1", "difficulty": "3",
        "problem": "Compute $$2+2$$.",
        "answer_option_list": [[{"aoVal": "A", "content": "$$3$$"}],
                               [{"aoVal": "B", "content": "$$4$$"}]],
        "answer_value": "B", "answer_analysis": ["$$2+2=4$$."],
        "knowledge_point_routes": ["Algebra->Arithmetic"],
        "competition_source_list": ["2021 Math Kangaroo Grade 3"],
    }
    cmath_sample = {"grade": 3, "input": "小明有 5 元，花了 2 元，还剩几元？",
                    "golden": "3", "reasoning_step": 1}
    c = normalize_csf_question(csf_choice, "英语", 4, "t", "u", "单元测验", "url#1")
    t = normalize_csf_question(csf_tf, "语文", 1, "t", "u", "单元测验", "url#2")
    e = normalize_tal_en_item(tal_en_sample)
    m = normalize_cmath_item(cmath_sample, 0)
    assert c and c["question_type"] == "选择题" and c["answer"] == "B. Her"
    assert "A. His" in c["question_text"] and c["grade"] == 4 and c["subject"] == "英语"
    assert t and t["question_type"] == "判断题" and t["answer"] == "对"
    assert e and e["grade"] == 3 and e["subject"] == "数学" and e["answer"].startswith("B.")
    assert e["difficulty"] == 4  # 3+1
    assert m and m["grade"] == 3 and m["answer"] == "3" and m["difficulty"] == 2
    assert parse_csf_grade("义务教育教科书·语文一年级上册_unit1.json") == 1
    assert parse_csf_grade("义务教育教科书·英语（PEP）（三年级起点）三年级上册_unit1.json") == 3
    print("selftest OK")
    return 0


async def main_async() -> int:
    await init_db()
    before = await table_count()

    records: list[dict] = []
    records.extend(csf_records())
    records.extend(tal_en_records())
    records.extend(cmath_records())
    records = dedupe_records(records)

    if not records:
        print("没有可导入记录。请先下载原始数据（见 scripts/fetch_datasets.py 或手动放置）。", flush=True)
        return 1

    print_group_stats(records)
    # write_bank 会 pop _file；先拷贝一份统计用已完成
    written = write_bank([dict(row) for row in records])
    print(f"已写入题库文件约 {written} 道（按文件分组后）", flush=True)

    total, added, updated = await import_bank()
    rebuild_index()
    after = await table_count()
    print(f"题库文件扫描 {total} 道，新导入 {added} 道，补上年段 {updated} 道", flush=True)
    print(f"question_bank 行数 {before} → {after}，增量 {after - before}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="导入 ChinaTextbookStudyFree / TAL-SCQ5K-EN / CMATH")
    parser.add_argument("--selftest", action="store_true", help="跑 normalize 自检，不下载不入库")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
