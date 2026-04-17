# components/sources/calendar_source.py
"""
Calendar Source — Poll any public ICS calendar feed and yield upcoming events.

Works with Google Calendar, Apple Calendar, Outlook, or any calendar
that exports an ICS/iCal URL. No authentication needed for public calendars.

Setup for Google Calendar (one time):
    1. Open Google Calendar
    2. Click the three dots next to your calendar → Settings
    3. Scroll to "Integrate calendar"
    4. Copy the "Public URL to this calendar" (ends in .ics)
    5. Set environment variable OR pass directly:
         export CALENDAR_ICS_URL='https://calendar.google.com/calendar/ical/...'

Example office.md:
    Sources: calendar(url="https://calendar.google.com/calendar/ical/...",
                      poll_interval=300, days_ahead=7)

Example Python:
    from dissyslab.components.sources.calendar_source import CalendarSource
    from dissyslab.blocks import Source

    source = CalendarSource(
        url="https://calendar.google.com/calendar/ical/...",
        poll_interval=300,
        days_ahead=7,
    )
    node = Source(fn=source.run, name="calendar")
"""

import time
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


class CalendarSource:
    """
    Poll any public ICS calendar URL and yield upcoming events.

    Each event is yielded as a dict:
        {
            "source":      "calendar",
            "title":       str,   # event title/summary
            "text":        str,   # description or title if no description
            "start":       str,   # start time as ISO string
            "end":         str,   # end time as ISO string
            "location":    str,   # location if set, else ""
            "timestamp":   str,   # same as start
            "url":         str,   # calendar URL
        }

    Args:
        url:          ICS calendar URL (or set CALENDAR_ICS_URL env var)
        poll_interval: Seconds between calendar checks (default: 300)
        days_ahead:   How many days ahead to look for events (default: 7)
        url_env:      Environment variable for calendar URL (default: CALENDAR_ICS_URL)
    """

    def __init__(
        self,
        url: Optional[str] = None,
        poll_interval: int = 300,
        days_ahead: int = 7,
        url_env: str = "CALENDAR_ICS_URL",
    ):
        self.url = url or os.environ.get(url_env)
        self.poll_interval = poll_interval
        self.days_ahead = days_ahead

        if not self.url:
            raise ValueError(
                "Calendar ICS URL not found.\n"
                "Either pass url= directly or set:\n"
                f"  export {url_env}='https://calendar.google.com/calendar/ical/...'\n"
                "Get it from Google Calendar → Settings → Integrate calendar → Public URL"
            )

        self._seen_uids = set()

    def _fetch_events(self):
        """Fetch and parse ICS calendar, return upcoming events."""
        try:
            import urllib.request
            import urllib.error
        except ImportError:
            return []

        # Try to import icalendar; fall back to basic parsing
        try:
            from icalendar import Calendar
            use_icalendar = True
        except ImportError:
            use_icalendar = False
            print("[CalendarSource] For better calendar parsing: pip install icalendar")

        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "DisSysLab/1.0 CalendarSource"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
        except Exception as e:
            print(f"[CalendarSource] Error fetching calendar: {e}")
            return []

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=self.days_ahead)
        events = []

        if use_icalendar:
            events = self._parse_with_icalendar(raw, now, cutoff)
        else:
            events = self._parse_basic(raw.decode(
                "utf-8", errors="replace"), now, cutoff)

        return events

    def _parse_with_icalendar(self, raw, now, cutoff):
        """Parse ICS using the icalendar library."""
        from icalendar import Calendar
        events = []

        try:
            cal = Calendar.from_ical(raw)
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue

                uid = str(component.get("UID", ""))
                summary = str(component.get("SUMMARY", "No title"))
                desc = str(component.get("DESCRIPTION", ""))
                loc = str(component.get("LOCATION", ""))
                dtstart = component.get("DTSTART")
                dtend = component.get("DTEND")

                if dtstart is None:
                    continue

                start = dtstart.dt
                # Convert date to datetime if needed
                if not hasattr(start, "hour"):
                    start = datetime(start.year, start.month, start.day,
                                     tzinfo=timezone.utc)
                elif start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)

                if not (now <= start <= cutoff):
                    continue

                if uid in self._seen_uids:
                    continue
                self._seen_uids.add(uid)

                end = dtend.dt if dtend else start
                if not hasattr(end, "hour"):
                    end = datetime(end.year, end.month,
                                   end.day, tzinfo=timezone.utc)
                elif end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)

                events.append({
                    "source":    "calendar",
                    "title":     summary,
                    "text":      desc if desc else summary,
                    "start":     start.isoformat(),
                    "end":       end.isoformat(),
                    "location":  loc,
                    "timestamp": start.isoformat(),
                    "url":       self.url,
                })

        except Exception as e:
            print(f"[CalendarSource] Parse error: {e}")

        return events

    def _parse_basic(self, raw_text, now, cutoff):
        """Basic ICS parser when icalendar library is not available."""
        events = []
        current = {}

        for line in raw_text.splitlines():
            line = line.strip()
            if line == "BEGIN:VEVENT":
                current = {}
            elif line == "END:VEVENT":
                if "DTSTART" in current:
                    try:
                        start_str = current["DTSTART"]
                        # Parse basic YYYYMMDDTHHMMSSZ format
                        if "T" in start_str:
                            start = datetime.strptime(
                                start_str[:15], "%Y%m%dT%H%M%S"
                            ).replace(tzinfo=timezone.utc)
                        else:
                            start = datetime.strptime(
                                start_str[:8], "%Y%m%d"
                            ).replace(tzinfo=timezone.utc)

                        uid = current.get("UID", start_str)
                        if now <= start <= cutoff and uid not in self._seen_uids:
                            self._seen_uids.add(uid)
                            events.append({
                                "source":    "calendar",
                                "title":     current.get("SUMMARY", "No title"),
                                "text":      current.get("DESCRIPTION",
                                                         current.get("SUMMARY", "")),
                                "start":     start.isoformat(),
                                "end":       start.isoformat(),
                                "location":  current.get("LOCATION", ""),
                                "timestamp": start.isoformat(),
                                "url":       self.url,
                            })
                    except Exception:
                        pass
                current = {}
            elif ":" in line:
                key, _, val = line.partition(":")
                # Strip property parameters (e.g. DTSTART;TZID=...)
                key = key.split(";")[0]
                current[key] = val

        return events

    def run(self):
        """
        Generator that polls the calendar and yields upcoming events.
        Runs forever, sleeping poll_interval seconds between checks.
        DisSysLab's Source block wraps this generator automatically.
        """
        print(
            f"[CalendarSource] Monitoring calendar (next {self.days_ahead} days)")
        print(f"[CalendarSource] Polling every {self.poll_interval}s")

        while True:
            print(f"[CalendarSource] Checking for upcoming events...")
            events = self._fetch_events()
            print(f"[CalendarSource] Found {len(events)} upcoming event(s)")
            for event in events:
                yield event
            print(f"[CalendarSource] Sleeping {self.poll_interval}s...")
            time.sleep(self.poll_interval)


# ── Convenience factory for office_utils SOURCE_REGISTRY ─────────────────────

def calendar(
    url: Optional[str] = None,
    poll_interval: int = 300,
    days_ahead: int = 7,
) -> CalendarSource:
    return CalendarSource(
        url=url,
        poll_interval=poll_interval,
        days_ahead=days_ahead,
    )


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    print("CalendarSource — Test")
    print("=" * 60)
    print("Requires: ICS calendar URL")
    print("Optional: pip install icalendar  (for better parsing)")
    print("-" * 60)

    url = os.environ.get("CALENDAR_ICS_URL")
    if not url:
        print("Set CALENDAR_ICS_URL environment variable to test.")
        print("Example:")
        print("  export CALENDAR_ICS_URL='https://calendar.google.com/calendar/ical/...'")
        sys.exit(0)

    source = CalendarSource(url=url, poll_interval=60, days_ahead=14)

    count = 0
    for event in source.run():
        count += 1
        print(f"\n{count}. {event['title']}")
        print(f"   Start: {event['start']}")
        print(f"   Location: {event['location'] or 'none'}")
        print(f"   Text: {event['text'][:100]}")
        if count >= 5:
            print("\n[Stopping after 5 events for test]")
            break
