"""Tests for automations/delivery.py"""
from pathlib import Path
import json
import pytest
from unittest.mock import patch, Mock
from requests import ConnectionError
from requests.exceptions import Timeout

from automations.delivery import send_whatsapp, enqueue_pending, retry_pending


class TestSendWhatsApp:
    def test_sends_post_to_bridge(self):
        with patch("automations.delivery.requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = send_whatsapp("hello", "+5511999999999")
            assert result is True
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert "http://localhost:8080/api/send" in args[0]
            assert kwargs["json"]["recipient"] == "+5511999999999"
            assert kwargs["json"]["message"] == "hello"

    def test_returns_false_on_connection_error(self):
        with patch("automations.delivery.requests.post") as mock_post:
            mock_post.side_effect = ConnectionError()
            result = send_whatsapp("hello", "+5511999999999")
            assert result is False

    def test_returns_false_on_timeout(self):
        with patch("automations.delivery.requests.post") as mock_post:
            mock_post.side_effect = Timeout()
            result = send_whatsapp("hello", "+5511999999999")
            assert result is False

    def test_returns_false_on_http_error(self):
        with patch("automations.delivery.requests.post") as mock_post:
            mock_post.return_value.ok = False
            mock_post.return_value.status_code = 500
            result = send_whatsapp("hello", "+5511999999999")
            assert result is False

    def test_returns_false_on_empty_recipient(self):
        result = send_whatsapp("hello", "")
        assert result is False


class TestEnqueuePending:
    def test_writes_to_pending_file(self, tmp_path):
        with patch("automations.delivery.PENDING_FILE", tmp_path / "pending.json"):
            enqueue_pending("test msg", "+5511999999999")
            data = json.loads((tmp_path / "pending.json").read_text())
            assert len(data) == 1
            assert data[0]["text"] == "test msg"
            assert data[0]["retry_count"] == 0

    def test_appends_to_existing_pending(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "old", "recipient": "+55", "failed_at": "x", "retry_count": 0}]))
        with patch("automations.delivery.PENDING_FILE", pf):
            enqueue_pending("new msg", "+5511999999999")
            data = json.loads(pf.read_text())
            assert len(data) == 2

    def test_keeps_only_last_50(self, tmp_path):
        pf = tmp_path / "pending.json"
        old = [{"text": str(i), "recipient": "+55", "failed_at": "x", "retry_count": 0} for i in range(55)]
        pf.write_text(json.dumps(old))
        with patch("automations.delivery.PENDING_FILE", pf):
            enqueue_pending("newest", "+5511999999999")
            data = json.loads(pf.read_text())
            assert len(data) == 50
            assert data[-1]["text"] == "newest"


class TestRetryPending:
    def test_delivers_pending_and_removes(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "m1", "recipient": "+55", "failed_at": "x", "retry_count": 0}]))
        with patch("automations.delivery.PENDING_FILE", pf), \
             patch("automations.delivery.send_whatsapp", return_value=True):
            count = retry_pending()
            assert count == 1
            assert json.loads(pf.read_text()) == []

    def test_increments_retry_count_on_failure(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "m1", "recipient": "+55", "failed_at": "x", "retry_count": 0}]))
        with patch("automations.delivery.PENDING_FILE", pf), \
             patch("automations.delivery.send_whatsapp", return_value=False):
            count = retry_pending()
            assert count == 0
            data = json.loads(pf.read_text())
            assert data[0]["retry_count"] == 1

    def test_discards_after_3_retries(self, tmp_path):
        pf = tmp_path / "pending.json"
        pf.write_text(json.dumps([{"text": "m1", "recipient": "+55", "failed_at": "x", "retry_count": 3}]))
        with patch("automations.delivery.PENDING_FILE", pf), \
             patch("automations.delivery.send_whatsapp") as mock_send:
            count = retry_pending()
            assert count == 0
            mock_send.assert_not_called()
            assert json.loads(pf.read_text()) == []
