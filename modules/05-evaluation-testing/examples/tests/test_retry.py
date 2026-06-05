"""
Layer 2 — Retry contract tests.
No API calls — all model interactions are mocked.
Tests verify the documented promises of the retry logic in client.py.
"""
from unittest.mock import patch, call, MagicMock
import pytest
from triage.client import triage_ticket
from triage.models import SupportTicket


def _good_response(urgency="low"):
    mock = MagicMock()
    mock.text = f'{{"urgency": "{urgency}", "topic": "test", "reply": "OK."}}'
    return mock


@pytest.fixture(autouse=True)
def _patch_vertexai_init():
    with patch("triage.client.vertexai.init"):
        yield


def test_retries_exactly_three_times_on_persistent_failure():
    with patch("triage.client.GenerativeModel") as MockModel, \
         patch("triage.client.time.sleep"):
        MockModel.return_value.generate_content.side_effect = Exception("API error")
        with pytest.raises(RuntimeError, match="All 3 attempts failed"):
            triage_ticket(SupportTicket("Test", "Body"), project_id="test-project")
        assert MockModel.return_value.generate_content.call_count == 3


def test_backoff_delays_are_1_2_seconds():
    with patch("triage.client.GenerativeModel") as MockModel, \
         patch("triage.client.time.sleep") as mock_sleep:
        MockModel.return_value.generate_content.side_effect = Exception("API error")
        with pytest.raises(RuntimeError):
            triage_ticket(SupportTicket("Test", "Body"), project_id="test-project")
        assert mock_sleep.call_args_list == [call(1), call(2)]


def test_success_on_first_attempt_does_not_sleep():
    with patch("triage.client.GenerativeModel") as MockModel, \
         patch("triage.client.time.sleep") as mock_sleep:
        MockModel.return_value.generate_content.return_value = _good_response("high")
        result = triage_ticket(SupportTicket("Test", "Body"), project_id="test-project")
        assert result.urgency.value == "high"
        mock_sleep.assert_not_called()


def test_success_on_second_attempt_stops_retrying():
    with patch("triage.client.GenerativeModel") as MockModel, \
         patch("triage.client.time.sleep"):
        mock_gen = MockModel.return_value.generate_content
        mock_gen.side_effect = [Exception("first fail"), _good_response("medium")]
        result = triage_ticket(SupportTicket("Test", "Body"), project_id="test-project")
        assert result.urgency.value == "medium"
        assert mock_gen.call_count == 2


def test_runtime_error_wraps_original_exception():
    original = ValueError("quota exceeded")
    with patch("triage.client.GenerativeModel") as MockModel, \
         patch("triage.client.time.sleep"):
        MockModel.return_value.generate_content.side_effect = original
        with pytest.raises(RuntimeError) as exc_info:
            triage_ticket(SupportTicket("Test", "Body"), project_id="test-project")
        assert exc_info.value.__cause__ is original
