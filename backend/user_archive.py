"""把老师生成的教案、批改和变式题按登录账号留一份文件。

目录：
  {USER_RECORDS_DIR}/{账号}/lessonplan/lessonplan-{id}.json
  {USER_RECORDS_DIR}/{账号}/grade/grade-{id}.json
  {USER_RECORDS_DIR}/{账号}/variant/variant-{id}.json

用户后来在自己的页面里删除，这里的副本仍然保留，供管理员查看。
"""
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

KINDS = ("lessonplan", "grade", "variant")
_NAME_RE = re.compile(r"^(lessonplan|grade|variant)-\d+\.json$")
_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def records_root() -> Path:
    from config import settings
    root = Path(settings.USER_RECORDS_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def account_dirname(username: str) -> str:
    """账号名做成文件夹名。去掉路径符号，避免写到目录外面。"""
    raw = (username or "").strip()
    cleaned = re.sub(r"[^\w.\-]+", "_", raw, flags=re.UNICODE).strip("._")
    if not cleaned or cleaned in {".", ".."}:
        return "unknown"
    return cleaned[:80]


def _account_dir(username: str) -> Path:
    root = records_root().resolve()
    folder = (root / account_dirname(username)).resolve()
    if folder.parent != root:
        raise ValueError("账号目录不合法")
    return folder


def _saved_at_text(value: Any = None) -> str:
    """写成服务器本地时间，日期才能和用量页的「按日期」对齐。"""
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.astimezone().replace(microsecond=0).isoformat(timespec="seconds")
    text = str(value or "").strip()
    if len(text) >= 19 and text[4] == "-" and text[7] == "-":
        return text[:19]
    return datetime.now().astimezone().replace(microsecond=0).isoformat(timespec="seconds")


def save_record(
    username: str,
    display_name: str,
    kind: str,
    record_id: int,
    title: str,
    body: Any,
    extra: Optional[Dict[str, Any]] = None,
    saved_at: Any = None,
) -> Path:
    if kind not in KINDS:
        raise ValueError(f"未知记录类型：{kind}")
    folder = _account_dir(username) / kind
    folder.mkdir(parents=True, exist_ok=True)
    when = _saved_at_text(saved_at)
    payload = {
        "kind": kind,
        "id": int(record_id),
        "username": username,
        "display_name": display_name or username,
        "title": title or "",
        "saved_at": when,
        "body": body,
    }
    if extra:
        payload["extra"] = extra
    path = folder / f"{kind}-{int(record_id)}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        stamp = datetime.fromisoformat(when).timestamp()
        os.utime(path, (stamp, stamp))
    except (OSError, ValueError):
        pass
    return path


def _safe_file(username: str, kind: str, name: str) -> Path:
    if kind not in KINDS or not _NAME_RE.fullmatch(name or "") or not name.startswith(kind + "-"):
        raise ValueError("记录不存在")
    folder = _account_dir(username)
    path = (folder / kind / name).resolve()
    if path.parent != (folder / kind).resolve():
        raise ValueError("记录不存在")
    return path


def list_accounts() -> List[Dict[str, Any]]:
    root = records_root().resolve()
    items = []
    if not root.is_dir():
        return items
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        counts = {}
        for kind in KINDS:
            kind_dir = entry / kind
            counts[kind] = len(list(kind_dir.glob(f"{kind}-*.json"))) if kind_dir.is_dir() else 0
        if not any(counts.values()):
            continue
        items.append({"username": entry.name, "counts": counts})
    return items


def list_records(username: str) -> List[Dict[str, Any]]:
    folder = _account_dir(username)
    if not folder.is_dir():
        return []
    items = []
    for kind in KINDS:
        kind_dir = folder / kind
        if not kind_dir.is_dir():
            continue
        for path in sorted(kind_dir.glob(f"{kind}-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            items.append({
                "kind": kind,
                "id": data.get("id"),
                "name": path.name,
                "title": data.get("title") or "",
                "display_name": data.get("display_name") or "",
                "saved_at": data.get("saved_at") or "",
                "bytes": path.stat().st_size,
            })
    return items


def read_record(username: str, kind: str, name: str) -> Dict[str, Any]:
    path = record_path(username, kind, name)
    return json.loads(path.read_text(encoding="utf-8"))


def record_path(username: str, kind: str, name: str) -> Path:
    path = _safe_file(username, kind, name)
    if not path.is_file():
        raise FileNotFoundError(name)
    return path


def _saved_day(path: Path) -> str:
    """优先用文件里的 saved_at 日期，读不到时用文件修改时间。"""
    try:
        head = path.read_text(encoding="utf-8")[:500]
    except OSError:
        head = ""
    matched = re.search(r'"saved_at"\s*:\s*"(\d{4}-\d{2}-\d{2})', head)
    if matched:
        return matched.group(1)
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def _walk_records():
    root = records_root().resolve()
    if not root.is_dir():
        return
    for account in sorted(root.iterdir(), key=lambda p: p.name):
        if not account.is_dir():
            continue
        for kind in KINDS:
            kind_dir = account / kind
            if not kind_dir.is_dir():
                continue
            for path in sorted(kind_dir.glob(f"{kind}-*.json")):
                if path.is_file() and _NAME_RE.fullmatch(path.name):
                    yield account.name, kind, path


def count_by_day() -> List[Dict[str, int]]:
    """每个日期留存了多少份用户文件。"""
    counts: Dict[str, Dict[str, int]] = {}
    for _username, kind, path in _walk_records():
        day = _saved_day(path)
        row = counts.setdefault(day, {"day": day, "files": 0, "lessonplan": 0, "grade": 0, "variant": 0})
        row["files"] += 1
        row[kind] += 1
    return [counts[day] for day in sorted(counts)]


def record_markdown(data: Dict[str, Any]) -> str:
    """把留存 JSON 转成可以直接打开的正文。教案用 body，批改写成学生、得分和逐题对错。"""
    kind = data.get("kind") or ""
    body = data.get("body")
    title = str(data.get("title") or "").strip()
    if kind == "lessonplan" and isinstance(body, str):
        return body if body.endswith("\n") else body + "\n"
    if kind == "grade" and isinstance(body, dict):
        grading = body.get("grading_result") if isinstance(body.get("grading_result"), dict) else {}
        questions = grading.get("questions") if isinstance(grading.get("questions"), list) else []
        score = body.get("score")
        wrong = body.get("wrong_count")
        lines = [
            f"# {title or '批改'}",
            "",
            f"- 学生：{body.get('student_name') or '学生'}",
            f"- 学科：{body.get('subject') or ''}",
            f"- 得分：{'—' if score is None else score}",
            f"- 错题：{'—' if wrong is None else wrong}",
            "",
        ]
        for index, question in enumerate(questions, 1):
            if not isinstance(question, dict):
                continue
            mark = "正确" if question.get("is_correct") else "错误"
            number = question.get("question_number") or index
            lines.append(f"## 第 {number} 题 · {mark}")
            if question.get("question_text"):
                lines.append(str(question["question_text"]))
            if question.get("student_answer"):
                lines.append(f"学生答案：{question['student_answer']}")
            if question.get("correct_answer"):
                lines.append(f"参考答案：{question['correct_answer']}")
            lines.append("")
        return "\n".join(lines)
    if isinstance(body, str):
        return body if body.endswith("\n") else body + "\n"
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _add_record_to_zip(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    archive.write(path, arcname=arcname)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    markdown_name = arcname[:-5] + ".md" if arcname.endswith(".json") else arcname + ".md"
    archive.writestr(markdown_name, record_markdown(data))


def zip_by_days(days: List[str]) -> bytes:
    """把选中日期的用户文件打成一个 zip，按 日期/账号/类型/文件名 存放。"""
    wanted = []
    for day in days:
        day = (day or "").strip()
        if not _DAY_RE.fullmatch(day):
            raise ValueError("日期格式应为 YYYY-MM-DD")
        if day not in wanted:
            wanted.append(day)
    if not wanted:
        raise ValueError("请选择日期")
    if len(wanted) > 366:
        raise ValueError("一次最多下载 366 天")
    wanted_set = set(wanted)
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for username, kind, path in _walk_records():
            day = _saved_day(path)
            if day not in wanted_set:
                continue
            _add_record_to_zip(archive, path, f"{day}/{username}/{kind}/{path.name}")
            count += 1
    if count == 0:
        raise FileNotFoundError("这些日期没有留存文件")
    return buf.getvalue()


def account_zip(username: str) -> bytes:
    """把一个账号目录打成 zip。只收规定文件名，避免把目录外的内容带出去。"""
    folder = _account_dir(username)
    if not folder.is_dir():
        raise FileNotFoundError(username)
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for kind in KINDS:
            kind_dir = folder / kind
            if not kind_dir.is_dir():
                continue
            for path in sorted(kind_dir.glob(f"{kind}-*.json")):
                if path.is_file() and _NAME_RE.fullmatch(path.name):
                    _add_record_to_zip(archive, path, f"{kind}/{path.name}")
                    count += 1
    if count == 0:
        raise FileNotFoundError(username)
    return buf.getvalue()
