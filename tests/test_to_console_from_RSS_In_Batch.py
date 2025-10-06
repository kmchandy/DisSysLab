from dsl.connectors.rss_in import RSS_In
from dsl.core import STOP

rss = RSS_In(url="https://news.ycombinator.com/rss", life_time=45)  # ~45s demo
for out in rss.run():
    if out == STOP:
        print("[STOP]")
    elif isinstance(out, list):  # batch
        print(f"[BATCH x{len(out)}]")
        for output_element in out:
            print(f"title: {output_element["title"]}")
            print(f"link: {output_element["link"]}")
            print(f"published: {output_element["published"]}")
            print()
