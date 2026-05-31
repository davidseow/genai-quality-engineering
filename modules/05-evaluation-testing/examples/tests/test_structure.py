import pytest
from triage.client import _parse
from triage.models import Urgency


def test_parse_valid_json():
    raw = '{"urgency": "high", "topic": "late delivery", "reply": "We are on it."}'
    result = _parse(raw)
    assert result.urgency == Urgency.HIGH
    assert result.topic == "late delivery"
    assert len(result.reply) > 0


def test_parse_strips_markdown_fences():
    raw = '```json\n{"urgency": "low", "topic": "feedback", "reply": "Thanks!"}\n```'
    result = _parse(raw)
    assert result.urgency == Urgency.LOW


def test_parse_raises_on_missing_key():
    raw = '{"urgency": "high", "topic": "missing reply"}'
    with pytest.raises((KeyError, Exception)):
        _parse(raw)


def test_parse_raises_on_bad_urgency():
    raw = '{"urgency": "critical", "topic": "x", "reply": "y"}'
    with pytest.raises((ValueError, KeyError)):
        _parse(raw)


def test_reply_not_excessively_long():
    raw = '{"urgency": "medium", "topic": "wrong item", "reply": "' + ("word " * 40).strip() + '"}'
    result = _parse(raw)
    assert len(result.reply.split()) <= 150
