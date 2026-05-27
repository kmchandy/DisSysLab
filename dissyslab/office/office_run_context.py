"""
Runtime context injected into every ``nl_role`` system prompt.

Used by ``dsl run`` and by the Custom App backend so agents see the same
prefetched **NOAA tombstone table**, optional **wardrobe_inventory.json** body,
and optional **Open-Meteo** snapshots for multiple cities—without teaching
each role file to read the filesystem.

Environment keys populated by ``build_office_run_context_env``:

* ``OFFICE_RUNTIME_SLUG`` — final directory segment of ``office_dir`` name
  (used to build garment image URLs inside the wardrobe digest).

All other keys are optional; they are appended only when non-empty:

* ``OFFICE_WEATHERAPI_DIGEST`` — historical name; carries the **NOAA MapClick**
  markdown table when ``office.md`` references ``forecast.weather.gov``.
* ``OFFICE_WARDROBE_INVENTORY_DIGEST`` — Markdown rendering of
  ``wardrobe_inventory.json``.
* ``OFFICE_OPEN_METEO_CITIES_DIGEST`` — current conditions table for cities
  listed in ``wardrobe_run_config.json``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[misc, assignment]

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[misc, assignment]

# WMO codes — keep in sync with WeatherSource for readable conditions.
_WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    95: "Thunderstorm",
}


def _read_office_md(office_dir: Path) -> str:
    p = office_dir / "office.md"
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def nws_mapclick_forecast_digest(page_url: str) -> str:
    """Scrape NOAA 7-day tombstones from a MapClick forecast URL."""
    if BeautifulSoup is None or not page_url or "forecast.weather.gov" not in page_url:
        return ""
    req = Request(
        page_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; DisSysLabOfficeRunContext/1.0; "
                "+https://github.com/kmchandy/DisSysLab)"
            )
        },
    )
    try:
        with urlopen(req, timeout=25) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[tuple[str, str]] = []
    for li in soup.select("li.forecast-tombstone")[:14]:
        pn = li.select_one("p.period-name")
        tc = li.select_one("div.tombstone-container")
        period = pn.get_text(strip=True) if pn else ""
        body = tc.get_text(" ", strip=True) if tc else ""
        if period or body:
            safe = body.replace("|", "/")[:220]
            rows.append((period, safe))
    if not rows:
        return ""
    lines = [
        "**NOAA weather.gov** (MapClick scrape — use for **multi-day period** "
        "labels like “Tuesday / Tuesday Night”). ",
        "If an event is outside the SoCal scrape region, also read the "
        "**Open-Meteo city table** appended below for current conditions.",
        "",
        "| period | conditions |",
        "|--------|--------------|",
    ]
    for period, safe in rows:
        lines.append(f"| {period} | {safe} |")
    return "\n".join(lines)


def forecast_digest_for_office_md(office_md_text: str) -> str:
    """Build NOAA digest when ``office.md`` uses WeatherAPI *or* skips scrape."""
    if "weatherapi(" in office_md_text:
        return ""
    if "web_scraper(" not in office_md_text or "forecast.weather.gov" not in office_md_text:
        return ""
    m = re.search(r'web_scraper\s*\(\s*url\s*=\s*"([^"]+)"', office_md_text)
    page_url = m.group(1) if m else ""
    return nws_mapclick_forecast_digest(page_url)


def _wardrobe_inventory_digest(office_dir: Path) -> str:
    """Render ``wardrobe_inventory.json`` as Markdown for the LLM."""

    from dissyslab.office.wardrobe_media import (
        markdown_image_url,
        resolve_item_display_relative,
    )

    path = office_dir / "wardrobe_inventory.json"
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    items = data.get("items")
    if not isinstance(items, list):
        return ""
    slug = Path(office_dir).resolve().name
    lines = [
        "**Canonical wardrobe (JSON)** — suggest **only** garments below.",
        "**Image links:** use the **Resolved Markdown (`![…](…)`) URLs** verbatim. "
        "Each points at the **uploaded reference photo** under ``media/uploads/`` "
        "(``photo_media``). Do **not** invent paths — only use URLs listed under each item.",
        "",
    ]
    body_lines: list[str] = []
    for i, raw in enumerate(items, 1):
        if not isinstance(raw, dict):
            continue
        oid = raw.get("id", f"item_{i}")
        cat = raw.get("category", "")
        desc = raw.get("description", "")
        photo_ref = raw.get("photo_media", raw.get("media", ""))
        disp_rel, disp_src = resolve_item_display_relative(office_dir, raw)

        line = f"{i}. **`{oid}`**"
        if cat:
            line += f" — *{cat}*"
        if desc:
            line += f" — {desc}"
        if photo_ref:
            line += f" — stored photo: `{photo_ref}`"
        if disp_rel:
            md_url = markdown_image_url(slug, disp_rel)
            line += f" — **Resolved Markdown:** `![]({md_url})` *(source: {disp_src})*"
        else:
            line += " — **⚠ Missing media:** set `photo_media` to a path under `media/uploads/` on disk."
        body_lines.append(line)
    if not body_lines:
        return ""
    lines.extend(body_lines)
    notes = data.get("notes")
    if isinstance(notes, str) and notes.strip():
        lines.extend(["", "**Notes:**", notes.strip()])
    return "\n".join(lines)


def _fetch_open_meteo_current(city: str) -> tuple[str, dict[str, Any] | None]:
    """Return ``(city_label, reading_dict_or_none)``."""
    if not city.strip() or requests is None:
        return city.strip(), None
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "format": "json"},
            timeout=10,
        )
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            return city, {"error": "geocode miss", "city": city}
        top = results[0]
        lat, lon = float(top["latitude"]), float(top["longitude"])
        fx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "timezone": "auto",
            },
            timeout=10,
        )
        fx.raise_for_status()
        cur = fx.json().get("current", {}) or {}
        temp_c = cur.get("temperature_2m")
        code = cur.get("weather_code")
        return city, {
            "city": city,
            "label": top.get("name", city),
            "country": top.get("country_code", ""),
            "temp_c": temp_c,
            "temp_f": round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else None,
            "conditions": _WMO_CODES.get(code, f"code {code}" if code is not None else "?"),
            "wind_kmh": cur.get("wind_speed_10m"),
        }
    except (OSError, ValueError, TypeError):
        return city, {"error": "fetch failed", "city": city}


def open_meteo_cities_digest(office_dir: Path) -> str:
    """One-shot current conditions rows for configured cities."""
    path = office_dir / "wardrobe_run_config.json"
    if not path.is_file():
        return ""
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    cities = cfg.get("open_meteo_cities")
    if not isinstance(cities, list) or not cities:
        return ""
    lines = [
        "**Open-Meteo — current conditions** (snapshot at office start). ",
        "Match ICS **location / city mentions** against the closest row when an **event "
        "is not** in greater Los Angeles.",
        "",
        "| city query | conditions | °F | wind (km/h) |",
        "|------------|------------|----|---------------|",
    ]
    for c in cities:
        if not isinstance(c, str) or not c.strip():
            continue
        label, reading = _fetch_open_meteo_current(c.strip())
        if reading is None:
            continue
        if reading.get("error"):
            lines.append(f"| {label} | *{reading.get('error')}* | — | — |")
            continue
        tf = reading.get("temp_f")
        cond = reading.get("conditions", "")
        wk = reading.get("wind_kmh")
        lines.append(f"| {label} | {cond} | {tf} | {wk} |")
    return "\n".join(lines) if len(lines) > 4 else ""


def build_office_run_context_env(office_dir: Path) -> dict[str, str]:
    """Return env key → string payload for ``nl_role`` context injection."""
    office_dir = Path(office_dir).resolve()
    raw_md = _read_office_md(office_dir)
    out: dict[str, str] = {"OFFICE_RUNTIME_SLUG": office_dir.name}
    nws = forecast_digest_for_office_md(raw_md)
    if nws:
        out["OFFICE_WEATHERAPI_DIGEST"] = nws
    winv = _wardrobe_inventory_digest(office_dir)
    if winv:
        out["OFFICE_WARDROBE_INVENTORY_DIGEST"] = winv
    om = open_meteo_cities_digest(office_dir)
    if om:
        out["OFFICE_OPEN_METEO_CITIES_DIGEST"] = om
    return out


def apply_office_run_context_to_environ(
    office_dir: Path,
    *,
    override: bool = True,
) -> dict[str, str]:
    """Merge ``build_office_run_context_env`` into ``os.environ``.

    Parameters
    ----------
    override
        When ``False``, existing non-empty ``os.environ`` values win.
    """
    import os

    ctx = build_office_run_context_env(office_dir)
    for key, val in ctx.items():
        if not val:
            continue
        if not override and os.environ.get(key):
            continue
        os.environ[key] = val
    return ctx


__all__ = [
    "build_office_run_context_env",
    "apply_office_run_context_to_environ",
    "forecast_digest_for_office_md",
    "nws_mapclick_forecast_digest",
    "open_meteo_cities_digest",
]
