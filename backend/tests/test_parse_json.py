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
