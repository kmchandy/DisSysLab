from dsl.connectors.rss_in import RSS_In
from dsl import network

# Define functions.

rss = RSS_In(url="https://news.ycombinator.com/rss",
             output_keys=["title", "link", "text"],
             fetch_page=True, life_time=2)  # ~2s demo


def from_rss():
    for out in rss.run():
        yield out


results = []


def to_results(v):
    results.append(v)


# Define the network
g = network([(from_rss, to_results)])
g.run_network()

if __name__ == "__main__":
    print(f"results = {results}")
