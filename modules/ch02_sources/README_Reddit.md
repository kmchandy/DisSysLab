# 2.6 • Source: Feed from Reddit

This page shows you how to get data from Reddit.

---
## What you’ll do

Create a network with two agents. One agent outputs a stream of posts from **Reddit** and the other agent prints the posts.

---

## Setup (once)

```bash
pip install websockets rich
```


## Reddit Feed Demo

```python
# modules.ch02_sources.feed_from_reddit

from dsl import network
# dsl.connectors has connectors to different sources of data and sinks
# including consoles. Reddit_In connects to a subreddit’s JSON feed.
from dsl.connectors.reddit_in import Reddit_In
# simple sink that prints dicts live
from dsl.connectors.live_kv_console import kv_live_sink


# ----------------------------------------------------
# 1) Configure the Reddit source
# ----------------------------------------------------
# Key params:
# - subreddit: which subreddit to read (e.g., "python" or "news").
# - poll_seconds: how often to check for new posts.
# - life_time: stop after N seconds (handy for short demos).
# - max_num_posts: stop after N posts (safety guard for lessons).

from dsl.connectors.reddit_in import Reddit_In

reddit = Reddit_In(
    subreddit="python",
    poll_seconds=5.0,
    life_time=30.0,
    max_num_posts=50,
)


def from_reddit():
    for item in reddit.run():
        yield {
            "subreddit": item.get("subreddit"),
            "author": item.get("author"),
            "title": item.get("title"),
            "score": item.get("score"),
            "created_utc": item.get("created_utc"),
        }


# ----------------------------------------------------
# 3) Create and run network: from_reddit -> kv_live_sink
# ----------------------------------------------------
g = network([(from_reddit, kv_live_sink)])
g.run_network()

```

## Run the demo
Execute the following from the DisSysLab directory:
```bash
python -m modules.ch02_sources.feed_from_posts
```

You will see a growing list of items like:
```bash
----------------------------------------                                             
                                                                                     
title                                                                                
Has writing matplot code been completely off-shored to AI?                           
                                                                                     
author                                                                               
Interesting_Bill2817                                                                 
                                                                                     
created_utc                                                                          
1765454039.0                                                                         
                                                                                     
score                                                                                
0                                                                                    
                                                                                     
subreddit                                                                            
Python                                                                               
                                       
```

## 👉 Next
[**Poll from REST sites** Poll numeric data from REST →](./README_REST.md)

