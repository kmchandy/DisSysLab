# dsl/block_lib/sources/source_lib/common_classes.py
from __future__ import annotations
import time
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_sources import (
    gen_list,
    gen_list_with_delay,
    gen_list_as_key,
    gen_list_as_key_with_time,
    gen_file_lines,
    gen_file_lines_as_key,
    gen_file_lines_as_key_with_time,
    gen_csv_dicts,
    gen_numpy_rows,
    gen_rss_headlines,
    generate_random_integers,
)

# Public API
__all__ = [
    "FromList",
    "FromListDelay",
    "FromListWithKey",
    "FromListWithKeyWithTime",
    "FromFile",
    "FromFileWithKey",
    "FromFileWithKeyWithTime",
    "FromCSV",
    "FromNumpyRows",
    "FromRSS",
]


class FromList(Source):
    """Source wrapper for gen_list(items)."""

    def __init__(self, items):
        super().__init__(generator_fn=gen_list(items))


class FromListDelay(Source):
    """Source wrapper for gen_list_with_delay(items, delay)."""

    def __init__(self, items, delay):
        super().__init__(generator_fn=gen_list_with_delay(items, delay))


class FromListWithKey(Source):
    """Source wrapper for FromListWithKey(items, key)."""

    def __init__(self, items, key: str):
        super().__init__(generator_fn=gen_list_as_key(items, key))


class FromListWithKeyWithTime(Source):
    def __init__(self, items, key: str, time_key: str = "time"):
        super().__init__(generator_fn=gen_list_as_key_with_time(
            items, key, time_key))


class FromFile(Source):
    """Source wrapper for FromFile(path, encoding)."""

    def __init__(self, path: str, encoding: str = "utf-8"):
        super().__init__(generator_fn=gen_file_lines(path, encoding))


class FromFileWithKey(Source):
    """Source wrapper for FromFileWithKey(path, key, encoding)."""

    def __init__(self, path: str, key: str, encoding: str = "utf-8"):
        super().__init__(generator_fn=gen_file_lines_as_key(path, key, encoding))


class FromFileWithKeyWithTime(Source):
    def __init__(self, path: str, key: str, time_key: str = "time", encoding: str = "utf-8"):
        super().__init__(generator_fn=gen_file_lines_as_key_with_time(
            path, key, time_key, encoding))


class FromCSV(Source):
    """Source wrapper for FromCSV(path, encoding)."""

    def __init__(self, path: str, encoding: str = "utf-8"):
        super().__init__(generator_fn=gen_csv_dicts(path, encoding))


class FromNumpyRows(Source):
    """Source wrapper for FromNumpyRows(array)."""

    def __init__(self, array):
        super().__init__(generator_fn=gen_numpy_rows(array))


class FromRSS(Source):
    """Source wrapper for FromRSS(url, interval, limit, sleep, parser)."""

    def __init__(self, url: str, interval: float = 5.0, limit: int | None = None,
                 sleep: callable = time.sleep, parser=None):
        super().__init__(generator_fn=gen_rss_headlines(
            url, interval, limit, sleep=sleep, parser=parser))


class FromRandomIntegers(Source):
    """Source wrapper for FromRandomIntegers(N, LOW, HIGH)."""

    def __init__(self, N: int, LOW: int, HIGH: int):
        super().__init__(generator_fn=generate_random_integers(N, LOW, HIGH))
