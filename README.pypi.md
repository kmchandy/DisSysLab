# DisSysLab — Build Your Own Office of AI Agents

AI chatbots answer when you ask. **DisSysLab runs an office of AI agents
that works for you continuously** — monitoring sources, filtering, analyzing,
and delivering results all the time, until you tell it to stop.

You describe the office in plain English. DisSysLab builds it.

![A DisSysLab office running](https://raw.githubusercontent.com/kmchandy/DisSysLab/main/dissyslab/gallery/org_situation_room/screenshot.png)

## Install

```bash
pip install dissyslab
dsl doctor
```

`dsl doctor` checks your Python, the dependencies, and whether your
Anthropic API key is set. Get a key at https://console.anthropic.com.

## Run your first office

```bash
dsl list
dsl init org_intelligence_briefing my_briefing
cd my_briefing
echo "ANTHROPIC_API_KEY=your-key-here" > .env
dsl run .
```

`dsl list` shows every office that ships with DisSysLab. `dsl init` copies
one of them into a folder you own. From there, edit prompts, connect
sources, rewire agents — the office is yours.

## What is an office?

An office is a team of AI agents with roles, connected by an org chart.
You write each role in plain English — the same way you'd describe a job
to a new hire — and you write the org chart in plain English too.

A single role file looks like this:

```
# Role: analyst

You are a news analyst who reviews articles and forwards items of
political or economic significance to an editor. Exclude celebrity
gossip, sports, and personal opinions.

If the item is relevant, send to editor.
Otherwise send to discard.
```

That's an agent. Combine a handful of them with sources and sinks in an
org chart, and you have an office that runs continuously.

**Offices can contain offices.** Each office is a black box — the
organization around it only sees what goes in and what comes out. You
build organizations of arbitrary complexity one office at a time,
reusing offices across different networks.

## Learn more

- Full documentation, source, and contributing guide on [GitHub](https://github.com/kmchandy/DisSysLab)
- Visual walk-through in the [micro-course](https://kmchandy.github.io/DisSysLab/office_microcourse.html)
- Every shipped office with `dsl list`

## Requirements

- Python 3.9 or newer
- An Anthropic API key

## License

MIT — see [LICENSE](https://github.com/kmchandy/DisSysLab/blob/main/LICENSE) on GitHub.
