"""下载第三批开源题库（round4 导入脚本的原始数据）。

- ChinaTextbookStudyFree（MIT）：只要 output/{chinese,math,english,science}/quizzes/，
  保留相对路径（round4 按目录结构遍历）。
- TAL-SCQ5K-EN（MIT）：TAL 仓库的英文卷 jsonl。
- cmath（数据集 CC BY 4.0）：datasets/cmath_dev.jsonl（distractor 为对抗样本，不入题库）。

复用 fetch_datasets 的下载/计数工具；某个数据集失败只打印原因并继续。
已存在且非空的文件会跳过（幂等）。
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_datasets import RAW, count_entries, download_bytes  # noqa: E402

DATASETS = {
    "ChinaTextbookStudyFree": {
        "urls": [
            "https://github.com/wuwangzhang1216/ChinaTextbookStudyFree/archive/refs/heads/main.zip",
            "https://codeload.github.com/wuwangzhang1216/ChinaTextbookStudyFree/zip/refs/heads/main",
        ],
        "prefix": "ChinaTextbookStudyFree-main/",
        "keep_prefix": "output/",  # 保留 output/ 下的相对路径
    },
    "TAL-SCQ5K-EN": {
        "urls": [
            "https://github.com/math-eval/TAL-SCQ5K/archive/refs/heads/main.zip",
            "https://codeload.github.com/math-eval/TAL-SCQ5K/zip/refs/heads/main",
        ],
        "prefix": "TAL-SCQ5K-main/",
        "keep_prefix": None,  # 按文件名后缀匹配
        "keep_names": ("en_single_choice_train_3K.jsonl", "en_single_choice_test_2K.jsonl"),
    },
    "cmath": {
        "urls": [
            "https://github.com/XiaoMi/cmath/archive/refs/heads/main.zip",
            "https://codeload.github.com/XiaoMi/cmath/zip/refs/heads/main",
        ],
        "prefix": "cmath-main/",
        "keep_prefix": "datasets/",
    },
}


def wanted(name: str, meta: dict, member: str) -> str | None:
    norm = member.replace("\\", "/")
    if norm.endswith("/"):
        return None
    if not norm.startswith(meta["prefix"]):
        return None
    rel = norm[len(meta["prefix"]):]
    if meta.get("keep_prefix"):
        if rel.startswith(meta["keep_prefix"]):
            return rel
        return None
    for keep in meta.get("keep_names") or ():
        if rel.endswith("/" + keep) or rel == keep:
            return Path(rel).name
    return None


def fetch_one(name: str, meta: dict) -> None:
    folder = RAW / name
    folder.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {name} → {folder} ===", flush=True)
    last_err = None
    payload = None
    for url in meta["urls"]:
        try:
            payload = download_bytes(url)
            break
        except Exception as err:  # noqa: BLE001
            last_err = err
            print(f"URL 失败: {err}", flush=True)
    if payload is None:
        print(f"无法下载 {name}: {last_err}", flush=True)
        return
    n_files, n_new = 0, 0
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for info in zf.infolist():
            rel = wanted(name, meta, info.filename)
            if not rel:
                continue
            target = folder / rel
            n_files += 1
            if target.exists() and target.stat().st_size > 0:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src:
                target.write_bytes(src.read())
            n_new += 1
    print(f"匹配文件 {n_files} 个，新写出 {n_new} 个", flush=True)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, meta in DATASETS.items():
        try:
            fetch_one(name, meta)
        except Exception as err:  # noqa: BLE001
            print(f"数据集 {name} 异常，继续下一个: {type(err).__name__}: {err}", flush=True)
    # 统计入库相关文件
    csf = RAW / "ChinaTextbookStudyFree" / "output"
    if csf.is_dir():
        for subject in ("chinese", "math", "english", "science"):
            files = list((csf / subject / "quizzes").glob("*.json")) if (csf / subject / "quizzes").is_dir() else []
            print(f"ChinaTextbookStudyFree/{subject}: {len(files)} 个 quiz 文件", flush=True)
    for name, pattern in (("TAL-SCQ5K-EN", "*.jsonl"), ("cmath", "**/cmath_dev.jsonl")):
        for path in sorted((RAW / name).glob(pattern)):
            print(f"{name}/{path.name} size={path.stat().st_size} entries≈{count_entries(path)}", flush=True)
    print("\n全部处理结束（失败项见上方日志）", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
