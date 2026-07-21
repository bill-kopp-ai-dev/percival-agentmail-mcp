"""Tests for the _normalize_list helper."""

import pytest

from percival_agentmail_mcp.helpers import normalize_list


@pytest.mark.parametrize(
    "val,expected",
    [
        (None, None),
        ("", []),
        ("a,b,c", ["a", "b", "c"]),
        ("a, b ,c", ["a", "b", "c"]),
        (["a", "b"], ["a", "b"]),
        ('["a","b"]', ["a", "b"]),
        ("single", ["single"]),
    ],
)
def test_normalize_list_basic_cases(val, expected):
    assert normalize_list(val) == expected


def test_normalize_list_invalid_json_string_passes_through():
    # Quando o JSON parsing falha, cai no split por vírgula
    assert normalize_list("[invalid") == ["[invalid"]


def test_normalize_list_coerces_int_items_to_str():
    assert normalize_list([1, 2, 3]) == ["1", "2", "3"]


def test_normalize_list_string_without_comma():
    assert normalize_list("hello world") == ["hello world"]


def test_normalize_list_unbalanced_bracket_preserves_input():
    """Regression: malformed JSON list preserves the original string."""
    assert normalize_list("[invalid") == ["[invalid"]


def test_normalize_list_malformed_json_preserves_input():
    """Regression: invalid JSON inside balanced brackets preserves the string."""
    assert normalize_list("[1, 2, 3") == ["[1, 2, 3"]


def test_normalize_list_json_object_preserves_input():
    """Regression: JSON object (not array) is preserved as a single string."""
    assert normalize_list('{"a": 1}') == ['{"a": 1}']
