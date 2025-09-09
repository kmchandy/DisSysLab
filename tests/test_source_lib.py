# tests/test_source_lib.py
# Simple, fast unit tests for dsl.block_lib.sources.gen_lib
# Keep them readable so students can tweak both code and tests.

from typing import List, Any, Dict
import dsl.block_lib.sources.source_lib.common_sources as S


# -------------------------
# gen_list / gen_list_as_key
# -------------------------
def test_gen_list_basic():
    gen = S.gen_list(["a", "b", "c"])
    assert list(gen()) == ["a", "b", "c"]


def test_gen_list_snapshot_not_affected_by_later_changes():
    items = ["x", "y"]
    gen = S.gen_list(items)
    items.append("z")  # change after building the generator
    assert list(gen()) == ["x", "y"]  # snapshot should be preserved


def test_gen_list_as_key_basic():
    gen = S.gen_list_as_key([1, 2], key="num")
    assert list(gen()) == [{"num": 1}, {"num": 2}]


def test_gen_list_as_key_with_time_uses_injected_now():
    gen = S.gen_list_as_key_with_time(["hi"], key="text", now=lambda: "TSTAMP")
    assert list(gen()) == [{"text": "hi", "time": "TSTAMP"}]


# -------------------------
# file line generators
# -------------------------
def test_gen_file_lines(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\n\nc\n")
    gen = S.gen_file_lines(str(p))
    assert list(gen()) == ["a", "b", "", "c"]


def test_gen_file_lines_as_key(tmp_path):
    p = tmp_path / "g.txt"
    p.write_text("one\ntwo\n")
    gen = S.gen_file_lines_as_key(str(p), key="line")
    assert list(gen()) == [{"line": "one"}, {"line": "two"}]


def test_gen_file_lines_as_key_with_time(tmp_path):
    p = tmp_path / "h.txt"
    p.write_text("L1\nL2\n")
    gen = S.gen_file_lines_as_key_with_time(
        str(p), key="text", now=lambda: "NOW")
    assert list(gen()) == [
        {"text": "L1", "time": "NOW"},
        {"text": "L2", "time": "NOW"},
    ]


# -------------------------
# CSV -> dicts
# -------------------------
def test_gen_csv_dicts(tmp_path):
    p = tmp_path / "people.csv"
    p.write_text("name,age\nAda,42\nAlan,41\n")
    gen = S.gen_csv_dicts(str(p))
    rows = list(gen())
    assert rows == [{"name": "Ada", "age": "42"},
                    {"name": "Alan", "age": "41"}]


# -------------------------
# NumPy rows (works with any iterable of rows)
# -------------------------
def test_gen_numpy_rows_with_list_of_lists():
    arr = [[1, 2], [3, 4]]
    gen = S.gen_numpy_rows(arr)
    assert list(gen()) == [[1, 2], [3, 4]]


# -------------------------
# RSS headlines (with fakes, no real sleep/parse)
# -------------------------
class SleepSpy:
    def __init__(self):
        self.calls: List[float] = []

    def __call__(self, seconds: float):
        self.calls.append(seconds)


class FeedObj:
    def __init__(self, entries: List[Dict[str, Any]], href: str = None):
        self.entries = entries
        if href:
            self.href = href


def test_gen_rss_headlines_limit_two_no_sleep_needed():
    # Parser returns two items immediately; limit=2 means no loop/sleep.
    def parser(_url: str):
        return FeedObj([{"title": "A"}, {"title": "B"}])

    sleep = SleepSpy()
    gen = S.gen_rss_headlines("http://example.com/feed", limit=2, interval=99,
                              parser=parser, sleep=sleep)
    out = list(gen())
    assert out == [
        {"text": "A", "source": "http://example.com/feed"},
        {"text": "B", "source": "http://example.com/feed"},
    ]
    assert sleep.calls == []  # returned before any sleep


def test_gen_rss_headlines_sleeps_when_no_new_items_then_yields():
    # First call: no entries -> must sleep; Second call: one new entry -> hits limit=1.
    calls = {"n": 0}

    def parser(_url: str):
        calls["n"] += 1
        if calls["n"] == 1:
            return FeedObj([])  # nothing yet
        return FeedObj([{"title": "X"}])  # second poll has a new title

    sleep = SleepSpy()
    gen = S.gen_rss_headlines("http://example.com/feed", limit=1, interval=0.5,
                              parser=parser, sleep=sleep)
    out = list(gen())
    assert out == [{"text": "X", "source": "http://example.com/feed"}]
    # One sleep occurred between the two polls
    assert sleep.calls == [0.5]


def test_gen_rss_headlines_skips_duplicates():
    # Parser always returns same two titles; limit=1 so we should stop after first title.
    def parser(_url: str):
        return FeedObj([{"title": "Same"}, {"title": "Same"}])

    sleep = SleepSpy()
    gen = S.gen_rss_headlines("http://example.com/feed", limit=1, interval=1.0,
                              parser=parser, sleep=sleep)
    out = list(gen())
    assert out == [{"text": "Same", "source": "http://example.com/feed"}]
