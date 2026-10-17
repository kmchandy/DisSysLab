# Recipes

Short, step-by-step how-tos. Each one starts from an office you already
have (usually one from the gallery, or the inbox sorter you build in the
[Getting Started guide](../GETTING_STARTED.md)), makes one change, and
says what `dsl check` and `dsl run` should show.

Do the Getting Started guide first; the recipes assume it.

| Recipe | You will |
|---|---|
| [Filter news for a topic](filter-for-a-topic.md) | change what an English role decides, and keep the rejects where you can read them |
| [Write a role in Python](write-a-python-role.md) | replace a model with a rule, test it, and write a role that remembers (no key needed) |
| [Read any RSS feed](add-an-rss-source.md) | bring a feed DisSysLab does not name into an office |
| [Sort your own inbox](monitor-your-inbox.md) | swap a file for your Gmail, and send only a short alert onward |
| [Send results outside](send-messages-outside.md) | write files, send email, post to Slack or a web service |
| [Receive webhooks](receive-webhooks.md) | listen for posts from other services |
| [Build an office out of offices](chain-offices.md) | use a whole office as one agent of a bigger one |
| [Deploy with Docker](deploy-with-docker.md) | run an office on a schedule, in the cloud or on your own machine |
| [Add a model backend](add-a-backend/README.md) | plug in a language model DisSysLab does not ship with |

Related:

- [SOURCES_AND_SINKS.md](../SOURCES_AND_SINKS.md): every source and sink,
  with its arguments.
- [LANGUAGE_MODELS.md](../LANGUAGE_MODELS.md): choosing a model, for the
  whole office or one agent.
- [The gallery](../../dissyslab/gallery/README.md): the example offices.
