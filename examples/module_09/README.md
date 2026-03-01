# Module 09: Container Edition

*The same app. A new envelope. Runs anywhere.*

---

## What You'll Learn

One idea, stated plainly: **a container packages your app so it runs
anywhere — your laptop, a server, the cloud — without any "it works on
my machine" problems.**

The app is the BlueSky sentiment monitor you already know. The network,
the transform functions, the display sink — none of that changes. The
only new thing in this module is the `Dockerfile` that wraps it.

---

## The Progression So Far

```
Module 07  g.run_network()      → each analyzer runs in a thread
Module 08  g.process_network()  → each analyzer runs in a process   (one word changed)
Module 09  docker run ...       → the whole app runs in a container  (one file added)
```

Each module adds exactly one new thing. The app code never changes.

---

## Part 1: Run It Locally First (2 minutes)

Before touching Docker, confirm the app works as plain Python:

```bash
python3 -m examples.module_09.app
```

You'll see:

```
📡 BlueSky Sentiment Monitor
════════════════════════════════════════════════════════════
  bluesky_stream → sentiment → display

  Stops automatically after 20 posts.

────────────────────────────────────────────────────────────

  😊 [POSITIVE]  @dev_sarah: Just deployed the new API! Developers are going to love this 🚀
  😞 [NEGATIVE]  @angry_customer: The checkout is broken AGAIN! This is frustrating.
  😐 [ NEUTRAL]  @dev_alex: Quick question: does your API support webhooks?
  ...

────────────────────────────────────────────────────────────
✅  Done — 20 posts processed.
```

If BlueSky is reachable you get live posts. If not, the app falls back
to demo posts automatically and tells you so. Either way it runs and exits
cleanly.

---

## Part 2: Ask Claude to Build the Container (5 minutes)

You don't need to understand Docker to use it. Here is the prompt that
generated the `Dockerfile` in this directory:

> "Create a Dockerfile for a Python 3.11 app in the DisSysLab repo.
>  The app is examples/module_09/app.py. It needs websocket-client."

That's it. Claude produced the file. Your job is to understand what it
does, not to write it yourself.

---

## Part 3: Understand the Dockerfile (10 minutes)

Open `Dockerfile`. It has five instructions:

```dockerfile
FROM python:3.11-slim
```
**Start from an official Python image.** Docker maintains a library of
base images — pre-built operating systems with Python already installed.
`python:3.11-slim` is a minimal Linux image with Python 3.11. You don't
install an OS; you start from one that already works.

```dockerfile
WORKDIR /app
```
**Set the working directory inside the container.** Everything that
follows happens inside `/app`. This is like `cd /app` but it also creates
the directory if it doesn't exist.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
**Install dependencies.** `COPY` brings `requirements.txt` from your
machine into the container. `RUN` executes a shell command — here, `pip
install`. The `--no-cache-dir` flag keeps the image small by not storing
the pip download cache.

```dockerfile
COPY . .
```
**Copy your code.** This brings the entire DisSysLab project into the
container's `/app` directory. The `.` on the left means "everything here
on my machine"; the `.` on the right means "put it here in the container."

```dockerfile
CMD ["python3", "-m", "examples.module_09.app"]
```
**The command that runs when the container starts.** This is exactly what
you typed in Part 1. The container runs your app, produces output, and
exits. Done.

---

## Part 4: Build and Run the Container (5 minutes)

**Step 1 — Build the image.** Run this from the DisSysLab root directory:

```bash
docker build -t dissyslab-monitor -f examples/module_09/Dockerfile .
```

`-t dissyslab-monitor` gives the image a name. `-f` points to the
Dockerfile. `.` means "use the current directory as the build context"
(so `COPY . .` copies everything from here).

You'll see Docker pulling the base image, installing dependencies, and
copying your code. This takes about a minute the first time; subsequent
builds are much faster because Docker caches each step.

**Step 2 — Run the container:**

```bash
docker run dissyslab-monitor
```

You'll see exactly the same output as Part 1 — the same posts, the same
sentiment labels, the same clean exit after 20 posts. The app doesn't
know or care that it's inside a container.

That's the lesson. **Same output. Different envelope.**

---

## Part 5: What Just Happened

When you ran `docker run dissyslab-monitor`, Docker:

1. Started a fresh Linux environment (the container)
2. Loaded your app and all its dependencies into that environment
3. Ran `python3 -m examples.module_09.app`
4. Showed you the output
5. Stopped and discarded the container when the app exited

The container is isolated — it has its own filesystem, its own Python,
its own installed packages. Nothing from your laptop leaks in; nothing
from the container leaks out. If the app works in the container on your
machine, it works in a container anywhere.

---

## Key Concepts

### Image vs Container

An **image** is the blueprint — your code, dependencies, and
configuration baked into a single file. You build it once with
`docker build`.

A **container** is a running instance of that image. You can start many
containers from the same image. Each one is isolated and temporary.

```
Dockerfile  →  docker build  →  image  →  docker run  →  container
(recipe)                       (blueprint)               (running app)
```

### Why containers matter

Without a container, running your app on another machine means: install
the right Python version, install the right packages, set the right
environment variables, clone the repo, hope nothing conflicts. Containers
eliminate all of that. The image carries everything the app needs.

### The fixed message count

`MAX_POSTS = 20` in `app.py` ensures the container runs, produces output,
and exits cleanly. This is intentional — a container that exits is easy
to inspect, easy to re-run, and has no cost surprises. Module 10 shows
what happens when you deploy this container to a cloud server.

---

## Files in This Module

```
examples/module_09/
├── README.md      ← you are here
├── app.py         ← the app (identical in Module 10)
└── Dockerfile     ← the new thing
```

The app uses components shared with earlier modules:

```
components/
├── sources/
│   ├── bluesky_jetstream_source.py   ← live BlueSky stream
│   └── demo_bluesky_jetstream.py     ← demo fallback (no network needed)
└── transformers/
    ├── demo_ai_agent.py              ← sentiment analysis (no API key)
    └── prompts.py                    ← SENTIMENT_ANALYZER prompt
```

---

## Troubleshooting

**`docker: command not found`**
Install Docker Desktop from https://www.docker.com/products/docker-desktop/
It's free and works on Mac, Windows, and Linux.

**`COPY failed: file not found`**
Make sure you run `docker build` from the DisSysLab root directory, not
from inside `examples/module_09/`. The `.` at the end of the build command
must point to the root.

**The build succeeds but the app prints demo posts instead of live ones**
The container has no internet access, or BlueSky is temporarily
unreachable. The demo fallback is working as designed. The sentiment
analysis and output are identical either way.

**`docker run` hangs and never exits**
The `timeout=120` in `app.py` should prevent this, but if it happens,
press `Ctrl+C`. Then check that `MAX_POSTS = 20` is set in `app.py`.

---
---

## Running the Tests

**Python logic tests** — no Docker required, runs in seconds:

```bash
pytest examples/module_09/test_module_09.py -v
```

**Docker tests** — requires Docker Desktop to be running.
Make the script executable once, then run it:

```bash
chmod +x examples/module_09/test_docker.sh
bash examples/module_09/test_docker.sh
```

The Docker tests build the image, run the container, check that sentiment
labels appear in the output, and verify the container exits cleanly. They
take about 60–90 seconds the first time (Docker downloads the base image).
Subsequent runs are much faster because Docker caches the layers.


## Next Steps

**Module 10** takes this container and deploys it to Render — a free
cloud platform. The only new file is `render.yaml`, which tells Render
how to run the container. The app is unchanged. The Dockerfile is
unchanged. One new file, and your network runs in the cloud.

**Want to customise this module's app first?** Try asking Claude:

> "Modify examples/module_09/app.py to filter BlueSky posts to only
>  those mentioning Python or AI before running sentiment analysis."

The Dockerfile and everything else stays the same. Only `app.py` changes.