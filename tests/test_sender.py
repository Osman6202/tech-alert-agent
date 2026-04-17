import pytest
from unittest.mock import patch, MagicMock


def test_send_message_posts_to_telegram():
    with patch("sender.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(is_success=True)
        from sender import send_message
        result = send_message("Hello Telegram")
    assert result is True
    assert mock_post.called
    call_kwargs = mock_post.call_args[1]["json"]
    assert call_kwargs["text"] == "Hello Telegram"
    assert call_kwargs["parse_mode"] == "HTML"


def test_send_message_retries_on_failure():
    with patch("sender.httpx.post") as mock_post:
        mock_post.side_effect = [
            Exception("network error"),
            MagicMock(is_success=True),
        ]
        with patch("sender.time.sleep"):
            from sender import send_message
            result = send_message("Retry test")
    assert result is True
    assert mock_post.call_count == 2


def test_send_messages_sends_all_parts():
    with patch("sender.send_message") as mock_send:
        mock_send.return_value = True
        from sender import send_messages
        send_messages(["part1", "part2", "part3"])
    assert mock_send.call_count == 3
