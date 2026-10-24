"""第二批 MIT 数学开源题：TAL-SCQ5K-CN / ape210k / math23k → dataset/题库 + question_bank。

仿照 import_open_math：复用 write_bank / import_bank / rebuild_index / format_choices。
原始数据在 dataset/题库/_原始下载/<数据集名>/。本批全是 MIT，不写 _仅非商业。
重复运行按 source_url 幂等；写盘文件带数据集后缀，避免覆盖已有年级文件。

用法：
  python import_open_round3.py           # 规范化写盘并入库（需已下载原始数据）
  python import_open_round3.py --selftest  # 手工 3 条小 JSON 走 normalize，不触网不写库
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
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
from models import QuestionBank

RAW = BANK_DIR / "_原始下载"
SAMPLE_DIR = BANK_DIR / "_抽检"
TAL_REPO = "https://github.com/math-eval/TAL-SCQ5K"
APE_REPO = "https://github.com/Chenny0808/ape210k"
MATH23K_REPO = "https://github.com/SCNU203/Math23k"

TAL_TIP = "来源 TAL-SCQ5K-CN，许可 MIT。竞赛/杯赛题，使用前请老师核对。"
APE_TIP = (
    "来源 ape210k，许可 MIT。无官方解析。"
    "来源网络爬取，含少量噪声，使用前请老师核对。"
)
MATH23K_TIP = (
    "来源 math23k，许可 MIT。无官方解析。"
    "来源网络爬取，含少量噪声，使用前请老师核对。"
)

# 中文年级词 → 数字年级（1–12）。抽样 HuggingFace / README 可见 competition_source_list
# 形如「希望杯五年级」「初中…」「高一…」；原始 JSON **没有**独立 grade 字段，
# 因此从 competition_source_list（及题干兜底）解析后再映射学段。
CN_GRADE = {
    "一年级": 1, "二年级": 2, "三年级": 3, "四年级": 4, "五年级": 5, "六年级": 6,
    "七年级": 7, "八年级": 8, "九年级": 9,
    "十年级": 10, "十一年级": 11, "十二年级": 12,
    "初一": 7, "初二": 8, "初三": 9,
    "高一": 10, "高二": 11, "高三": 12,
}
CN_GRADE_RE = re.compile("|".join(sorted(CN_GRADE, key=len, reverse=True)))


def stage_of(grade: int | None) -> str:
    """数值年级 → 学段。依据与 import_open_math.stage_of 一致：1–6 小学，7–9 初中，10–12 高中。"""
    if grade is None or grade <= 0:
        return "小学"  # 未分级默认归小学目录（ape/math23k）；TAL 未解析到时也先放小学/未分年级
    if grade <= 6:
        return "小学"
    if grade <= 9:
        return "初中"
    return "高中"


def file_label(grade: int | None, suffix: str) -> str:
    if grade is None or grade <= 0:
        return f"未分年级-{suffix}"
    return f"{grade}年级-{suffix}"


def map_tal_difficulty(raw) -> int:
    """TAL difficulty 取值 0–4（字符串或 int）→ 本库 1–5。

    映射：d' = int(d) + 1，即 0→1 … 4→5；越界钳到 1–5；无法解析默认 3。
    """
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return 3
    return max(1, min(5, value + 1))


def flatten_knowledge_routes(routes) -> list[str]:
    """knowledge_point_routes 是粗→细路径字符串列表，按 '->' / '→' 拍平去重保序。"""
    seen = set()
    out = []
    for route in routes or []:
        text = str(route or "").strip()
        if not text:
            continue
        parts = re.split(r"\s*(?:->|→)\s*", text)
        for part in parts:
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                out.append(part)
    return out


def parse_grade_from_text(*texts: str) -> int | None:
    """从竞赛来源 / 题干里抽出中文年级。优先具体年级词，再退到学段关键词。"""
    blob = " ".join(t for t in texts if t)
    if not blob:
        return None
    match = CN_GRADE_RE.search(blob)
    if match:
        return CN_GRADE[match.group(0)]
    if "小学" in blob:
        return 5  # 仅标小学无年级时取中位，写入 5年级-tal；注释见 tal_records
    if "初中" in blob or "中考" in blob:
        return 8
    if "高中" in blob or "高考" in blob:
        return 11
    return None


def resolve_tal_grade(item: dict) -> int | None:
    """TAL 年级解析优先级：
    1) 若将来数据带数值 grade 字段则直接用；
    2) 否则从 competition_source_list 解析（HF 抽样可见「五年级」「二年级」等）；
    3) 再对 problem 题干兜底；
    4) 仍无则 None → 未分年级。
    """
    raw = item.get("grade")
    if isinstance(raw, int) and 1 <= raw <= 12:
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        num = int(raw.strip())
        if 1 <= num <= 12:
            return num
    sources = item.get("competition_source_list") or []
    source_text = " ".join(str(s) for s in sources)
    found = parse_grade_from_text(source_text)
    if found is not None:
        return found
    return parse_grade_from_text(str(item.get("problem") or ""))


def tal_choices(option_list) -> list[dict]:
    """answer_option_list 形如 [[{aoVal, content}], ...] → [{key, text}, ...]。"""
    choices = []
    for block in option_list or []:
        if isinstance(block, list) and block:
            node = block[0] if isinstance(block[0], dict) else {}
        elif isinstance(block, dict):
            node = block
        else:
            continue
        key = str(node.get("aoVal") or node.get("key") or "").strip()
        text = str(node.get("content") or node.get("text") or "").strip()
        if key or text:
            choices.append({"key": key, "text": text})
    return choices


def choice_answer_text(letter: str, choices: list[dict]) -> str:
    letter = (letter or "").strip()
    for choice in choices:
        if (choice.get("key") or "").strip() == letter:
            text = (choice.get("text") or "").strip()
            return f"{letter}. {text}" if text else letter
    return letter


def normalize_tal_item(item: dict) -> dict | None:
    problem = (item.get("problem") or "").strip()
    answer_letter = str(item.get("answer_value") or "").strip()
    if not problem or not answer_letter:
        return None
    choices = tal_choices(item.get("answer_option_list"))
    question = format_choices(problem, choices) if choices else problem
    answer = choice_answer_text(answer_letter, choices)
    analysis = item.get("answer_analysis") or []
    if isinstance(analysis, list):
        solution = "\n".join(str(part).strip() for part in analysis if str(part).strip())
    else:
        solution = str(analysis).strip()
    grade = resolve_tal_grade(item)
    # resolve_tal_grade 已把「小学/初中/高中」关键词落到中位年级；仍为 None 则未分年级归小学目录。
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
        "source_url": f"{TAL_REPO}#cn-{que_id}",
        "teaching_tips": TAL_TIP,
        "_file": (stage, "数学", file_label(grade, "tal")),
    }


def normalize_ape_item(item: dict, index: int) -> dict | None:
    question = (item.get("question") or item.get("original_text") or "").strip()
    answer = str(item.get("answer") if item.get("answer") is not None else item.get("ans") or "").strip()
    if not question or not answer:
        return None
    eid = item.get("id") or index
    return {
        "question_text": question,
        "answer": answer,
        "solution": "",
        "question_type": "解答题",
        "subject": "数学",
        "education_level": "小学",
        "grade": 0,  # 0 = 未分级
        "exam_type": "应用题",
        "knowledge_points": ["小学应用题"],
        "difficulty": 0,  # 0 = 未知
        "source_url": f"{APE_REPO}#{eid}",
        "teaching_tips": APE_TIP,
        "_file": ("小学", "数学", file_label(0, "ape210k")),
    }


def normalize_math23k_item(item: dict, index: int) -> dict | None:
    question = (item.get("original_text") or item.get("question") or "").strip()
    answer = str(item.get("ans") if item.get("ans") is not None else item.get("answer") or "").strip()
    if not question or not answer:
        return None
    eid = item.get("id") or index
    return {
        "question_text": question,
        "answer": answer,
        "solution": "",
        "question_type": "解答题",
        "subject": "数学",
        "education_level": "小学",
        "grade": 0,
        "exam_type": "应用题",
        "knowledge_points": ["小学应用题"],
        "difficulty": 0,
        "source_url": f"{MATH23K_REPO}#{eid}",
        "teaching_tips": MATH23K_TIP,
        "_file": ("小学", "数学", file_label(0, "math23k")),
    }


def load_json_records(path: Path) -> list:
    """支持 JSON 数组、jsonl、以及 ape210k 那种每行一个 JSON 对象。"""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if not stripped:
        return []
    if stripped[0] == "[":
        data = json.loads(text)
        return data if isinstance(data, list) else []
    # 拼接对象格式（如 math23k：}\n{ 分隔的无包裹 JSON 对象序列）
    try:
        return json.loads("[" + re.sub(r"\}\s*\{", "},{", text) + "]")
    except json.JSONDecodeError:
        pass
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def dedupe_records(records: list[dict]) -> list[dict]:
    """批次内按 question_text 空白折叠去重，保留先出现的。"""
    seen = set()
    out = []
    for row in records:
        stem = "".join((row.get("question_text") or "").split())
        if not stem or stem in seen:
            continue
        seen.add(stem)
        out.append(row)
    return out


def tal_records() -> list[dict]:
    folder = RAW / "TAL-SCQ5K"
    paths = [
        folder / "ch_single_choice_train_3K.jsonl",
        folder / "ch_single_choice_test_2K.jsonl",
    ]
    records = []
    for path in paths:
        if not path.exists():
            print(f"缺少 {path}", flush=True)
            continue
        for item in load_json_records(path):
            row = normalize_tal_item(item)
            if row:
                records.append(row)
        print(f"TAL 读取 {path.name}", flush=True)
    return dedupe_records(records)


def ape_records() -> list[dict]:
    folder = RAW / "ape210k"
    paths = [
        folder / "train.ape.json",
        folder / "valid.ape.json",
        folder / "test.ape.json",
    ]
    records = []
    for path in paths:
        if not path.exists():
            print(f"缺少 {path}", flush=True)
            continue
        items = load_json_records(path)
        print(f"ape210k 读取 {path.name} 原始 {len(items)} 条", flush=True)
        for index, item in enumerate(items):
            row = normalize_ape_item(item, index)
            if row:
                records.append(row)
    records = dedupe_records(records)
    print(f"ape210k 规范化后合计 {len(records)} 条", flush=True)
    # 全量入库前抽样 2000 条供人工质检
    sample_n = min(2000, len(records))
    if sample_n:
        sample = random.Random(42).sample(records, sample_n)
        # 抽检文件不带 _file
        payload = [{k: v for k, v in row.items() if k != "_file"} for row in sample]
        SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
        target = SAMPLE_DIR / "ape210k_sample.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写抽检 {target} ({sample_n} 条)", flush=True)
    return records


def math23k_records() -> list[dict]:
    folder = RAW / "math23k"
    paths = [folder / "math23k_train.json", folder / "math23k_test.json"]
    records = []
    for path in paths:
        if not path.exists():
            print(f"缺少 {path}", flush=True)
            continue
        items = load_json_records(path)
        print(f"math23k 读取 {path.name} 原始 {len(items)} 条", flush=True)
        for index, item in enumerate(items):
            row = normalize_math23k_item(item, index)
            if row:
                records.append(row)
    return dedupe_records(records)


def print_group_stats(records: list[dict]) -> None:
    counter: Counter = Counter()
    for row in records:
        stage = row.get("education_level") or "?"
        grade = row.get("grade")
        grade_key = "未分级" if grade in (None, 0) else f"{grade}年级"
        qtype = row.get("question_type") or "?"
        counter[(stage, grade_key, qtype)] += 1
    print("按 学段/年级/题型：", flush=True)
    for (stage, grade_key, qtype), n in sorted(counter.items()):
        print(f"  {stage}/{grade_key}/{qtype}: {n}", flush=True)


async def table_count() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(QuestionBank))
        return int(result.scalar() or 0)


def selftest() -> int:
    """手工 3 条小 JSON 验证 normalize，不读写磁盘题库、不连库。"""
    tal_sample = {
        "queId": "selftest-tal-1",
        "qid": "1",
        "difficulty": "2",
        "problem": "计算 $$1+1$$ 等于多少？",
        "answer_option_list": [
            [{"aoVal": "A", "content": "$$1$$"}],
            [{"aoVal": "B", "content": "$$2$$"}],
            [{"aoVal": "C", "content": "$$3$$"}],
        ],
        "answer_value": "B",
        "answer_analysis": ["$$1+1=2$$，故选 B。"],
        "knowledge_point_routes": ["知识标签->计算模块->整数加减"],
        "competition_source_list": ["2020年希望杯五年级竞赛第1题"],
        "grade": None,
    }
    ape_sample = {
        "id": "ape-self-1",
        "question": "鸡兔同笼，共 10 只，腿 28 条，鸡有几只？",
        "equation": "x=6",
        "answer": "6",
    }
    math_sample = {
        "id": "m23-self-1",
        "original_text": "小明有 3 个苹果，又买了 2 个，一共几个？",
        "equation": "x=5",
        "ans": "5",
    }
    tal = normalize_tal_item(tal_sample)
    ape = normalize_ape_item(ape_sample, 0)
    math23 = normalize_math23k_item(math_sample, 0)
    assert tal is not None, "TAL normalize 失败"
    assert ape is not None, "ape normalize 失败"
    assert math23 is not None, "math23k normalize 失败"
    assert tal["grade"] == 5, f"TAL grade 期望 5，得到 {tal['grade']}"
    assert tal["education_level"] == "小学"
    assert tal["question_type"] == "选择题"
    assert "A. $$1$$" in tal["question_text"] and tal["answer"].startswith("B.")
    assert tal["difficulty"] == 3  # 2+1
    assert "计算模块" in tal["knowledge_points"]
    assert ape["grade"] == 0 and ape["difficulty"] == 0 and ape["solution"] == ""
    assert ape["question_type"] == "解答题" and ape["education_level"] == "小学"
    assert math23["grade"] == 0 and math23["answer"] == "5"
    print("selftest OK")
    print(json.dumps(
        {
            "tal": {k: v for k, v in tal.items() if k != "_file"},
            "ape210k": {k: v for k, v in ape.items() if k != "_file"},
            "math23k": {k: v for k, v in math23.items() if k != "_file"},
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


async def main_async() -> int:
    before = 0
    await init_db()
    before = await table_count()

    records: list[dict] = []
    records.extend(tal_records())
    records.extend(ape_records())
    records.extend(math23k_records())
    records = dedupe_records(records)

    if not records:
        print("没有可导入记录。请先运行 scripts/fetch_datasets.py 下载原始数据。", flush=True)
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
    parser = argparse.ArgumentParser(description="导入 TAL-SCQ5K / ape210k / math23k")
    parser.add_argument("--selftest", action="store_true", help="跑 normalize 自检，不下载不入库")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
