# wardrobe_assistant

**Tags:** sense-and-respond, multi-source, multi-stage LLM pipeline,
calendar + weather + inventory

Looks at the next week of your calendar, pulls the local weather
forecast, and recommends what to wear for each event from your
known wardrobe. Posts a digest to the console, archives every outfit
recommendation to a JSONL log, and (optionally) emails you a
daily summary.

This office is the gallery's most ambitious "sense-and-respond"
example. Two unrelated real-world streams (ICS calendar feed, NOAA
forecast page) feed into a four-LLM pipeline that produces concrete
recommendations a person actually wants. Originally built by
Nyasha Makaya as part of his React app for DisSysLab.

## How it is wired

```
calendar (ICS feed) ──→ Casey  ─stylist─→ Jordan ─compiler─→ Riley ─┬→ display
                                                                    ├→ jsonl_recorder
                                                                    └→ gmail_sink

web_scraper (NOAA) ──→ Morgan ─summary─→ intelligence_display
```

The two source streams are independent: Casey reads each upcoming
calendar event and produces a structured event record; Morgan reads
each NOAA forecast period and produces a one-line weather summary.

Jordan (the stylist) consumes Casey's event records, consults the
wardrobe inventory, and recommends two or three outfit options per
event. Riley (the compiler) condenses Jordan's recommendations into
a digest suitable for terminal display, JSONL archival, and email.

## Run

```bash
dsl run wardrobe_assistant
```

You will see:

- **Console**: one card per upcoming calendar event with the
  recommended outfit, plus a running weather strip from Morgan.
- **`wardrobe_outfits.jsonl`** in the current directory: one line
  per outfit recommendation, suitable for after-the-fact analysis
  or building a personal style log.
- **Email** (if `GMAIL_USER` and `GMAIL_APP_PASSWORD` are set):
  a digest delivered to the address `GMAIL_USER` names. The
  shipped office uses `to="you@example.com"`; the framework
  substitutes your `GMAIL_USER` address automatically because
  `example.com` is the RFC 2606 placeholder domain. No per-office
  edit required. Without those env vars set, the would-be email
  body lands in `outbox.md` instead — useful preview, costs
  nothing.

## Customise

### Your wardrobe

Edit `wardrobe_inventory.json` to list your own clothes. The shipped
file has five sample items (a hoodie, two t-shirts, jeans, a polo).
Each item needs an `id`, a `category`, and a one-sentence
`description`. The stylist reads only the textual fields; you do
not need to provide images for the gallery version of the office.

Example minimal item:

```json
{
  "id": "item_navy_blazer",
  "category": "outerwear",
  "description": "Navy wool blazer — versatile dress-up layer."
}
```

The role files reference image paths (a holdover from the React-app
version of this office that rendered garment photos in a web UI).
The terminal display ignores those references; you can leave them
blank or remove the `photo_media` field entirely.

### Your calendar

The shipped office.md points at the US Holidays public Google
Calendar so the office demonstrates working out of the box. Replace
the `calendar(url="...")` line in `office.md` with your own ICS
URL — most calendar apps (Google Calendar, iCloud, Outlook) expose
one. For Google Calendar specifically, the URL is at
**Settings → Settings for my calendars → \<calendar name\> →
Integrate calendar → Secret address in iCal format**. Use the
secret address rather than the public one if you keep private
events; the URL itself is the credential.

### Your local weather

The `web_scraper(...)` source defaults to NOAA's forecast page for
Pasadena, CA (lat 34.1478, lon -118.1445). Change the `lat` and
`lon` query parameters in the URL to your own location. Find your
coordinates at <https://forecast.weather.gov> — search for your
city and the URL shows the lat/lon when the forecast loads.

### The stylist's personality

Edit `roles/wardrobe_stylist.md` to change how outfit suggestions
are framed. The shipped version produces practical "what to wear
to this event in this weather" recommendations; you might prefer a
more adventurous "try this combination you would not normally
consider" mode. Same edit pattern for any of the four roles —
each is a plain English `.md` file.

## The five agents

| Agent  | Role             | What it does |
| ------ | ---------------- | --- |
| Casey  | `calendar_analyst` | Reads each upcoming calendar event, structures it (title, time, location, dress category). |
| Morgan | `forecast_parser` | Reads each NOAA forecast period, emits a one-line weather summary. |
| Jordan | `wardrobe_stylist` | For each calendar event, consults the inventory and recommends two or three outfit options. |
| Riley  | `summary_compiler` | Combines Jordan's recommendations into a single per-event digest with weather context. |

## Files

- `office.md` — the four-agent wiring with two streaming sources
  and four sinks. The two source URLs (calendar + weather) and the
  Gmail recipient are the three knobs you most likely want to edit.
- `wardrobe_inventory.json` — the canonical garment list the
  stylist reads.
- `roles/calendar_analyst.md`, `forecast_parser.md`,
  `wardrobe_stylist.md`, `summary_compiler.md` — the four prompt
  files, fully self-contained. Edit any one independently.

## Output files (in the directory you ran `dsl run` from)

- `wardrobe_outfits.jsonl` — one line per outfit recommendation;
  useful for "what did I plan to wear last week?" review or for
  building a personal style dataset over time.
- `outbox.md` — if Gmail credentials are not set, would-be email
  digests land here in preview mode.

## Cost note

The office makes four LLM calls per calendar event Casey forwards:
Casey, Jordan, Riley each fire once; Morgan fires once per forecast
period (independently of Casey's events). For a typical week with
five events and 14 forecast periods, that's roughly 5 × 3 + 14 = 29
LLM calls per office run. Modest on any backend.

## Image extension (for React-app users)

The original office shipped with `media/uploads/<garment>.png`
images that the React UI rendered alongside each outfit
recommendation. The gallery version omits those because the
terminal display is text-only and the photos were the author's
personal wardrobe.

If you want the visual experience: set up Nyasha's React custom-app
backend (separate project), drop your own garment photos into
`media/uploads/`, add `photo_media: "media/uploads/<file>.png"`
fields back to `wardrobe_inventory.json`, and run the office under
the custom-app frontend. The `__DSLAPP__:` lines the stylist
already emits will render as inline images in that frontend.
