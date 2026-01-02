<!--  modules.ch03_GPT.README_1.md    -->

## 🧩 3.1 Agents that call AI Services

## 🎯 Goal
- Build AI agents that call AI services such as OpenAI, Gemini, and Anthropic.

## 📍 What’s an AI agent?
An AI agent is a transformer, i.e., it has a single argument and returns a single value. The value returned by an AI agent is obtained by calling an AI service.

An AI agent is specified by a system prompt:

```python
ai_agent = AgentOpenAI(system_prompt)

```
A common network pattern is one in which each agent enriches (adds fields to) dict messages as messages flow through the agent. An AI agent receives a message which is a dict with a field 'text' which contains the text. The message may have fields in addition to the 'text' field. The agent analyzes the text in the 'text' field and returns a JSON object. The fields of the returned JSON object are added to the message that the agent received.

You create an ai agent that receives and outputs dict messages as follows:

```python
ai_agent.enrich_dict

```
The simple examples in this module create networks in which a source is connected to an AI agent which is connected to a sink. These examples illustrate how you can use AI services in a distributed computation. We will build more complex examples later.

You will need to register with the AI provider and get a key to run these examples and build your own AI agents. The AI service may limit the amount of free service that you use.

The examples in this module use a [**Source** agent](./source_list_of_text.py) that yields texts from a list of texts and a [sink agent, **kv_live_sink.py**](dsl.connectors.live_kv_console), that prints results.

---

## 🧠 Examples
- [**Analyze sentiment of text**](./README_sentiment.md)
- [**AI simple demo of text analysis**](./README_general.md)
- [**Identify entities in text**](./README_entity.md)
- [**Provide summaries of texts**](./README_summarizer.md)
- [**Example of a detailed prompt for weather alerts**](./README_WeatherAlerts.md)

## 👉 Next
[**Analyze sentiment of text**](./README_sentiment.md)
