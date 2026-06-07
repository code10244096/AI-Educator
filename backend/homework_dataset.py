"""解析 dataset/测试集/批改作业 目录下的测试作业数据"""
import os
import re
from typing import List, Dict, Optional

DATASET_DIR = os.environ.get(
    "DATASET_DIR",
    os.path.join(os.path.dirname(__file__), "..", "dataset", "测试集", "批改作业"),
)


def _split_sections(content: str):
    student_part = content
    reference_part = ""
    if "## 参考答案" in content:
        parts = content.split("## 参考答案", 1)
        student_part = parts[0]
        reference_part = parts[1].strip()
    return student_part, reference_part


def _count_questions(content: str) -> int:
    return len(re.findall(r"^###\s+\d+\.", content, re.MULTILINE))


def _extract_title(content: str, filename: str) -> str:
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else filename.replace(".md", "")


def parse_homework_file(filepath: str) -> Dict:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(filepath)
    student_part, reference_part = _split_sections(content)
    title = _extract_title(content, filename)
    question_count = _count_questions(student_part)

    return {
        "filename": filename,
        "title": title,
        "question_count": question_count,
        "student_content": student_part.strip(),
        "reference_answer": reference_part,
        "full_content": content,
        "file_size": len(content),
    }


def list_dataset_homeworks() -> List[Dict]:
    if not os.path.isdir(DATASET_DIR):
        return []

    files = sorted(
        f for f in os.listdir(DATASET_DIR) if f.endswith(".md")
    )
    result = []
    for idx, filename in enumerate(files, start=1):
        filepath = os.path.join(DATASET_DIR, filename)
        try:
            parsed = parse_homework_file(filepath)
            result.append({
                "id": idx,
                "filename": filename,
                "title": parsed["title"],
                "question_count": parsed["question_count"],
                "file_size": parsed["file_size"],
            })
        except Exception:
            continue
    return result


def get_dataset_homework(file_id: Optional[int] = None, filename: Optional[str] = None) -> Optional[Dict]:
    if not os.path.isdir(DATASET_DIR):
        return None

    if filename:
        filepath = os.path.join(DATASET_DIR, filename)
        if not os.path.isfile(filepath):
            return None
        parsed = parse_homework_file(filepath)
        files = sorted(f for f in os.listdir(DATASET_DIR) if f.endswith(".md"))
        parsed["id"] = files.index(filename) + 1 if filename in files else 0
        return parsed

    if file_id is not None:
        files = sorted(f for f in os.listdir(DATASET_DIR) if f.endswith(".md"))
        if file_id < 1 or file_id > len(files):
            return None
        filepath = os.path.join(DATASET_DIR, files[file_id - 1])
        parsed = parse_homework_file(filepath)
        parsed["id"] = file_id
        return parsed

    return None


def get_dataset_file_path(filename: str) -> Optional[str]:
    filepath = os.path.join(DATASET_DIR, filename)
    return filepath if os.path.isfile(filepath) else None
