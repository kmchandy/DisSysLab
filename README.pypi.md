# DisSysLab — Build Your Own Office of AI Agents

AI chatbots answer when you ask. **DisSysLab runs an office of AI
agents that works for you continuously** — monitoring sources,
filtering, analyzing, and delivering results, until
you tell it to stop. Describe the office in plain English.


## Try it in seconds

```bash
pip install dissyslab
dsl run periodic_brief
open brief.html
```

You'll get a single styled HTML page with three headlines from BBC,
three from NPR, current weather for Pasadena, and three stock
tickers.

`dsl list` shows every office that ships with DisSysLab.
`dsl init periodic_brief my_brief` copies one into a folder you own
so you can edit it.

## Mix and match agents that best fit your accuracy, budget, and privacy needs.
An office can mix different types of agents: paid AI services such as Anthropic and OpenAI, ; free local AI such as Qwen on
Ollama for roles where cost or privacy matters more than accuracy; specialized
free models for specialized tasks like coding or entity extraction; and plain
Python functions. Get the agent you want from:


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

Or use the one-line installer to get prompts
and have your shell rc file set up for you:

```bash
curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
```

## What is an office?

An office is a team of AI agents with **roles** where the connections
between agents are specified by an
**org chart**. You specify a role as a job description in English,
and you specify the org chart in English.


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
You can build an office whose agents are offices. So you can structure
a complex office as a network of sub-offices just as a university
has sub-offices responsible for the medical school, engineering school,
and the college of humanities.

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
