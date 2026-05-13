"""
WeatherAPI.com forecast source — multi-day JSON via HTTPS (requests).

Use this instead of ``web_scraper`` for WeatherAPI.com: their API returns
JSON, not HTML, so BeautifulSoup-based scraping does not apply.

Set your key in the environment (do not commit it):

    export WEATHERAPI_KEY='your-key'

Example ``office.md``::

    weatherapi(q="Pasadena", days=7, poll_interval=1800, api_key_env="WEATHERAPI_KEY")

Each poll yields **one message per forecast day** (same five-key shape as
``WebScraper``) so downstream agents can match calendar dates to ``title``
/ ``timestamp`` (ISO date string).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests


class WeatherAPISource:
    """
    Poll WeatherAPI.com ``/v1/forecast.json`` and yield one dict per day.

    Args:
        q:              Location query (city, lat/lon, etc.) per WeatherAPI docs
        days:           Forecast days (1–14 per plan; clamped to 14)
        poll_interval:  Seconds between full fetches
        api_key_env:    Env var holding the API key (default: WEATHERAPI_KEY)
        max_readings:   Stop after this many polls (None = forever)
    """

    _URL = "https://api.weatherapi.com/v1/forecast.json"

    def __init__(
        self,
        q: str = "Pasadena",
        days: int = 7,
        poll_interval: int = 1800,
        api_key_env: str = "WEATHERAPI_KEY",
        max_readings: Optional[int] = None,
    ):
        self.q = q
        self.days = max(1, min(int(days), 14))
        self.poll_interval = int(poll_interval)
        self.api_key_env = api_key_env
        self.max_readings = max_readings

    def _message_for_day(self, day_block: dict[str, Any]) -> dict[str, str]:
        date = day_block.get("date") or ""
        d = day_block.get("day") or {}
        cond = (d.get("condition") or {}).get("text") or ""
        hi = d.get("maxtemp_f")
        lo = d.get("mintemp_f")
        rain = d.get("daily_chance_of_rain")
        parts = []
        if hi is not None and lo is not None:
            parts.append(f"High {hi}°F, low {lo}°F.")
        if cond:
            parts.append(cond + ".")
        if rain is not None:
            parts.append(f"Chance of rain {rain}%.")
        text = " ".join(parts).strip() or cond or "No daytime summary."
        title = f"{date} — {cond}" if cond else f"{date} — forecast"
        return {
            "source":    "weatherapi",
            "title":     title,
            "text":      text,
            "url":       f"https://www.weatherapi.com/",
            "timestamp": date,
        }

    def run(self):
        readings = 0
        while True:
            key = os.environ.get(self.api_key_env)
            if not key:
                yield {
                    "source":    "weatherapi",
                    "title":     "WeatherAPI configuration error",
                    "text":      (
                        f"Missing API key: set environment variable "
                        f"{self.api_key_env!r} to your WeatherAPI.com key."
                    ),
                    "url":       "https://www.weatherapi.com/",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                try:
                    r = requests.get(
                        self._URL,
                        params={
                            "key": key,
                            "q": self.q,
                            "days": self.days,
                            "aqi": "no",
                            "alerts": "no",
                        },
                        timeout=15,
                    )
                    r.raise_for_status()
                    data = r.json()
                    days = (data.get("forecast") or {}).get("forecastday") or []
                    if not days:
                        yield {
                            "source":    "weatherapi",
                            "title":     "WeatherAPI empty response",
                            "text":      str(data)[:500],
                            "url":       "",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    for block in days:
                        yield self._message_for_day(block)
                except Exception as exc:  # noqa: BLE001
                    yield {
                        "source":    "weatherapi",
                        "title":     "WeatherAPI request error",
                        "text":      str(exc),
                        "url":       "",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

            readings += 1
            if self.max_readings is not None and readings >= self.max_readings:
                return
            if self.poll_interval > 0:
                print(
                    f"[weatherapi] Sleeping {self.poll_interval}s "
                    f"(q={self.q!r}, days={self.days})..."
                )
                time.sleep(self.poll_interval)


def weatherapi(
    q: str = "Pasadena",
    days: int = 7,
    poll_interval: int = 1800,
    api_key_env: str = "WEATHERAPI_KEY",
    max_readings: Optional[int] = None,
) -> WeatherAPISource:
    return WeatherAPISource(
        q=q,
        days=days,
        poll_interval=poll_interval,
        api_key_env=api_key_env,
        max_readings=max_readings,
    )
