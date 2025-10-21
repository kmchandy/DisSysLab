## 🧩 2.1 Sources

## 🎯 Goal
- Use different types of sources and create your own sources of data.

## 📍 What’s a “source”?
A **source** is a zero-argument Python callable that yields a stream of values (e.g., a generator).  
In this module we use standard sources such as RSS news feeds, social media posts, and sensors.  
Later, we’ll connect sources to AI agents and Python functions to analyze the data.  
For now, examples focus on **source → display**.

## 📍 Connectors
`dsl.connectors` contains interfaces to different **sources** and **sinks**. We’re actively adding more and welcome contributions.

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
