# dsl/block_lib/sources/source_lib/common_classes.py
from __future__ import annotations
import time
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_sources import (
    gen_list,
    gen_list_as_key,
    gen_list_as_key_with_time,
    gen_file_lines,
    gen_file_lines_as_key,
    gen_file_lines_as_key_with_time,
    gen_csv_dicts,
    gen_numpy_rows,
    gen_rss_headlines,
)

# Public API
__all__ = [
    "GEN_LIST",
    "GEN_LIST_AS_KEY",
    "GEN_LIST_AS_KEY_WITH_TIME",
    "GEN_FILE_LINES",
    "GEN_FILE_LINES_AS_KEY",
    "GEN_FILE_LINES_AS_KEY_WITH_TIME",
    "GEN_CSV_DICTS",
    "GEN_NUMPY_ROWS",
    "GEN_RSS_HEADLINES",
]


class GEN_LIST(Source):
    """Source wrapper for gen_list(items)."""

    def __init__(self, items, name: str = "FromList"):
        super().__init__(generator_fn=gen_list(items), name=name)


class GEN_LIST_AS_KEY(Source):
    """Source wrapper for gen_list_as_key(items, key)."""

    def __init__(self, items, key: str, name: str = "FromListAddKey"):
        super().__init__(generator_fn=gen_list_as_key(items, key), name=name)


class GEN_LIST_AS_KEY_WITH_TIME(Source):
    def __init__(self, items, key: str, time_key: str = "time", name: str = "FromListAddKeyWithTime"):
        super().__init__(generator_fn=gen_list_as_key_with_time(
            items, key, time_key), name=name)


class GEN_FILE_LINES(Source):
    """Source wrapper for gen_file_lines(path, encoding)."""

    def __init__(self, path: str, encoding: str = "utf-8", name: str = "FromFileLines"):
        super().__init__(generator_fn=gen_file_lines(path, encoding), name=name)


class GEN_FILE_LINES_AS_KEY(Source):
    """Source wrapper for gen_file_lines_as_key(path, key, encoding)."""

    def __init__(self, path: str, key: str, encoding: str = "utf-8",
                 name: str = "FromFileLinesAddKey"):
        super().__init__(generator_fn=gen_file_lines_as_key(path, key, encoding), name=name)


class GEN_FILE_LINES_AS_KEY_WITH_TIME(Source):
    def __init__(self, path: str, key: str, time_key: str = "time", encoding: str = "utf-8",
                 name: str = "FromFileLinesAddKeyWithTime"):
        super().__init__(generator_fn=gen_file_lines_as_key_with_time(
            path, key, time_key, encoding), name=name)


class GEN_CSV_DICTS(Source):
    """Source wrapper for gen_csv_dicts(path, encoding)."""

    def __init__(self, path: str, encoding: str = "utf-8", name: str = "FromCSV"):
        super().__init__(generator_fn=gen_csv_dicts(path, encoding), name=name)


class GEN_NUMPY_ROWS(Source):
    """Source wrapper for gen_numpy_rows(array)."""

    def __init__(self, array, name: str = "FromNumpyRows"):
        super().__init__(generator_fn=gen_numpy_rows(array), name=name)


class GEN_RSS_HEADLINES(Source):
    """Source wrapper for gen_rss_headlines(url, interval, limit, sleep, parser)."""

    def __init__(self, url: str, interval: float = 5.0, limit: int | None = None,
                 sleep: callable = time.sleep, parser=None, name: str = "FromRSS"):
        super().__init__(generator_fn=gen_rss_headlines(url, interval, limit, sleep=sleep, parser=parser),
                         name=name)
