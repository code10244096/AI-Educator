"""模型 JSON 返回解析：容忍 ``` 围栏、前后杂质、LaTeX 反斜杠、字符串内裸换行/控制字符。"""
import pytest

from ai_client import parse_json_response


def test_plain_object():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_code_fence_and_prose():
    text = '好的，结果如下：\n```json\n{"total": 2}\n```\n希望对你有帮助。'
    assert parse_json_response(text) == {"total": 2}


def test_latex_backslashes():
    text = r'{"q": "已知 \\( \\frac{a}{b} \\) 求值"}'
    out = parse_json_response(text)
    assert "\\frac" in out["q"]


def test_raw_newline_inside_string():
    """推理模型会把字符串直接断行（裸 \\n 而非 \\n 转义），strict=False 必须容忍。"""
    text = '{\n  "total_questions": 2,\n  "correct_count": \n1,\n  "questions": [\n    {\n      "question_number":\n 1,\n      "question_text": "第一行\n第二行。",\n      "is_correct": true\n    }\n  ]\n}'
    out = parse_json_response(text)
    assert out["total_questions"] == 2
    assert out["questions"][0]["question_text"] == "第一行\n第二行。"


def test_invalid_json_still_raises():
    with pytest.raises(Exception):
        parse_json_response('{"a": }')


def test_trailing_comma_fixed():
    assert parse_json_response('{"a": 1, "b": [1, 2,],}') == {"a": 1, "b": [1, 2]}


def test_truncated_array_repaired():
    """输出被掐断：截到最后一个完整成员并补括号。"""
    out = parse_json_response('{"total": 2, "questions": [{"q": 1}, {"q": 2},')
    assert out["total"] == 2
    assert out["questions"] == [{"q": 1}, {"q": 2}]


def test_missing_root_closer_repaired():
    assert parse_json_response('{"a": 1, "b": 2') == {"a": 1, "b": 2}


def test_salvage_grading_questions():
    """整体烂掉但题目块完好：逐题抢救，缺失字段由 normalize 补齐。"""
    from ai_client import salvage_grading_questions
    raw = '''not json at all "questions": [
      {"question_number": 1, "question_text": "题一", "is_correct": true, "explanation": "\\frac{1}{2}"},
      {"question_number": 2, "question_text": "题二", "is_correct": false},
      残片'''
    out = salvage_grading_questions(raw)
    assert out is not None
    assert out["total_questions"] == 2
    assert out["correct_count"] == 1
    assert out["wrong_count"] == 1
    assert all(q["needs_review"] for q in out["questions"])
    assert salvage_grading_questions('{"nothing": "here"}') is None
