# dissyslab/components/sources/weather_source.py

"""
WeatherSource: Emits current-weather dicts into a DisSysLab pipeline.

WeatherSource polls the free Open-Meteo API (https://open-meteo.com/).
No API key is required and there are no signups. The only cost is a
network request every `poll_interval` seconds.

Each message looks like:
    {
        "type":       "weather",
        "city":       "Pasadena",
        "country":    "US",
        "temp_c":     22.4,
        "temp_f":     72.3,
        "wind_kmh":   8.6,
        "conditions": "Mainly clear",
        "timestamp":  "2026-04-21T12:34:56+00:00",
    }

Usage:
    from dissyslab.components.sources.weather_source import WeatherSource
    from dissyslab.blocks import Source

    weather = WeatherSource(city="Pasadena", poll_interval=3600)
    source  = Source(fn=weather.run, name="weather")

For testing (fire immediately, stop after one reading):
    weather = WeatherSource(city="Pasadena", poll_interval=0, max_readings=1)

Design notes:
    - First reading fires *immediately* when `run()` is first called, so
      a newly started office produces a briefing in the first few seconds
      instead of making the student wait a full poll interval.
    - If the network request fails (offline, rate-limited, bad city name),
      the source yields an error dict instead of crashing. This keeps the
      pipeline alive so students can see something useful happen.
    - Geocoding (city name → lat/lon) is done on first run and cached, so
      subsequent polls do only one HTTP call.
"""

import time
from datetime import datetime, timezone
from typing import Optional

import requests

# WMO weather-code → human-readable string. Reference:
# https://open-meteo.com/en/docs  (section "Weather variable documentation")
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
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherSource:
    """
    Polls Open-Meteo for current weather and yields one dict per reading.

    Args:
        city:          Plain-English city name (e.g. "Pasadena",
                       "London", "Tokyo"). Resolved once via Open-Meteo's
                       geocoding API.
        poll_interval: Seconds between readings. Default: 3600 (one hour).
                       Open-Meteo's free tier allows ~10k requests/day so
                       any interval above a few seconds is safe.
        max_readings:  Stop after this many readings. None = run forever.
                       Set to a small number for testing.

    Example:
        >>> weather = WeatherSource(city="Pasadena", poll_interval=3600)
        >>> source  = Source(fn=weather.run, name="weather")
    """

    _GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    _FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        city: str = "Pasadena",
        poll_interval: int = 3600,
        max_readings: Optional[int] = None,
    ):
        self.city = city
        self.poll_interval = poll_interval
        self.max_readings = max_readings

        # Geocoding cache — filled on first run.
        self._lat: Optional[float] = None
        self._lon: Optional[float] = None
        self._country: Optional[str] = None

    # ── HTTP helpers ──────────────────────────────────────────────────────

    def _geocode(self) -> None:
        """Resolve self.city → (lat, lon, country) and cache."""
        resp = requests.get(
            self._GEOCODE_URL,
            params={"name": self.city, "count": 1, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
        if not results:
            raise ValueError(
                f"Could not find a city called '{self.city}'. "
                f"Try a more specific name (e.g. 'Pasadena, CA')."
            )
        top = results[0]
        self._lat = float(top["latitude"])
        self._lon = float(top["longitude"])
        self._country = top.get("country_code") or top.get("country") or ""

    def _fetch(self) -> dict:
        """Fetch one current-weather reading."""
        if self._lat is None or self._lon is None:
            self._geocode()

        resp = requests.get(
            self._FORECAST_URL,
            params={
                "latitude": self._lat,
                "longitude": self._lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "timezone": "UTC",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("current", {}) or {}

        temp_c = data.get("temperature_2m")
        code = data.get("weather_code")
        return {
            "type": "weather",
            "city": self.city,
            "country": self._country or "",
            "temp_c": temp_c,
            "temp_f": round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else None,
            "wind_kmh": data.get("wind_speed_10m"),
            "conditions": _WMO_CODES.get(code, f"code {code}"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Generator ─────────────────────────────────────────────────────────

    def run(self):
        """
        Generator that yields one weather dict per poll.

        Compatible with Source(fn=weather.run, name="weather") directly —
        Source() in dsl/blocks/source.py auto-wraps generators.
        """
        readings = 0

        while True:
            try:
                yield self._fetch()
            except Exception as exc:  # noqa: BLE001 — surface any failure cleanly
                yield {
                    "type": "weather_error",
                    "city": self.city,
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            readings += 1
            if self.max_readings is not None and readings >= self.max_readings:
                return

            if self.poll_interval > 0:
                time.sleep(self.poll_interval)
