from app.site.pagination import paginate


def test_paginate_splits_evenly() -> None:
    pages = paginate(list(range(10)), per_page=5)
    assert len(pages) == 2
    assert pages[0].items == [0, 1, 2, 3, 4]
    assert pages[1].items == [5, 6, 7, 8, 9]


def test_paginate_handles_remainder() -> None:
    pages = paginate(list(range(7)), per_page=3)
    assert [len(p.items) for p in pages] == [3, 3, 1]


def test_paginate_empty_list_yields_one_empty_page() -> None:
    empty: list[int] = []
    pages = paginate(empty, per_page=5)
    assert len(pages) == 1
    assert pages[0].items == []
    assert pages[0].total_pages == 1


def test_page_navigation_flags() -> None:
    pages = paginate(list(range(15)), per_page=5)
    assert not pages[0].has_previous
    assert pages[0].has_next
    assert pages[0].next_page == 2
    assert pages[-1].has_previous
    assert not pages[-1].has_next
    assert pages[-1].previous_page == 2
