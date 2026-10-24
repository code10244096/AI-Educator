"""把许可证清楚的公开题库按学段和学科写入 dataset/题库/_仅非商业，并导入同一个 question_bank。

只收 C-Eval 与 CMMLU 里能对上中小学和大学学科的选择题。二者都是 CC BY-NC-SA 4.0。
Math23K、Ape210K 的题目来自网站爬取，第三方仓库上的 MIT 不能覆盖题目本身，这里不导入。
重复运行不会插入已有 source_url。
"""
import asyncio
import csv
import io
import json
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from import_open_math import BANK_DIR, import_bank, rebuild_index
from database import init_db

RAW = BANK_DIR / "_原始下载"
LIMITED = BANK_DIR / "_仅非商业"
CEVAL_REPO = "https://huggingface.co/datasets/ceval/ceval-exam"
CMMLU_REPO = "https://github.com/haonan-li/CMMLU"
NC_TIP = "来源 {source}，许可 CC BY-NC-SA 4.0。只能非商业使用，再分发须保持相同许可。原数据没有细分年级，使用前请老师核对。"

CEVAL_TASKS = {
    "middle_school_mathematics": ("初中", "数学", "初中数学"),
    "middle_school_physics": ("初中", "物理", "初中物理"),
    "middle_school_chemistry": ("初中", "化学", "初中化学"),
    "middle_school_biology": ("初中", "生物", "初中生物"),
    "middle_school_politics": ("初中", "政治", "初中政治"),
    "middle_school_history": ("初中", "历史", "初中历史"),
    "middle_school_geography": ("初中", "地理", "初中地理"),
    "high_school_mathematics": ("高中", "数学", "高中数学"),
    "high_school_physics": ("高中", "物理", "高中物理"),
    "high_school_chemistry": ("高中", "化学", "高中化学"),
    "high_school_biology": ("高中", "生物", "高中生物"),
    "high_school_politics": ("高中", "政治", "高中政治"),
    "high_school_history": ("高中", "历史", "高中历史"),
    "high_school_geography": ("高中", "地理", "高中地理"),
    "high_school_chinese": ("高中", "语文", "高中语文"),
    "advanced_mathematics": ("大学", "数学", "高等数学"),
    "probability_and_statistics": ("大学", "数学", "概率统计"),
    "discrete_mathematics": ("大学", "数学", "离散数学"),
    "college_physics": ("大学", "大学物理", "大学物理"),
    "college_chemistry": ("大学", "大学化学", "大学化学"),
    "chinese_language_and_literature": ("大学", "大学语文", "大学语文"),
    "college_programming": ("大学", "计算机", "大学编程"),
    "computer_network": ("大学", "计算机", "计算机网络"),
    "operating_system": ("大学", "计算机", "操作系统"),
    "computer_architecture": ("大学", "计算机", "计算机组成"),
    "college_economics": ("大学", "经济学", "大学经济学"),
    "business_administration": ("大学", "管理学", "工商管理"),
}

CMMLU_TASKS = {
    "elementary_chinese": ("小学", "语文", "小学语文"),
    "elementary_mathematics": ("小学", "数学", "小学数学"),
    "high_school_mathematics": ("高中", "数学", "高中数学"),
    "high_school_physics": ("高中", "物理", "高中物理"),
    "high_school_chemistry": ("高中", "化学", "高中化学"),
    "high_school_biology": ("高中", "生物", "高中生物"),
    "high_school_politics": ("高中", "政治", "高中政治"),
    "high_school_geography": ("高中", "地理", "高中地理"),
    "chinese_history": ("高中", "历史", "中国历史"),
    "world_history": ("高中", "历史", "世界历史"),
    "chinese_literature": ("高中", "语文", "中国文学"),
    "ancient_chinese": ("高中", "语文", "古汉语"),
    "modern_chinese": ("高中", "语文", "现代汉语"),
}


def download(url, dest, timeout=60):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"已有 {dest.name} {dest.stat().st_size}", flush=True)
        return True
    print(f"下载 {url}", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": "ai-educator"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, dest.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 128)
                if not chunk:
                    break
                handle.write(chunk)
    except Exception as error:
        if dest.exists():
            dest.unlink()
        print(f"失败 {type(error).__name__}: {error}", flush=True)
        return False
    print(f"完成 {dest.name} {dest.stat().st_size}", flush=True)
    return dest.stat().st_size > 0


def fetch_cmmlu():
    saved = []
    for split in ("dev", "test"):
        for name in CMMLU_TASKS:
            dest = RAW / "cmmlu" / split / f"{name}.csv"
            url = f"https://raw.githubusercontent.com/haonan-li/CMMLU/master/data/{split}/{name}.csv"
            mirror = "https://gh-proxy.com/" + url
            if download(url, dest) or download(mirror, dest):
                saved.append(dest)
    return saved


def fetch_one_ceval(task, split):
    dest = RAW / "ceval" / task / f"{split}.parquet"
    name = f"{split}-00000-of-00001.parquet"
    urls = [
        f"https://hf-mirror.com/datasets/ceval/ceval-exam/resolve/main/{task}/{name}",
        f"https://huggingface.co/datasets/ceval/ceval-exam/resolve/main/{task}/{name}?download=true",
        f"https://gh-proxy.com/https://huggingface.co/datasets/ceval/ceval-exam/resolve/main/{task}/{name}",
    ]
    for url in urls:
        if download(url, dest, timeout=45) and dest.read_bytes()[:4] == b"PAR1":
            return task, split, dest
        if dest.exists():
            dest.unlink()
    print(f"C-Eval 缺少 {task}/{split}", flush=True)
    return None


def fetch_ceval():
    jobs = [(task, split) for task in CEVAL_TASKS for split in ("dev", "val", "test")]
    saved = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_one_ceval, task, split) for task, split in jobs]
        for future in as_completed(futures):
            item = future.result()
            if item:
                saved.append(item)
    return saved


def choice_text(question, options):
    lines = [question.strip()]
    for key, text in options:
        text = (text or "").strip()
        if text:
            lines.append(f"{key}. {text}")
    return "\n".join(lines)


def choice_answer(letter, options):
    letter = (letter or "").strip().upper()
    for key, text in options:
        if key == letter and (text or "").strip():
            return f"{letter}. {text.strip()}"
    return letter


def add_choice(records, seen, source_url, question, options, answer, solution, stage, subject, point, tip):
    question = (question or "").strip()
    answer = (answer or "").strip()
    if not question or not answer or answer.upper() not in {"A", "B", "C", "D"}:
        return False
    stem = "".join(question.split())
    if stem in seen:
        return False
    seen.add(stem)
    records.append({
        "question_text": choice_text(question, options),
        "answer": choice_answer(answer, options),
        "solution": (solution or "").strip(),
        "question_type": "选择题",
        "subject": subject,
        "education_level": stage,
        "grade": None,
        "exam_type": "综合练习",
        "knowledge_points": [point],
        "difficulty": 3,
        "source_url": source_url,
        "teaching_tips": tip,
        "_file": (stage, subject, "未分年级"),
    })
    return True


def read_csv_rows(payload):
    text = payload.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def cmmlu_records(paths, seen):
    records = []
    tip = NC_TIP.format(source="CMMLU")
    for path in paths:
        split = path.parent.name
        name = path.stem
        stage, subject, point = CMMLU_TASKS[name]
        rows = read_csv_rows(path.read_bytes())
        kept = 0
        for index, row in enumerate(rows):
            lowered = {key.lower(): value for key, value in row.items() if key}
            options = [(key, lowered.get(key.lower(), "")) for key in ("A", "B", "C", "D")]
            url = f"{CMMLU_REPO}#{split}-{name}-{index}"
            if add_choice(records, seen, url, lowered.get("question", ""), options, lowered.get("answer", ""), "", stage, subject, point, tip):
                kept += 1
        print(f"CMMLU {split}/{name} {kept}/{len(rows)}", flush=True)
    return records


def ceval_records(files, seen):
    import pyarrow.parquet as pq

    records = []
    tip = NC_TIP.format(source="C-Eval")
    grouped = defaultdict(list)
    for task, split, path in files:
        grouped[task].append((split, path))
    for task, parts in grouped.items():
        stage, subject, point = CEVAL_TASKS[task]
        kept = 0
        total = 0
        for split, path in parts:
            rows = pq.read_table(path).to_pylist()
            total += len(rows)
            for row in rows:
                lowered = {str(key).lower(): value for key, value in row.items()}
                options = [(key, "" if lowered.get(key.lower()) is None else str(lowered.get(key.lower()))) for key in ("A", "B", "C", "D")]
                row_id = lowered.get("id")
                url = f"{CEVAL_REPO}#{task}-{split}-{row_id}"
                answer = lowered.get("answer")
                explanation = lowered.get("explanation")
                if add_choice(
                    records, seen, url, str(lowered.get("question") or ""), options,
                    "" if answer is None else str(answer),
                    "" if explanation is None else str(explanation),
                    stage, subject, point, tip,
                ):
                    kept += 1
        print(f"C-Eval {task} {kept}/{total}", flush=True)
    return records


def write_limited(records):
    grouped = defaultdict(list)
    for row in records:
        stage, subject, label = row.pop("_file")
        grouped[(stage, subject, label)].append(row)
    for (stage, subject, label), items in grouped.items():
        folder = LIMITED / stage / subject
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{label}.json"
        target.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"写入 {target.relative_to(BANK_DIR)} {len(items)}", flush=True)
    return sum(len(items) for items in grouped.values())


async def main():
    cmmlu_paths = fetch_cmmlu()
    ceval_files = fetch_ceval()
    seen = set()
    records = cmmlu_records(cmmlu_paths, seen)
    records.extend(ceval_records(ceval_files, seen))
    written = write_limited(records)
    print(f"仅非商业目录写入 {written} 道", flush=True)
    await init_db()
    total, added, updated = await import_bank()
    rebuild_index()
    print(f"题库文件 {total} 道，新导入 {added} 道，补上年段 {updated} 道", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
