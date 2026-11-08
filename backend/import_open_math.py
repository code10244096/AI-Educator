"""整理开源题库到 dataset/题库，并导入同一个 question_bank。重复运行不会插入已有题目。"""
import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select

from database import AsyncSessionLocal, init_db
from models import QuestionBank

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "dataset" / "题库"
RAW_CANDIDATES = [
    BANK_DIR / "_原始下载",
    Path(__file__).parent / "dataset" / "open",
]
TAXONOMY_REPO = "https://github.com/xiaoyang111222/cn-math-taxonomy"
CMATH_REPO = "https://github.com/XiaoMi/cmath"
GAOKAO_BENCH_REPO = "https://github.com/OpenLMLab/GAOKAO-Bench"
SUBJECTS = {"cnm": "数学", "cne": "英语", "cnp": "物理"}
TYPE_NAMES = {"numeric": "填空题", "choice": "选择题", "short": "解答题", "self": "解答题"}
DIFFICULTY = {"basic": 2, "standard": 3, "advanced": 4}
TAXONOMY_TIP = "来源 cn-math-taxonomy，许可 CC BY-NC 4.0。题目由模型生成，使用前请老师核对。"
CMATH_TIP = "来源 XiaoMi/cmath，许可 CC BY 4.0。这是小学应用题基准集。"
GAOKAO_BENCH_TIP = "来源 OpenLMLab/GAOKAO-Bench，2010–2022 高考数学真题（含解析）。"

# 题号+分值前缀，如 "17. (12 分) " / "13. (5 分) " / "19. （12 分）"
_GAOKAO_PREFIX_RE = re.compile(
    r"^\s*\d+\s*[.、．]?\s*[（(]?\s*\d+(?:\.\d+)?\s*分\s*[)）]?\s*"
)

# 本地文件名 → 远端路径 + 题型（供 daily_crawl / 本地导入共用）
GAOKAO_BENCH_FILES = [
    {
        "local": "2010-2022_Math_I_MCQs.json",
        "remote_path": "Data/Objective_Questions/2010-2022_Math_I_MCQs.json",
        "question_type": "选择题",
    },
    {
        "local": "2010-2022_Math_II_MCQs.json",
        "remote_path": "Data/Objective_Questions/2010-2022_Math_II_MCQs.json",
        "question_type": "选择题",
    },
    {
        "local": "2010-2022_Math_I_Fill-in-the-Blank.json",
        "remote_path": "Data/Subjective_Questions/2010-2022_Math_I_Fill-in-the-Blank.json",
        "question_type": "填空题",
    },
    {
        "local": "2010-2022_Math_II_Fill-in-the-Blank.json",
        "remote_path": "Data/Subjective_Questions/2010-2022_Math_II_Fill-in-the-Blank.json",
        "question_type": "填空题",
    },
    {
        "local": "2010-2022_Math_I_Open-ended_Questions.json",
        "remote_path": "Data/Subjective_Questions/2010-2022_Math_I_Open-ended_Questions.json",
        "question_type": "解答题",
    },
    {
        "local": "2010-2022_Math_II_Open-ended_Questions.json",
        "remote_path": "Data/Subjective_Questions/2010-2022_Math_II_Open-ended_Questions.json",
        "question_type": "解答题",
    },
]


def raw_dir():
    for path in RAW_CANDIDATES:
        if (path / "cn-math-questions.json").exists() and (path / "cn-math-topics.json").exists():
            return path
    return None


def stage_of(grade):
    if grade <= 6:
        return "小学", f"{grade}年级"
    if grade <= 9:
        return "初中", f"{grade}年级"
    if grade <= 12:
        return "高中", f"{grade}年级"
    return "高中", "选择性必修"


def format_choices(prompt, choices):
    lines = [prompt.strip()]
    for choice in choices or []:
        key = (choice.get("key") or "").strip()
        text = (choice.get("text") or "").strip()
        if key and text:
            lines.append(f"{key}. {text}")
    return "\n".join(lines)


def choice_answer(answer, choices):
    letter = (answer or "").strip()
    for choice in choices or []:
        if (choice.get("key") or "").strip() == letter:
            text = (choice.get("text") or "").strip()
            return f"{letter}. {text}" if text else letter
    return letter


def taxonomy_records(questions, topics):
    records = []
    for item in questions:
        topic_id = item.get("topicId") or ""
        prefix = topic_id.split("_")[0]
        subject = SUBJECTS.get(prefix)
        if not subject:
            continue
        topic = topics.get(topic_id) or {}
        grade = topic.get("grade")
        if not isinstance(grade, int):
            continue
        prompt = (item.get("prompt") or "").strip()
        answer = (item.get("answer") or "").strip()
        if not prompt or not answer:
            continue
        qtype = item.get("type") or "short"
        if qtype == "choice":
            prompt = format_choices(prompt, item.get("choices"))
            answer = choice_answer(answer, item.get("choices"))
        stage, _label = stage_of(grade)
        points = [name for name in (topic.get("name"), topic.get("domain")) if name]
        records.append({
            "question_text": prompt,
            "answer": answer,
            "solution": (item.get("explanation") or "").strip(),
            "question_type": TYPE_NAMES.get(qtype, "解答题"),
            "subject": subject,
            "education_level": stage,
            "grade": None if grade > 12 else grade,
            "exam_type": "选择性必修" if grade > 12 else "同步练习",
            "knowledge_points": points,
            "difficulty": DIFFICULTY.get(item.get("difficulty"), 3),
            "source_url": f"{TAXONOMY_REPO}#{item.get('id')}",
            "teaching_tips": TAXONOMY_TIP,
            "_file": (stage, subject, "选择性必修" if grade > 12 else f"{grade}年级"),
        })
    return records


def cmath_records(path):
    records = []
    if not path or not path.exists():
        return records
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        item = json.loads(line)
        prompt = (item.get("input") or "").strip()
        answer = str(item.get("golden") or "").strip()
        grade = item.get("grade") or 0
        if not prompt or not answer or not isinstance(grade, int) or not 1 <= grade <= 6:
            continue
        records.append({
            "question_text": prompt,
            "answer": answer,
            "solution": "",
            "question_type": "解答题",
            "subject": "数学",
            "education_level": "小学",
            "grade": grade,
            "exam_type": "应用题",
            "knowledge_points": [f"{grade}年级应用题"],
            "difficulty": 1 if grade <= 2 else 2 if grade <= 4 else 3,
            "source_url": f"{CMATH_REPO}#dev-{index}",
            "teaching_tips": CMATH_TIP,
            "_file": ("小学", "数学", f"{grade}年级"),
        })
    return records


def strip_gaokao_question_prefix(text: str) -> str:
    """剥高考题干开头的题号与分值前缀；无前缀时幂等返回原文。"""
    if not text:
        return ""
    return _GAOKAO_PREFIX_RE.sub("", text, count=1)


def _gaokao_normalize_answer(answer) -> str:
    if isinstance(answer, list):
        parts = [str(part).strip() for part in answer if str(part).strip()]
        return "、".join(parts)
    return str(answer or "").strip()


def _gaokao_normalize_region(category) -> str:
    region = str(category or "").strip()
    return region.strip("（）()").strip()


def _gaokao_normalize_year(year):
    if year is None or year == "":
        return None
    try:
        return int(year)
    except (TypeError, ValueError):
        return None


def _gaokao_normalize_score(score):
    if score is None or score == "":
        return None
    try:
        value = float(score)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else value


def gaokao_bench_file_records(path, *, remote_path: str, question_type: str):
    """解析单个 GAOKAO-Bench JSON 文件为题库 records。"""
    records = []
    if not path or not Path(path).exists():
        return records
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return records
    examples = payload.get("example") if isinstance(payload, dict) else None
    if not isinstance(examples, list):
        return records

    for item in examples:
        if not isinstance(item, dict):
            continue
        question = strip_gaokao_question_prefix(item.get("question") or "").strip()
        answer = _gaokao_normalize_answer(item.get("answer"))
        if not question or not answer:
            continue
        index = item.get("index")
        if index is None:
            index = len(records)
        records.append({
            "question_text": question,
            "answer": answer,
            "solution": str(item.get("analysis") or "").strip(),
            "question_type": question_type,
            "subject": "数学",
            "education_level": "高中",
            "grade": None,
            "exam_type": "高考",
            "year": _gaokao_normalize_year(item.get("year")),
            "region": _gaokao_normalize_region(item.get("category")),
            "knowledge_points": [],
            "difficulty": 3,
            "score": _gaokao_normalize_score(item.get("score")),
            "source_url": f"{GAOKAO_BENCH_REPO}/blob/main/{remote_path}#q{index}",
            "teaching_tips": GAOKAO_BENCH_TIP,
            "_file": ("高中", "数学", "高考"),
        })
    return records


def gaokao_bench_records(source):
    """从下载目录汇总 6 个数学文件的 records。"""
    records = []
    if not source:
        return records
    root = Path(source)
    for spec in GAOKAO_BENCH_FILES:
        records.extend(
            gaokao_bench_file_records(
                root / spec["local"],
                remote_path=spec["remote_path"],
                question_type=spec["question_type"],
            )
        )
    return records


def write_bank(records):
    grouped = defaultdict(list)
    for row in records:
        stage, subject, label = row.pop("_file")
        grouped[(stage, subject, label)].append(row)
    for (stage, subject, label), items in grouped.items():
        folder = BANK_DIR / stage / subject
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{label}.json"
        target.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    rebuild_index()
    return sum(len(items) for items in grouped.values())


def _nest_counts(bucket):
    return {
        stage: {subject: dict(grades) for subject, grades in subjects.items()}
        for stage, subjects in bucket.items()
    }


def rebuild_index():
    """按磁盘上的题库文件重写索引。主库和仅非商业分开放，避免后一次导入冲掉另一边。"""
    main = defaultdict(lambda: defaultdict(dict))
    limited = defaultdict(lambda: defaultdict(dict))
    for path in iter_bank_files() or []:
        parts = path.relative_to(BANK_DIR).parts
        bucket = limited if "_仅非商业" in parts else main
        parts = [part for part in parts if part != "_仅非商业"]
        if len(parts) < 3:
            continue
        stage, subject, filename = parts[0], parts[1], parts[2]
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        bucket[stage][subject][Path(filename).stem] = len(rows)
    catalog = {
        "location": "dataset/题库",
        "database": "backend/teaching_assistant.db 的 question_bank 表",
        "counts": _nest_counts(main),
        "仅非商业": {
            "说明": "这些题在 dataset/题库/_仅非商业。许可是 CC BY-NC-SA 4.0，不能用于商业产品，再分发也要相同方式共享。",
            "counts": _nest_counts(limited),
        },
    }
    BANK_DIR.mkdir(parents=True, exist_ok=True)
    (BANK_DIR / "索引.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_bank_files():
    if not BANK_DIR.exists():
        return
    for path in sorted(BANK_DIR.rglob("*.json")):
        if path.name == "索引.json" or "_原始下载" in path.parts:
            continue
        yield path


async def import_bank():
    rows = []
    for path in iter_bank_files():
        rows.extend(json.loads(path.read_text(encoding="utf-8")))
    added = 0
    updated = 0
    async with AsyncSessionLocal() as db:
        existing = {
            item.source_url: item
            for item in (await db.execute(select(QuestionBank))).scalars().all()
            if item.source_url
        }
        for row in rows:
            found = existing.get(row["source_url"])
            if found:
                if found.grade != row.get("grade") or found.exam_type != (row.get("exam_type") or ""):
                    found.grade = row.get("grade")
                    found.exam_type = row.get("exam_type") or ""
                    updated += 1
                continue
            db.add(QuestionBank(
                question_text=row["question_text"],
                answer=row["answer"],
                solution=row.get("solution") or "",
                question_type=row["question_type"],
                subject=row["subject"],
                education_level=row["education_level"],
                grade=row.get("grade"),
                exam_type=row.get("exam_type") or "",
                knowledge_points=json.dumps(row.get("knowledge_points") or [], ensure_ascii=False),
                difficulty=row.get("difficulty", 3),
                source_url=row["source_url"],
                teaching_tips=row.get("teaching_tips") or "",
                is_verified=False,
            ))
            added += 1
            if added % 400 == 0:
                await db.commit()
        await db.commit()
    return len(rows), added, updated


async def main():
    source = raw_dir()
    if source:
        questions = json.loads((source / "cn-math-questions.json").read_text(encoding="utf-8"))
        topics = {item["id"]: item for item in json.loads((source / "cn-math-topics.json").read_text(encoding="utf-8"))}
        records = taxonomy_records(questions, topics)
        records.extend(cmath_records(source / "cmath_dev.jsonl"))
        written = write_bank(records)
        print(f"已写入 {BANK_DIR} ，共 {written} 道")
    await init_db()
    total, added, updated = await import_bank()
    print(f"题库文件 {total} 道，新导入 {added} 道，补上年段 {updated} 道")


if __name__ == "__main__":
    asyncio.run(main())
