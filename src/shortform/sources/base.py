from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Post:
    title: str
    body: str


class Source(Protocol):
    def fetch(self, url: str) -> Post: ...
