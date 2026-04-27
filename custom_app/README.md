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

### 2. Frontend

From `DisSysLab/custom_app/frontend/`:

```bash
npm install
```

## Running

You need two terminals, both starting from `DisSysLab/`.

**Terminal 1 — backend:**
```bash
cd custom_app/backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd custom_app/frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.

## What you can do

### Browse offices
All built-in offices from `dissyslab/gallery/` appear in the sidebar. Your own created offices appear under "Your Offices".

### Run an office
Click any office → click **Run**. Output streams live in the terminal panel. Click **Stop** to end it.

### Edit an office
Click **Edit** to open the editor. Switch between `office.md` and each role file using the tabs. Click **Save** when done.

### Create a new office
Click **+ New Office** at the bottom of the sidebar. Chat with Claude — describe what you want your office to do. When Claude produces the files, you'll be prompted to name the office and click **Create Office**. It will appear in the sidebar immediately.
