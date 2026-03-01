<!---- exampes/module_10/README.md --->

# Module 10: Cloud Edition

*The same app. The same container. Now running in the cloud.*

---

## What You'll Learn

One idea: **pushing to GitHub is all it takes to deploy your app to the cloud.**

The app is the BlueSky sentiment monitor from Module 09. The Dockerfile
is unchanged. The only new file is `railway.toml`, which tells Railway:
- where to find the Dockerfile
- what command to run
- how often to run it (every 10 minutes)

Push those files to GitHub, connect Railway, and your distributed system
runs in the cloud on a schedule — without your laptop being open.

---

## The Progression So Far

```
Module 07  g.run_network()      → runs in threads         on your laptop
Module 08  g.process_network()  → runs in processes       on your laptop  (one word changed)
Module 09  docker run ...       → runs in a container     on your laptop  (one file added)
Module 10  git push             → runs in the cloud       while you sleep (one file added)
```

Each module adds exactly one new thing. The app never changes.

---

## Before You Start

You need:
- A [Railway account](https://railway.app) — free, no credit card required
- A GitHub account (you likely already have one)
- Your DisSysLab repo pushed to GitHub

If DisSysLab is not yet on GitHub:
```bash
# From the DisSysLab root directory
git init
git add .
git commit -m "Initial commit"
gh repo create DisSysLab --public --push   # requires GitHub CLI
```

---

## Part 1: Understand the New File (5 minutes)

Open `railway.toml` at the repo root. It has three settings:

```toml
[build]
dockerfilePath = "examples/module_09/Dockerfile"
```

**Tell Railway where the Dockerfile lives.** Our Dockerfile is inside
`examples/module_09/`, not at the repo root. Without this line, Railway
would look in the wrong place and the build would fail.

```toml
[deploy]
startCommand = "python3 -m examples.module_10.app"
```

**The command Railway runs when the cron fires.** Same command you use
locally. The container starts, runs the pipeline, prints results to the
log viewer, and exits.

```toml
cronSchedule = "*/10 * * * *"
```

**Run every 10 minutes.** The five fields are: minute, hour,
day-of-month, month, day-of-week. `*/10` in the minute field means
"every 10 minutes." Railway uses UTC time.

That is the entire configuration. Three settings, one file.

---

## Part 2: Ask Claude to Build the Config (2 minutes)

You don't need to write `railway.toml` yourself. Here is the prompt
that generated the file in this directory:

> "Create a railway.toml for a Python app in a monorepo. The Dockerfile
>  is at examples/module_09/Dockerfile. Run it as a cron job every
>  10 minutes. The start command is: python3 -m examples.module_10.app"

---

## Part 3: Deploy to Railway (10 minutes)

**Step 1 — Copy `railway.toml` to the repo root:**

The file must live at the root of your repo, not inside `module_10/`:

```bash
cp examples/module_10/railway.toml railway.toml
git add railway.toml
git commit -m "Add Railway config for Module 10"
git push
```

**Step 2 — Create a Railway project:**

1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Select your DisSysLab repository
5. Click **Deploy Now**

Railway detects `railway.toml`, finds the Dockerfile, builds the image,
and schedules the first run.

**Step 3 — Watch the first run:**

Within 10 minutes, Railway fires the cron job. To see the output:

1. Click your service on the Railway project canvas
2. Click **Deployments**
3. Click the most recent deployment
4. Click **View Logs**

You'll see:

```
📡 BlueSky Sentiment Monitor
════════════════════════════════════════════════════════════

  bluesky_stream → sentiment → display

  Stops automatically after 20 posts.

────────────────────────────────────────────────────────────

  😊 [ POSITIVE]  @dev_sarah: Just deployed the new API! Developers are going to love this
  😞 [ NEGATIVE]  @angry_customer: The checkout is broken AGAIN! This is frustrating.
  😐 [  NEUTRAL]  @dev_alex: Quick question: does your API support webhooks?
  ...

────────────────────────────────────────────────────────────
✅  Done — 20 posts processed.
```

The same output you saw locally in Module 09 — now appearing in a cloud
log viewer, produced by a container you did not manually start.

**Step 4 — Trigger a run immediately (optional):**

You don't have to wait 10 minutes. In the Railway dashboard:

1. Click your service
2. Click **Trigger Run** (top right)

The container starts within seconds.

---

## Part 4: What Just Happened

When you pushed to GitHub, Railway:

1. Detected `railway.toml` in your repo
2. Found the Dockerfile at `examples/module_09/Dockerfile`
3. Built a container image from it
4. Registered the cron schedule (`*/10 * * * *`)

Every 10 minutes, Railway:

1. Starts a fresh container from that image
2. Runs `python3 -m examples.module_10.app`
3. Streams the output to the log viewer
4. Stops and discards the container when the app exits

Your laptop does not need to be on. The pipeline runs whether you are
at your desk, asleep, or on holiday.

---

## Key Concepts

### Infrastructure as Code

`railway.toml` is an example of **infrastructure as code** — the
deployment configuration is a text file in your repo, not a collection
of settings clicked through a dashboard. This means:

- Your deployment is version-controlled alongside your app
- Another student can clone your repo and deploy identically
- If something breaks, you can see exactly what changed

### Cron Jobs

A **cron job** is a task that runs on a schedule. The format
`*/10 * * * *` is read as:

```
  */10  *    *    *    *
   │    │    │    │    └── day of week (0=Sunday)
   │    │    │    └─────── month (1-12)
   │    │    └──────────── day of month (1-31)
   │    └───────────────── hour (0-23)
   └────────────────────── minute (*/10 = every 10 minutes)
```

Common schedules:
```
*/10 * * * *    every 10 minutes
0 * * * *       every hour
0 9 * * *       every day at 9am UTC
0 9 * * 1       every Monday at 9am UTC
```

### Why the app exits cleanly

Railway's cron scheduler skips a run if the previous one is still
running. Our `MAX_POSTS = 20` limit ensures the app always finishes
in under 2 minutes and exits with status 0. This is why the fixed
message count matters for cloud deployment — it makes the app safe
to schedule.

---

## Files in This Module

```
examples/module_10/
├── README.md           ← you are here
├── app.py              ← identical to module_09/app.py
├── test_module_10.py   ← tests for app and railway.toml

railway.toml            ← in the REPO ROOT (not module_10/)
examples/module_09/
└── Dockerfile          ← shared — unchanged from Module 09
```

---

## Running the Tests

```bash
pytest examples/module_10/test_module_10.py -v
```

The tests check that `railway.toml` exists at the repo root, contains
the required fields, and that `app.py` is identical to Module 09's.
They also re-run the network tests to confirm everything still works.

---

## Troubleshooting

**Railway says "No Dockerfile found"**
Make sure `railway.toml` is at the repo root (not inside `module_10/`)
and that `dockerfilePath` points to `examples/module_09/Dockerfile`.

**The cron job never fires**
Check that `cronSchedule` is set in `railway.toml`. Then click
**Trigger Run** in the dashboard to fire it manually and confirm the
app runs correctly before waiting for the schedule.

**The app runs but prints demo posts instead of live BlueSky posts**
Railway's container has internet access, but BlueSky Jetstream may be
temporarily unreachable. The demo fallback is working correctly.
Check again on the next scheduled run.

**My Railway trial has expired**
The 30-day free trial is enough to complete this module. If you want
to keep the app running after the trial, Railway's Hobby plan is $5/month.
Alternatively, see the Next Steps section below for other platforms.

---

## Next Steps

**Make it yours.** Ask Claude:

> "Modify examples/module_10/app.py to only show NEGATIVE sentiment posts,
>  and add a count of how many were found at the end."

Push the change. Railway redeploys automatically.

**Change the schedule.** Edit `cronSchedule` in `railway.toml`:

```toml
cronSchedule = "0 9 * * *"   # every day at 9am UTC
```

Push. Railway picks up the new schedule on the next deployment.

**Other cloud platforms.** Railway is one option. The same Dockerfile
works on any platform that supports containers:

| Platform | Free tier | Credit card |
|---|---|---|
| Railway | 30-day trial, then $5/month | Not required for trial |
| Render | Web services free (cron jobs $1/month) | Not required |
| Fly.io | Limited free tier | Required |
| AWS (ECS) | 12-month free tier | Required |
| Google Cloud Run | Always-free tier | Required |

The container you built in Module 09 is portable to all of them. That
is the point of containers.
