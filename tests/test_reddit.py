"""Tests for shortform.sources.reddit — all HTTP is mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
import requests

from shortform.sources.reddit import RedditSource, fetch


def _make_response(status_code: int, json_body=None, text: str = "") -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


def _reddit_payload(title: str = "Test title", selftext: str = "Test body") -> list:
    return [{"data": {"children": [{"data": {"title": title, "selftext": selftext}}]}}]


class TestFetch:
    def test_returns_post_on_200(self):
        payload = _reddit_payload("My title", "My body")
        resp = _make_response(200, json_body=payload)
        with patch("shortform.sources.reddit.requests.get", return_value=resp):
            post = fetch("https://reddit.com/r/test/comments/abc/post")
        assert post.title == "My title"
        assert post.body == "My body"

    def test_appends_json_and_strips_trailing_slash(self):
        payload = _reddit_payload()
        resp = _make_response(200, json_body=payload)
        with patch("shortform.sources.reddit.requests.get", return_value=resp) as mock_get:
            fetch("https://reddit.com/r/test/comments/abc/post/")
        called_url = mock_get.call_args[0][0]
        assert called_url.endswith(".json")
        assert "//" not in called_url.replace("https://", "")

    def test_retries_once_on_429(self):
        payload = _reddit_payload()
        rate_limited = _make_response(429)
        ok = _make_response(200, json_body=payload)
        with patch("shortform.sources.reddit.requests.get", side_effect=[rate_limited, ok]):
            with patch("shortform.sources.reddit.time.sleep") as mock_sleep:
                post = fetch("https://reddit.com/r/test/comments/abc/")
        mock_sleep.assert_called_once()
        assert post.title == _reddit_payload()[0]["data"]["children"][0]["data"]["title"]

    def test_raises_on_404(self):
        resp = _make_response(404)
        with patch("shortform.sources.reddit.requests.get", return_value=resp):
            with pytest.raises(requests.HTTPError):
                fetch("https://reddit.com/r/test/comments/abc/")

    def test_raises_on_500(self):
        resp = _make_response(500)
        with patch("shortform.sources.reddit.requests.get", return_value=resp):
            with pytest.raises(requests.HTTPError):
                fetch("https://reddit.com/r/test/comments/abc/")


class TestRedditSource:
    def test_delegates_to_fetch(self):
        payload = _reddit_payload("Delegated title", "Delegated body")
        resp = _make_response(200, json_body=payload)
        source = RedditSource()
        with patch("shortform.sources.reddit.requests.get", return_value=resp):
            post = source.fetch("https://reddit.com/r/test/comments/abc/")
        assert post.title == "Delegated title"
