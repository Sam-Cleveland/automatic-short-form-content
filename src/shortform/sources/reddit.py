"""Reddit post scraper.

Hits the Reddit JSON API directly (no OAuth) by appending `.json` to the post URL.
Retries automatically on 429 rate-limit responses.
"""

from __future__ import annotations

import logging
import time

import requests

from .base import Post

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}
_RETRY_WAIT = 3  # seconds to wait after a 429


def fetch(url: str) -> Post:
    """Fetch a Reddit post by URL. Retries once on 429."""
    clean_url = url.rstrip("/")
    resp = requests.get(clean_url + ".json", headers=_HEADERS, timeout=15)
    log.debug("GET %s → %d", clean_url, resp.status_code)

    if resp.status_code == 429:
        log.warning("Rate limited — waiting %ds before retry", _RETRY_WAIT)
        time.sleep(_RETRY_WAIT)
        return fetch(url)

    resp.raise_for_status()

    data = resp.json()[0]["data"]["children"][0]["data"]
    return Post(title=data["title"], body=data["selftext"])


class RedditSource:
    """Adapter wrapping the module-level `fetch` function."""

    def fetch(self, url: str) -> Post:
        return fetch(url)
