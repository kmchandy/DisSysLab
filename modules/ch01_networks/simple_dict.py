# modules.ch01_networks.simple_dict

from dsl import network

list_of_words = ['hello', 'world', 'python']


def from_list(items=list_of_words):
    for item in items:
        yield {'text': item}


def exclaim(msg):
    msg['exclaim'] = msg.get('text', '') + '!'
    return msg


def uppercase(msg):
    msg['uppercase'] = msg.get('text', '').upper()
    return msg


results = []
def to_results(v): results.append(v)


# Define the network.
g = network([(from_list, exclaim), (exclaim, uppercase),
            (uppercase, to_results)])
g.run_network()

assert results == [
    {'text': 'hello', 'exclaim': 'hello!', 'uppercase': 'HELLO'},
    {'text': 'world', 'exclaim': 'world!', 'uppercase': 'WORLD'},
    {'text': 'python', 'exclaim': 'python!', 'uppercase': 'PYTHON'}
]
