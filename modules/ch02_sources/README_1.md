## 🧩 2.1 Sources

## 🎯 Goal
- Learn how to use different types of sources and create your own sources of data.

## 📍 What’s a “source”?
A **source** is a zero-argument Python callable that yields a stream of values (e.g., a generator).  
In this module we use standard sources such as RSS news feeds, social media posts, and sensors.

The next set of examples illustrates sources. In these examples, a source agent is connected to a sink agent which displays the data acquired by the source. Later, we will study examples in which sources are connected to AI agents or Python data science functions that analyze data streams from sources. The results of the analyses are fed to display.

## 📍 Connectors
`dsl.connectors` contains interfaces to different **sources** and **sinks**. We are adding more connectors and welcome contributions.

> ⚠️ Some connectors require registration/API keys or have usage restrictions—even if keys aren’t required.  
> Always review the provider’s terms and docs before using a connector.

---

## 🧠 Examples
- [**RSS** sources](./README_2_RSS.md)
- [**Social media post** sources](./README_3_posts.md)
- [**Coinbase data** sources](./README_4_REST.md)
- [**Temperature sensor** sources](./README_5_replay.md)
- [**Synthetic data: Sine waves** sources](./README_6_synthetic.md)

## 👉 Next
[**RSS** sources →](./README_2_RSS.md)
