# DisSysLab — Build Your Own Office of AI Agents

AI chatbots answer when you ask. **DisSysLab runs an office of AI
agents that works for you continuously** — monitoring sources,
filtering, analyzing, and delivering results all the time, until
you tell it to stop.

You describe the office in plain English. DisSysLab builds it.

## Try it in ten seconds — no API key needed

```bash
pip install dissyslab
dsl run periodic_brief
open brief.html
```

You'll get a single styled HTML page with three headlines from BBC,
three from NPR, current weather for Pasadena, and three stock
tickers — all wired together by an office described in plain English.
Zero LLM calls, zero credentials, ~10 seconds wall time.

`dsl list` shows every office that ships with DisSysLab.
`dsl init periodic_brief my_brief` copies one into a folder you own
so you can edit it.

## Pick an AI engine when you want to go deeper

`periodic_brief` is the framework doing what frameworks do — wiring
data sources together. The richer demos (`situation_room`,
`inbox_triage`, `competitor_watch`, ...) use LLM-powered agents and
need you to pick an engine:

- **Ollama** — free, local, private. Download a ~19 GB model
  (Qwen3) one time. Office runs take 15–60 min on a typical Mac.
- **OpenRouter** — hosted Qwen-2.5-7B. Pennies per run, finishes in
  1–5 min on any laptop. API key from
  [openrouter.ai/keys](https://openrouter.ai/keys).
- **Claude** — Anthropic's hosted model. Highest quality, ~25–50¢
  per office run. API key from
  [console.anthropic.com](https://console.anthropic.com).

```bash
# Example: OpenRouter, the fast-and-cheap path
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct

dsl run situation_room
```

Or use the one-line installer to get prompted through engine choice
and have your shell rc file set up for you:

```bash
curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
```

## What is an office?

An office is a team of AI agents with **roles**, connected by an
**org chart**. You write each role in plain English — the same way
you'd describe a job to a new hire — and you write the org chart in
plain English too.

A single role file looks like this:

```
# Role: analyst

You are a news analyst who reviews articles and forwards items of
political or economic significance to an editor. Exclude celebrity
gossip, sports, and personal opinions.

If the item is relevant, send to editor.
Otherwise send to discard.
```

That's an agent. Combine a handful of them with sources and sinks
in an `office.md` file, and you have an office that runs continuously.

**Offices can contain offices.** Each office is a black box — the
organization around it only sees what goes in and what comes out.
You build organizations of arbitrary complexity one office at a time,
reusing offices across different networks.

## Learn more

- Full documentation, source, and contributing guide on
  [GitHub](https://github.com/kmchandy/DisSysLab).
- The [gallery](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/gallery/README.md)
  has a no-key tier (runs anywhere) and a hosted-backend tier
  (`inbox_triage`, `ticket_router`, `competitor_watch`,
  `lead_qualifier`, `new_grad_jobs`, ...).
- Visual walk-through in the
  [micro-course](https://kmchandy.github.io/DisSysLab/office_microcourse.html).

## Requirements

- Python 3.9 or newer.
- macOS or Linux for the shell installer; Windows works for the
  core framework via `pip install`.
- An LLM backend if you want to run the agentic offices — see
  "Pick an AI engine" above. The `periodic_brief` demo needs none.

## License

MIT — see [LICENSE](https://github.com/kmchandy/DisSysLab/blob/main/LICENSE)
on GitHub.
