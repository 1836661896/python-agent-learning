import pytest

from src.mcp.commands import parse_kv_args, parse_mcp_call


def test_parse_kv_basic_types():
    data = parse_kv_args("a=1 b=3.14 tool_succeeded=true name=tom")
    assert data == {"a": 1, "b": 3.14, "tool_succeeded": True, "name": "tom"}


def test_parse_kv_args_none_and_null():
    data = parse_kv_args("x=null y=none")
    assert data == {"x": None, "y": None}


def test_parse_kv_args_empty_payload():
    data = parse_kv_args("")
    assert data == {}


def test_parse_kv_args_invalid_token():
    with pytest.raises(ValueError, match="key=value"):
        parse_kv_args("a=1 wrong-token")


def test_parse_mcp_call_with_json_args():
    result = parse_mcp_call("调用mcp now tz=UTC retry=false")
    assert result == ("now", {"tz": "UTC", "retry": False})


def test_parse_kv_args_quoted_string():
    data = parse_kv_args('name="tom cat" city=shanghai')
    assert data == {"name": "tom cat", "city": "shanghai"}


def test_parse_kv_args_error_has_arg_index():
    with pytest.raises(ValueError, match="第2个参数格式错误"):
        parse_kv_args("a=1 wrong-token c=3")


def test_parse_kv_args_unclosed_quote_error():
    with pytest.raises(ValueError, match="参数引号格式错误"):
        parse_kv_args('name="tom cat age=18')


def test_parse_kv_args_duplicate_key_error():
    with pytest.raises(ValueError, match="参数重复"):
        parse_kv_args("a=1 a=2")
