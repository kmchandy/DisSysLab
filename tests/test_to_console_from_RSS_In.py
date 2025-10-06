from dsl.connectors.rss_in import RSS_In
from dsl.core import STOP

rss = RSS_In(url="https://news.ycombinator.com/rss",
             emit_mode="item", life_time=20)
for out in rss.run():
    if out == STOP:
        print("[STOP]")
    else:  # single item
        print(out["title"])
