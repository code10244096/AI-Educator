"""下载第二批 MIT 数学开源题库到 dataset/题库/_原始下载/<数据集名>/。

仅使用标准库 + requests；已存在且非空的文件会跳过。某个数据集失败只打印原因并继续。
不要在本脚本里做规范化或入库。
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "题库" / "_原始下载"
UA = {"User-Agent": "ai-educator-fetch/1.0"}
TIMEOUT = 120
RETRIES = 2  # 超时后再试 2 次，合计最多 3 次

# (数据集目录名, 首选 zip URL 列表, 解压后需要保留的相对路径匹配)
DATASETS = {
    "TAL-SCQ5K": {
        "urls": [
            "https://github.com/math-eval/TAL-SCQ5K/archive/refs/heads/main.zip",
            "https://codeload.github.com/math-eval/TAL-SCQ5K/zip/refs/heads/main",
        ],
        # 只要中文 cn jsonl；英文跳过
        "keep": (
            "ch_single_choice_constructed_5K/ch_single_choice_train_3K.jsonl",
            "ch_single_choice_constructed_5K/ch_single_choice_test_2K.jsonl",
        ),
        "kind": "zip",
    },
    "ape210k": {
        "urls": [
            "https://github.com/Chenny0808/ape210k/archive/refs/heads/master.zip",
            "https://codeload.github.com/Chenny0808/ape210k/zip/refs/heads/master",
        ],
        "keep": (
            "data/train.ape.json",
            "data/valid.ape.json",
            "data/test.ape.json",
        ),
        "kind": "zip",
    },
    "math23k": {
        "urls": [
            "https://github.com/SCNU203/Math23k/archive/refs/heads/main.zip",
            "https://codeload.github.com/SCNU203/Math23k/zip/refs/heads/main",
        ],
        "keep": (
            "math23k_train.json",
            "math23k_test.json",
        ),
        "kind": "zip",
    },
}


def dest_dir(name: str) -> Path:
    path = RAW / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def already_have(name: str, keep: tuple[str, ...]) -> bool:
    folder = dest_dir(name)
    for rel in keep:
        target = folder / Path(rel).name
        if not target.exists() or target.stat().st_size <= 0:
            return False
    return True


def download_bytes(url: str) -> bytes:
    last_error = None
    attempts = RETRIES + 1
    for attempt in range(1, attempts + 1):
        try:
            print(f"  GET {url} (尝试 {attempt}/{attempts})", flush=True)
            resp = requests.get(url, headers=UA, timeout=TIMEOUT, stream=True)
            resp.raise_for_status()
            chunks = []
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    chunks.append(chunk)
            payload = b"".join(chunks)
            if not payload:
                raise RuntimeError("空响应")
            return payload
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError, RuntimeError) as err:
            last_error = err
            print(f"  失败 {type(err).__name__}: {err}", flush=True)
    raise RuntimeError(f"下载失败: {last_error}")


def match_keep(member: str, keep: tuple[str, ...]) -> str | None:
    """zip 内路径通常带仓库前缀，按后缀匹配 keep 相对路径。"""
    norm = member.replace("\\", "/")
    for rel in keep:
        if norm.endswith("/" + rel) or norm.endswith(rel):
            return Path(rel).name
    return None


def extract_keep(zip_bytes: bytes, name: str, keep: tuple[str, ...]) -> list[Path]:
    folder = dest_dir(name)
    saved: list[Path] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            out_name = match_keep(info.filename, keep)
            if not out_name:
                continue
            target = folder / out_name
            if target.exists() and target.stat().st_size > 0:
                print(f"  跳过已有 {target.name}", flush=True)
                saved.append(target)
                continue
            with zf.open(info) as src:
                data = src.read()
            target.write_bytes(data)
            print(f"  写出 {target.name} {len(data)} bytes", flush=True)
            saved.append(target)
    return saved


def count_entries(path: Path) -> int:
    """粗估条目数：jsonl 按非空行；json 数组按长度；jsonl-like 逐行 JSON。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return -1
    stripped = text.lstrip()
    if not stripped:
        return 0
    if stripped[0] == "[":
        try:
            return len(json.loads(text))
        except json.JSONDecodeError:
            return -1
    # jsonl 或 ape210k 每行一条 JSON
    count = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            count += 1
        except json.JSONDecodeError:
            # 少数文件是单行超大 JSON 对象序列；回退按换行粗算
            if line.startswith("{") or line.startswith("["):
                count += 1
    return count


def fetch_one(name: str, meta: dict) -> None:
    keep = meta["keep"]
    folder = dest_dir(name)
    print(f"\n=== {name} → {folder} ===", flush=True)
    if already_have(name, keep):
        print("已齐全，跳过下载", flush=True)
    else:
        last_err = None
        for url in meta["urls"]:
            try:
                payload = download_bytes(url)
                extract_keep(payload, name, keep)
                break
            except Exception as err:
                last_err = err
                print(f"URL 失败: {err}", flush=True)
        else:
            print(f"无法下载 {name}: {last_err}", flush=True)
            return

    for rel in keep:
        path = folder / Path(rel).name
        if not path.exists():
            print(f"缺失 {path.name}", flush=True)
            continue
        n = count_entries(path)
        size = path.stat().st_size
        print(f"文件 {path.name} size={size} entries≈{n}", flush=True)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, meta in DATASETS.items():
        try:
            fetch_one(name, meta)
        except Exception as err:
            print(f"数据集 {name} 异常，继续下一个: {type(err).__name__}: {err}", flush=True)
    print("\n全部处理结束（失败项见上方日志）", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
