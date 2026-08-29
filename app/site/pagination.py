"""Generic pagination helper used by every listing page."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    page_number: int
    total_pages: int

    @property
    def has_previous(self) -> bool:
        return self.page_number > 1

    @property
    def has_next(self) -> bool:
        return self.page_number < self.total_pages

    @property
    def previous_page(self) -> int:
        return self.page_number - 1

    @property
    def next_page(self) -> int:
        return self.page_number + 1


def paginate[T](items: Sequence[T], per_page: int) -> list[Page[T]]:
    if per_page <= 0:
        per_page = len(items) or 1
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    pages = []
    for page_number in range(1, total_pages + 1):
        start = (page_number - 1) * per_page
        chunk = list(items[start : start + per_page])
        pages.append(Page(items=chunk, page_number=page_number, total_pages=total_pages))
    return pages
