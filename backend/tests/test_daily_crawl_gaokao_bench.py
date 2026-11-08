"""GAOKAO-Bench 开放源：题干前缀剥除、字段映射、走 filter_new_rows 管道。"""
from __future__ import annotations

import json
from pathlib import Path

from crawler.daily_crawl import (
    OPEN_REPOS,
    SourceStats,
    _GITHUB_SKIP_DIRS,
    filter_new_rows,
)
from import_open_math import (
    GAOKAO_BENCH_FILES,
    GAOKAO_BENCH_REPO,
    gaokao_bench_file_records,
    gaokao_bench_records,
    strip_gaokao_question_prefix,
)


# 截短的真实样例（来自 2010-2022_Math_I_Open-ended_Questions.json 首条）
OPEN_SAMPLE = {
    "year": "2010",
    "category": "（新课标）",
    "question": (
        "17. (12 分) 设数列满足 $a_{1}=2, a_{n+1}-a_{n}=3 \\cdot 2^{2 n-1}$\n\n"
        "（1）求数列 $\\left\\{a_{n}\\right\\}$ 的通项公式;\n"
    ),
    "answer": "解： ( I ) 由已知, 当 $n \\geqslant 1$ 时, $a_{n}=2^{2 n-1}$.\n",
    "analysis": "（I）由题意得数列 $\\left\\{a_{n}\\right\\}$ 的通项公式为 $a_{n}=2^{2 n-1}$.\n",
    "index": 0,
    "score": 12,
}

MCQ_SAMPLE = {
    "year": "2010",
    "category": "（新课标）",
    "question": (
        "1. （5 分) 已知集合 $A=\\{x \\in R|| x \\mid \\leqslant 2\\}$，则 $A \\cap B=(\\quad$ ）\n"
        "A. $(0,2)$\nB. $[0,2]$\nC. $\\{0,2\\}$\nD. $\\{0,1,2\\}$\n"
    ),
    "answer": ["D"],
    "analysis": "故 $A \\cap B=\\{0,1,2\\}$. 应选 D.\n",
    "index": 0,
    "score": 5,
}

DIRTY_HTM = (
    "7006319. htm下文是2024年北京高考各科试卷及答案解析："
    "请考生结合自身情况合理安排复习。"
)


def _write_gaokao_json(path: Path, examples: list[dict]) -> None:
    path.write_text(
        json.dumps({"keywords": path.stem, "example": examples}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_strip_gaokao_prefix_real_open_ended():
    text = strip_gaokao_question_prefix(OPEN_SAMPLE["question"])
    assert text.startswith("设数列")
    assert "12 分" not in text[:20]


def test_strip_gaokao_prefix_idempotent():
    clean = "设数列满足 $a_{1}=2$"
    assert strip_gaokao_question_prefix(clean) == clean
    once = strip_gaokao_question_prefix(OPEN_SAMPLE["question"])
    assert strip_gaokao_question_prefix(once) == once


def test_gaokao_bench_open_ended_mapping(tmp_path: Path):
    remote = "Data/Subjective_Questions/2010-2022_Math_I_Open-ended_Questions.json"
    path = tmp_path / "2010-2022_Math_I_Open-ended_Questions.json"
    _write_gaokao_json(path, [OPEN_SAMPLE])

    rows = gaokao_bench_file_records(
        path, remote_path=remote, question_type="解答题"
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["question_type"] == "解答题"
    assert row["education_level"] == "高中"
    assert row["exam_type"] == "高考"
    assert row["subject"] == "数学"
    assert row["year"] == 2010
    assert row["region"] == "新课标"
    assert row["grade"] is None
    assert row["difficulty"] == 3
    assert row["score"] == 12
    assert row["knowledge_points"] == []
    assert row["question_text"].startswith("设数列")
    assert row["answer"].startswith("解：")
    assert "通项公式" in row["solution"]
    assert row["source_url"] == f"{GAOKAO_BENCH_REPO}/blob/main/{remote}#q0"


def test_gaokao_bench_mcq_answer_list(tmp_path: Path):
    remote = "Data/Objective_Questions/2010-2022_Math_I_MCQs.json"
    path = tmp_path / "2010-2022_Math_I_MCQs.json"
    _write_gaokao_json(path, [MCQ_SAMPLE])

    rows = gaokao_bench_file_records(
        path, remote_path=remote, question_type="选择题"
    )
    assert len(rows) == 1
    assert rows[0]["question_type"] == "选择题"
    assert rows[0]["answer"] == "D"
    assert rows[0]["question_text"].startswith("已知集合")


def test_gaokao_bench_records_from_dir(tmp_path: Path):
    for spec in GAOKAO_BENCH_FILES:
        examples = []
        if "Open-ended" in spec["local"]:
            examples = [dict(OPEN_SAMPLE, index=0)]
        elif "MCQ" in spec["local"]:
            examples = [dict(MCQ_SAMPLE, index=0)]
        else:
            examples = [{
                "year": "2010",
                "category": "（新课标）",
                "question": "13. (5 分) 设 $y=f(x)$ 为区间上的连续函数，则积分为\n",
                "answer": "$\\frac{N_1}{N}$\n",
                "analysis": "由频率估计概率。\n",
                "index": 0,
                "score": 5,
            }]
        _write_gaokao_json(tmp_path / spec["local"], examples)

    rows = gaokao_bench_records(tmp_path)
    assert len(rows) == 6
    types = {r["question_type"] for r in rows}
    assert types == {"选择题", "填空题", "解答题"}
    assert all(r["exam_type"] == "高考" for r in rows)
    assert all(r["education_level"] == "高中" for r in rows)


def test_open_repos_registers_gaokao_bench():
    keys = [spec["key"] for spec in OPEN_REPOS]
    assert "gaokao-bench" in keys
    bench = next(spec for spec in OPEN_REPOS if spec["key"] == "gaokao-bench")
    assert bench["repo"] == "OpenLMLab/GAOKAO-Bench"
    locals_ = [f["local"] for f in bench["files"]]
    assert len(locals_) == 6
    assert "2010-2022_Math_I_Open-ended_Questions.json" in locals_
    assert "Data" not in _GITHUB_SKIP_DIRS
    assert "Objective_Questions" not in _GITHUB_SKIP_DIRS
    assert "Subjective_Questions" not in _GITHUB_SKIP_DIRS


def test_gaokao_records_pass_filter_new_rows(tmp_path: Path):
    remote = "Data/Subjective_Questions/2010-2022_Math_I_Open-ended_Questions.json"
    path = tmp_path / "open.json"
    dirty = {
        "year": "2010",
        "category": "（新课标）",
        "question": DIRTY_HTM,
        "answer": "无",
        "analysis": "",
        "index": 99,
        "score": 0,
    }
    _write_gaokao_json(path, [OPEN_SAMPLE, dirty])
    records = gaokao_bench_file_records(
        path, remote_path=remote, question_type="解答题"
    )
    # 脏样例无题号前缀时仍保留原文；两条都会进 records
    assert len(records) == 2

    cleaned = []
    for row in records:
        row = dict(row)
        row.pop("_file", None)
        cleaned.append(row)

    stats = SourceStats()
    fresh = filter_new_rows(
        cleaned,
        existing_urls=set(),
        existing_hashes=set(),
        night_new_total=0,
        stats=stats,
    )
    assert len(fresh) == 1
    assert fresh[0]["question_text"].startswith("设数列")
    assert stats.dirty == 1
    assert stats.dup == 0
