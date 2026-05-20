# DisSysLab Custom App

A browser-based UI for managing, running, editing, and creating DisSysLab offices.

## Structure

```
custom_app/
├── backend/          # FastAPI server (Python)
│   ├── main.py
│   └── requirements.txt
├── frontend/         # React app (Vite)
│   ├── src/
│   └── package.json
├── user_offices/     # Your created offices live here
└── README.md
```

### User offices (`user_offices/`)

Keep **office definitions and role prompts** under `custom_app/user_offices/<name>/` so your pipeline stays app-scoped.

- **`calendar_stylist`** can use **`web_scraper`** on **NOAA `forecast.weather.gov` (MapClick)** or **`weatherapi`** on **WeatherAPI.com**. For **`weatherapi`**, set **`WEATHERAPI_KEY`**; the **office_v2** compiler prefetches JSON and appends a date table to every role’s prompt. For **`web_scraper`** with a `forecast.weather.gov` URL, the **custom app backend** prefetches the same HTML before **Run** and sets **`OFFICE_WEATHERAPI_DIGEST`** with a **period** table so agents match weekdays like the situation room (`dsl run` from the shell skips that prefetch unless you set that env yourself). Install backend deps so **`beautifulsoup4`** is available for the NOAA prefetch.
- The MCP **`web`** source is different: it uses **fetch** and may be blocked by **robots.txt** on some hosts.

## Setup

These paths are relative to the **DisSysLab** repository root, e.g. `DisDylab/DisSysLab/`. If `cd custom_app/frontend` fails, you are probably one directory too high: `cd` into `DisSysLab` first.

### 1. Backend

From `DisSysLab/custom_app/backend/`:

```bash
pip install -r requirements.txt
```

Make sure your `ANTHROPIC_API_KEY` is set (either exported in your shell or in a `.env` file in `DisSysLab/`):

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

For **WeatherAPI.com** (e.g. `user_offices/calendar_stylist`), add a **WeatherAPI** key to the same `.env` or your shell (never commit it):

```bash
export WEATHERAPI_KEY='your-weatherapi-key'
```

### 2. Frontend

From `DisSysLab/custom_app/frontend/`:

```bash
npm install
```

## Running

You need two terminals. First `cd` to the **DisSysLab** repo root (the folder that contains `custom_app/` and `dissyslab/`).

**Terminal 1 — backend:**
```bash
cd custom_app/backend
uvicorn main:app --reload --port 8000
```

If your shell prompt is already `.../custom_app/backend` (or you see `backend %`), **do not** run `cd custom_app/backend` again — that path does not exist from inside `backend/`. Just run:

```bash
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd custom_app/frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.

**Office logs:** When you click **Run**, the child office process is streamed to the **Output** panel in the app. The same lines are also printed to the **backend terminal on stderr** with an `[office:name]` prefix (so you can debug next to Uvicorn’s `INFO` access lines).

## What you can do

### Browse offices
All built-in offices from `dissyslab/gallery/apps/`, `dissyslab/gallery/examples/`, and any legacy office folders directly under `dissyslab/gallery/` appear in the sidebar (same layout as `dsl list`). Your own offices under `custom_app/user_offices/` appear under "Your Offices".

### Run an office
Click any office → click **Run**. Output streams live in the **Output** panel below the office preview (not in the shell where `uvicorn` is running). Click **Stop** to end it.

### Edit an office
Click **Edit** to open the editor. Switch between `office.md` and each role file using the tabs. Click **Save** when done.

### Create a new office
Click **+ New Office** at the bottom of the sidebar. Chat with Claude — describe what you want your office to do. When Claude produces the files, you'll be prompted to name the office and click **Create Office**. It will appear in the sidebar immediately.
