## 🧩 3.1 Agents that call AI Services

## 🎯 Goal
- Build AI agents that call AI services such as OpenAI, Gemini, and Anthropic.

## 📍 What’s an AI agent?
An agent in **dsl** is a Python function that has a single argument and returns a single value: It receives a single message and outputs a single message. The output message of an AI agent is computed by an AI service.

You will need to register with the AI provider and get a key to run these examples and build your own AI agents.

These examples use a [**Source** agent](./source_list_of_text.py) that yields texts from a list of texts and a [sink agent, **kv_live_sink.py**](dsl.connectors.live_kv_console), that prints results. An AI agent is specified by a system prompt:

```python
ai_agent = AgentOpenAI(system_prompt=system_prompt)

```
A common network pattern is one in which each agent enriches (adds fields to) dict messages as messages flow through the agent. 

```python
ai_agent.enrich_dict(msg)

```
returns a dict which is the original msg with additional fields specified by the AI agent. The examples create networks in which a source is connected to an ai agent which is connected to a sink.


---

## 🧠 Examples
- [**Analyze sentiment of text**](./README_sentiment.md)
- [**AI simple demo of text analysis**](./README_general.md)
- [**Identify entities in text**](./README_entity.md)
- [**Provide summaries of texts**](./README_summarizer.md)
- [**Example of a detailed prompt for weather alerts**](./README_WeatherAlerts.md)

## 👉 Next
[**Analyze sentiment of text**](./README_sentiment.md)
