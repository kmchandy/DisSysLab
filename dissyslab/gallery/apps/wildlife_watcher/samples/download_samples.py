#!/usr/bin/env python3
"""Download six public-domain animal photos for the wildlife_watcher demo.

Pure standard library — no pip install needed beyond Python itself.

Run from this folder::

    python download_samples.py

It writes six small JPEGs (~50 KB each, ~300 KB total) next to this
script, plus a ``LICENSES.md`` that credits each photographer and
links back to the canonical Wikimedia Commons page.

Why these photos
----------------

Five of the six are works of US federal employees (USDA, USFWS,
NPS) released into the public domain under 17 U.S.C. § 105. One
(the red fox) was released CC0 by its photographer. All are safe
to redistribute, modify, and ship in a software repository.

The script uses Wikimedia Commons' ``Special:FilePath`` redirect,
which is stable across the hash-bucketed CDN URLs that
``upload.wikimedia.org`` uses internally. If a file moves or is
renamed, edit ``PHOTOS`` below.

If you would rather use your own images, drop any ``.jpg`` or
``.png`` into this folder and run ``dsl run wildlife_watcher`` —
the office reads every supported image in the folder, no
download step required.
"""

from __future__ import annotations

import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path


HERE = Path(__file__).resolve().parent

# Each entry: (local filename, Wikimedia file name, license, author,
#              link to the file's Commons page for verification).
PHOTOS = [
    {
        "filename":   "white_tailed_deer.jpg",
        "remote":     "White-tailed_deer.jpg",
        "license":    "Public Domain (USDA — U.S. work)",
        "author":     "Scott Bauer, USDA Agricultural Research Service",
        "source":     "https://commons.wikimedia.org/wiki/File:White-tailed_deer.jpg",
    },
    {
        "filename":   "bald_eagle.jpg",
        "remote":     "Usfws-bald-eagle-ottawa-refuge.jpg",
        "license":    "Public Domain (USFWS — U.S. work)",
        "author":     "Tony Everhardt, U.S. Fish and Wildlife Service",
        "source":     "https://commons.wikimedia.org/wiki/File:Usfws-bald-eagle-ottawa-refuge.jpg",
    },
    {
        "filename":   "black_bear.jpg",
        "remote":     "American black bear (53625231256).jpg",
        "license":    "Public Domain (USFWS — U.S. work)",
        "author":     "U.S. Fish and Wildlife Service - Midwest Region",
        "source":     "https://commons.wikimedia.org/wiki/File:American_black_bear_(53625231256).jpg",
    },
    {
        "filename":   "red_fox.jpg",
        "remote":     "Vulpes_vulpes_ssp_fulvus.jpg",
        "license":    "CC0 1.0 Universal (Public Domain Dedication)",
        "author":     "Joanne Redwood",
        "source":     "https://commons.wikimedia.org/wiki/File:Vulpes_vulpes_ssp_fulvus.jpg",
    },
    {
        "filename":   "coyote.jpg",
        "remote":     "Coyote at the Sacramento National Wildlife Refuge. Credit John Heil USFWS (51174790883).jpg",
        "license":    "Public Domain (USFWS — U.S. work)",
        "author":     "John Heil, USFWS Pacific Southwest Region",
        "source":     "https://commons.wikimedia.org/wiki/File:Coyote_at_the_Sacramento_National_Wildlife_Refuge._Credit_John_Heil_USFWS_(51174790883).jpg",
    },
    {
        "filename":   "cougar.jpg",
        "remote":     "Mountain_Lion_in_Glacier_National_Park.jpg",
        "license":    "Public Domain (NPS — U.S. work)",
        "author":     "National Park Service, Glacier National Park",
        "source":     "https://commons.wikimedia.org/wiki/File:Mountain_Lion_in_Glacier_National_Park.jpg",
    },
]


_USER_AGENT = (
    "dissyslab-wildlife-watcher/1.0 "
    "(https://github.com/kmchandy/DisSysLab; mailto:kmchandy@gmail.com)"
)
_THUMB_WIDTH = 480  # one of Wikimedia's standard allowed thumbnail sizes
_TIMEOUT_SECONDS = 30


def _filepath_url(remote_name: str) -> str:
    """Build the ``Special:FilePath`` redirect URL for one file."""
    encoded = urllib.parse.quote(remote_name, safe='')
    return (
        f"https://commons.wikimedia.org/wiki/Special:FilePath/"
        f"{encoded}?width={_THUMB_WIDTH}"
    )


def _looks_like_jpeg(buf: bytes) -> bool:
    return buf[:3] == b"\xff\xd8\xff"


def _download_one(photo: dict, ctx: ssl.SSLContext) -> tuple[bool, str]:
    """Download a single photo. Returns ``(succeeded, status_text)``."""
    out_path = HERE / photo["filename"]
    if out_path.exists() and out_path.stat().st_size > 0:
        return True, "already present"
    url = _filepath_url(photo["remote"])
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT}
        )
        with urllib.request.urlopen(
            req, context=ctx, timeout=_TIMEOUT_SECONDS
        ) as resp:
            data = resp.read()
    except Exception as exc:
        return False, f"download failed: {exc}"
    if not _looks_like_jpeg(data):
        return False, "did not return JPEG bytes"
    out_path.write_bytes(data)
    size_kb = out_path.stat().st_size / 1024
    return True, f"{size_kb:.0f} KB"


def _write_licenses(report: list[tuple[dict, bool, str]]) -> Path:
    """Write LICENSES.md next to the script."""
    licenses_path = HERE / "LICENSES.md"
    lines = [
        "# Sample image licenses",
        "",
        "Every sample image shipped or downloaded by this script is "
        "in the public domain (works of U.S. federal employees, "
        "17 U.S.C. § 105) or released CC0 by the photographer. The "
        "images are reproduced here, attributed to the original "
        "creator, and linked back to the canonical Wikimedia "
        "Commons page where the license can be independently "
        "verified.",
        "",
        "| File | License | Photographer | Wikimedia source |",
        "|---|---|---|---|",
    ]
    for photo, ok, _status in report:
        lines.append(
            f"| `{photo['filename']}` | {photo['license']} | "
            f"{photo['author']} | "
            f"[file page]({photo['source']}) |"
        )
    lines.append("")
    licenses_path.write_text("\n".join(lines), encoding="utf-8")
    return licenses_path


def main() -> int:
    print(f"Downloading {len(PHOTOS)} public-domain animal photos to {HERE}/")
    print()
    ctx = ssl.create_default_context()
    report = []
    for photo in PHOTOS:
        ok, status = _download_one(photo, ctx)
        report.append((photo, ok, status))
        flag = "OK  " if ok else "FAIL"
        print(f"  {flag}  {photo['filename']:<26}  {status}")
    licenses_path = _write_licenses(report)
    successes = sum(1 for _, ok, _ in report if ok)
    print()
    print(
        f"Downloaded {successes}/{len(PHOTOS)} images. "
        f"Credits written to {licenses_path.name}."
    )
    if successes == 0:
        print(
            "\nIf every download failed, you may be offline or behind a "
            "proxy. Drop any .jpg / .png files into this folder by hand "
            "and `dsl run wildlife_watcher` will pick them up.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
