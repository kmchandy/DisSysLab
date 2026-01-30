<!-- modules/basic/README.md  -->

# Simple Network

## Key Point
 Build a distributed system without using concurrency primitives such as threads, processes locks, or message passing.

You specify a distributed system as a graph. The nodes of the graph call ordinary functions Often these functions are obtained from Python's rich collection of libraries. These functions do not have concurrency features such as threads, processes, locks, and messages.

## The Graph
The graph is specified as a list of directed edges where an edge from node u to
node v is written as (u, v). Each node in the graph has at least one incident edge.
The graph in this example is:

```python
    (hacker_data_source, discard_spam),
    (tech_data_source, discard_spam),
    (reddit_data_source, discard_spam),
    (discard_spam, analyze_sentiment),
    (discard_spam, discard_non_urgent),
    (discard_non_urgent, issue_alert),
    (analyze_sentiment, archive_recorder), 

RSS FEEDS (Sources)

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ hacker_data │    │ tech_data   │    │ reddit_data │
│   _source   │    │   _source   │    │   _source   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                 FANIN    ▼
                   ┌─────────────┐
                   │  discard_   │ (Transform: AI Spam Filter)
                   │    spam     │
                   └──────┬──────┘
                          │
                          │
                 FANOUT   ├──────────────────┐
                          │                  │
                          ▼                  ▼
                   ┌─────────────┐    ┌─────────────┐
                   │  analyze_   │    │  discard_   │ (Transform: Filter Urgent)
                   │  sentiment  │    │  non_urgent │
                   └──────┬──────┘    └──────┬──────┘
                          │                  │
                          │                  │
                          ▼                  ▼
                   ┌─────────────┐    ┌─────────────┐
                   │  archive_   │    │  issue_     │ (Sink: Email Alerts)
                   │  recorder   │    │  alert      │
                   └─────────────┘    └─────────────┘
                    (Sink: JSON)
```

## Nodes: Sources, Transformers and Sinks

Nodes without input edges are called **Source** nodes. Nodes without output edges are called **Sink** nodes. Nodes with at least one input and one output edge are called **Transformers**.

In this example, hacker_data_source, tech_data_source, and reddit_data_source  are souces; discard_spam, analyze_sentiment, and discard_non_urgent are transformers; and issue_alert and archive_recorder are sinks.

## Edges
Associated with each edge of the graph (u, v) is a queue consisting of the messages that u has sent that v has not received. The queue is changed only when u appends a message to the queue or when v receives a message from a (nonempty) queue.

## Components Library
The components library is a library of ordinary Python functions that have no concurrency primitives. In this example, we use functions in the library that are mockups of calls to AI services. For example, we use a mockup call to an AI service that determines the sentiment of a text. You can execute the code in this example immediately without registering for services. Later we will build and execute the same system with mockups replaced by calls to AI services and APIs. 

## From Plain Python to a Node of a Distributed System Graph

### Sources ###
You build a source node of the graph by calling **Source(f)** where **f** is a function that returns a value. Look at
```python
hacker_data_source = Source(MockRSSSource(
    feed_name="hacker_news", max_articles=100).run)
```
**MockRSSSource** is a class, and **MockRSSSource(feed_name="hacker_news", max_articles=100)** is an object -- an instance of that class -- while **MockRSSSource(feed_name="hacker_news", max_articles=100).run** is a function. When the function is called it returns the next article from the RSS source. The dsl infrastructure calls the function repeatedyl to generate a stream of articles.

### Transformers and Sinks ###
Similarly **Transform(f)**, where where **f** is a function, is a transformer node. Function **f** has a single argument and returns a single value.

In this example **MockAISentimentAnalyzer.run** is a function that has a single argument, a text, and that returns a single value which is a dict. When a message arrives at this node the contents of the message are passed to the function and the function's return value is sent as a message by the node.

Likewise, **Sink(f)**, where where **f** is a function, is a sink node. Function **f** must have a single argument. When a message arrives at this node the contents of the message are passed to the function and the function is executed.


### Filters: drop None messages ###
Streams do not contain **None** messages. When a node sends a **None** message the dsl infrastructure filters out the message and does not send it. This feature is used to build filters. In the example, the spam filter node executes a function that receives a text and returns **None** if the text is spam and returns the text if it is not spam. So the only messages output by spam filter are non-spam.


## Merge and Broadcast ##

### Merge Streams ###
A node may have input edges from multple nodes. In the example, the node **discard_spam** has inputs from all three source nodes. The message streams from all edges feeding a node are merged nondeterministically and fairly. Nondeterministically means that the order in which messages are received is unknown. The following situation is possible in a graph with edges (u, w) and (v, w). Node u sends message m to w and later node v sends a message m' to w, but w receives m' before m. 

The order of messages in the same edge is maintained. If u sends m to w and later send m' to w then w receives m before m'. Fairly means that if the computation runs forever then every message sent is received eventually.

### Broadcast ###
A node may have multiple edges leading from it. In the example, the node **discard_spam** has outputs to nodes **analyze_sentiment**, and **discard_non_urgent**. A stream output by a node is broadcast along all the output edges from that node. In the example, nodes **analyze_sentiment** and **discard_non_urgent** receive identical streams. The delay of messages on different streams is unknown. So, at a given instant, **analyze_sentiment** may have received more, or fewer, or the same number of messages as **discard_non_urgent**.

## Run the System
From the root directory, ```DisSysLab```, execute
```python
python -m modules.basic.network
```


## What you did
You built a distributed system in which multiple nodes execute concurrently. You specified the system network as a graph -- a list of edges. You specified each node in the graph by its type (Source, Transform, or Sink) and the function that the node called. These functions do not use concurrency operators. So, you built a distributed system without using parallel operators.

## Next
In this module, a node receives a message from one input queue and it outputs a message by appending it to one output queue. Next, we introduce a type of node called a **split** node which has more than one output queue. We also generalize a node to an **agent** which may send and receive messages from arbitrary numbers of queues.