"""用量汇总：历史调用和错题本要能按模块分开。"""
import usage_stats


def _row(feature, tokens, teacher_id=None, task_meta=None, call_id="c"):
    meta = dict(task_meta or {})
    if teacher_id is not None:
        meta["teacher_id"] = teacher_id
    return usage_stats._slim_record({
        "call_id": call_id,
        "feature": feature,
        "task_meta": meta,
        "success": True,
        "elapsed_seconds": 1,
        "ts_utc": "2026-09-26T00:00:00Z",
        "usage": {"prompt_tokens": 1, "completion_tokens": tokens - 1, "total_tokens": tokens},
    }, "mem")


def test_notebook_calls_are_their_own_module():
    rows = [
        _row("ocr", 10, 3, {"feature_source": "notebook"}, "n1"),
        _row("variant", 7, 3, {"wrong_question_id": 9}, "n2"),
        _row("grade", 20, call_id="g1"),
        _row("probe", 4, call_id="p1"),
    ]
    summary = usage_stats.summarize(rows)
    modules = {item["module"]: item for item in summary["by_module"]}
    assert modules["notebook"]["calls"] == 2
    assert modules["notebook"]["total_tokens"] == 17
    assert modules["grade"]["total_tokens"] == 20
    assert modules["ocr"]["calls"] == 0
    assert modules["lessonplan"]["calls"] == 0
    assert summary["overview"]["calls"] == 4
    assert summary["overview"]["total_tokens"] == 41

    teachers = {item["teacher_id"]: item for item in summary["by_teacher"]}
    assert teachers[None]["modules"]["grade"]["calls"] == 1
    assert teachers[None]["modules"]["probe"]["total_tokens"] == 4
    assert teachers[3]["modules"]["notebook"]["calls"] == 2


def test_module_totals_match_overview_when_logs_exist():
    usage_stats.clear_cache()
    records = usage_stats.load_call_records(usage_stats.default_log_root())
    if not records:
        return
    summary = usage_stats.summarize(records)
    assert summary["overview"]["total_tokens"] == sum(item["total_tokens"] for item in summary["by_module"])
    unassigned = [item for item in summary["by_teacher"] if item["teacher_id"] is None]
    if unassigned:
        row = unassigned[0]
        assert sum(item["calls"] for item in row["modules"].values()) == row["calls"]
