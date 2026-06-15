# How to deploy an office for continuous operation

**Goal.** Run your office 24/7 — on a schedule, in the cloud — without
your laptop being on. This recipe walks you through wrapping an
office in a container and deploying it to a cloud scheduler.

You don't need to know Docker. The Dockerfile and deployment config
in this recipe were written by Claude; the recipe shows you the
prompts so you can do the same for your own office.


## When to use this

When your office is one you'd want running on a schedule (a morning
brief, an hourly weather check, an inbox triage), and you don't want
to keep a terminal open all day.

For a short interactive run on your laptop, you don't need any of
this. Just `dsl run <office>` is enough.


## The plan

```
your office (office.md)
        │
        ▼
    Dockerfile         ← Claude writes this from a prompt
        │
        ▼
docker run … <office>  ← test it on your laptop
        │
        ▼
   railway.toml        ← Claude writes this too
        │
        ▼
   git push            ← Railway picks up the config and starts running
                         on the schedule you set
```

The example below uses Railway because it's free for hobby projects
and reads a `railway.toml` config file directly from your repo. The
same Dockerfile works with any container scheduler — Google Cloud
Run, AWS Fargate, fly.io, a Raspberry Pi running `cron` and `docker`,
or a Linux box running `systemd`.


## What you'll need

- An office you already run locally with `dsl run <office>`. We'll
  use `periodic_brief` as the example (it produces a styled morning
  HTML brief and exits — perfect for a "run once each morning"
  schedule).
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  installed locally.
- A [Railway account](https://railway.app) — free, no credit card
  required.
- Your repo (containing your office) on GitHub.


## Step 1 — Ask Claude to write a Dockerfile

Open Claude and paste a prompt like this, adjusted for your office:

> *Write a Dockerfile for a DisSysLab office. The office lives at
> `my_brief/office.md` in the repo. Install Python 3.11, install
> `dissyslab` from PyPI, copy the office directory in, set the
> working directory to `/app/my_brief`, and run `dsl run .` when the
> container starts.*

Claude returns a file along these lines:

```dockerfile
# my_brief/Dockerfile
FROM python:3.11-slim
WORKDIR /app

# 1. Install dissyslab from PyPI.
RUN pip install --no-cache-dir dissyslab

# 2. Copy the office in.
COPY . /app/my_brief

# 3. Set the workdir to the office and run.
WORKDIR /app/my_brief
CMD ["dsl", "run", "."]
```

Save it as `my_brief/Dockerfile`. You don't need to understand every
line — Claude can explain any line you point at.

If your office needs additional packages beyond `dissyslab`'s
defaults (a fancier RSS reader, a specific OCR library, etc.) tell
Claude that in the prompt and it will adjust the `pip install` line.


## Step 2 — Test the container on your laptop

Build the image and run it once:

```bash
docker build -t my-brief my_brief/
docker run --rm my-brief
```

If your office needs an API key (`ANTHROPIC_API_KEY`, etc.), pass it
in with `-e`:

```bash
docker run --rm -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY my-brief
```

You should see the same output `dsl run my_brief` produced when you
ran it without Docker. If it works locally, it will work in the
cloud.


## Step 3 — Ask Claude to write a Railway config

Same idea as Step 1, different prompt:

> *Write a `railway.toml` for a DisSysLab office. The Dockerfile is
> at `my_brief/Dockerfile`. Run the container as a cron job every
> day at 6 AM UTC. The start command is `dsl run .`.*

Claude returns:

```toml
# railway.toml
[build]
dockerfilePath = "my_brief/Dockerfile"

[deploy]
startCommand = "dsl run ."
cronSchedule = "0 6 * * *"
```

The five fields in `cronSchedule` are minute, hour, day-of-month,
month, day-of-week. `0 6 * * *` means *"at minute 0 of hour 6, every
day."* Railway uses UTC. For a useful tutorial on cron syntax see
[crontab.guru](https://crontab.guru/).

**Save `railway.toml` at the repo root.** Railway looks for it there,
not inside the office folder.


## Step 4 — Deploy to Railway

Push your repo:

```bash
git add my_brief/Dockerfile railway.toml
git commit -m "Add Dockerfile and Railway config for my_brief"
git push
```

Then in Railway:

1. Sign in at [railway.app](https://railway.app).
2. Click **New Project → Deploy from GitHub repo**.
3. Pick your repo.
4. In the new project's **Variables** tab, add any environment
   variables your office uses (`ANTHROPIC_API_KEY`,
   `OPENROUTER_API_KEY`, etc.). Railway injects these at runtime.
5. Click **Deploy**. The first build takes 2–3 minutes. After it
   succeeds, the **Deployments** tab shows the cron schedule and the
   next run time.

When the cron fires, Railway spins up the container, runs your
office once, captures stdout in the log viewer, and shuts the
container down. No long-running process, no idle costs.


## Step 5 — Watch it run

The **Deployments** tab in Railway shows a log for every cron run.
Click the most recent one to see exactly what `dsl run .` printed.
If your office writes to a JSONL file or sends a message via a sink,
those side effects happen too — the container has full network
access.

If a run fails, Railway emails you and you can re-trigger from the
same tab.


## Alternative: self-hosting with cron + Docker

If you have a always-on machine (a home server, a Raspberry Pi, a
small VPS), you can run the same container locally on a cron
schedule without Railway.

Add a crontab entry:

```bash
crontab -e
```

Paste:

```cron
0 6 * * *  docker run --rm -e ANTHROPIC_API_KEY=sk-ant-xxx my-brief
```

That's it. The same `cronSchedule` syntax, the same container, your
machine, no cloud bill.

For systemd timers (more robust than cron on Linux), ask Claude:

> *Write a systemd service + timer that runs `docker run --rm
> my-brief` every day at 6 AM. The container needs
> `ANTHROPIC_API_KEY` from `/etc/dissyslab.env`.*


## Cost notes

Railway's free tier covers small daily-cron offices. The hours used
are counted from container start to container exit; offices that
finish in 30 seconds use about 15 minutes per month of compute. If
you cross the free-tier limit, Railway shows a forecast and lets you
upgrade per project.

For comparable services without Railway, look at fly.io (similar
free tier and slightly more complex setup), Google Cloud Run (free
tier of 2 million requests/month), or a $5/month VPS with the cron
recipe above.


## Common pitfalls

- **`railway.toml` in the wrong place.** It must be at the repo
  root, not inside your office folder. Railway only checks the root.
- **Forgot to add environment variables.** A cron run that exits
  immediately with `ANTHROPIC_API_KEY not set` is almost always
  missing a Railway Variables entry.
- **Cron in your local timezone.** Railway runs cron in UTC. A "6 AM
  every day" run wanted for Pacific time is `0 13 * * *` UTC during
  PDT, `0 14 * * *` during PST.
- **Office runs forever and bills accumulate.** Set `max_articles=N`
  / `max_readings=N` in your `office.md` so the office exits cleanly
  after one cycle. Cron will spin it up again on schedule.


## See also

- `docs/algorithms/CHECKPOINT_RESUME.md` — if your office is
  long-running (not a daily cron) and you want crash-resume.
- `docs/BUILD_APPS.md` — the full guide to designing offices.
- Railway docs: [docs.railway.app](https://docs.railway.app).
- Cron syntax help: [crontab.guru](https://crontab.guru).
