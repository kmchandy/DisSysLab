# modules.ch03_openai.source_list_of_text
class source_list_of_text:
    def __init__(self, list_of_text=None):
        self.list_of_text = list_of_text

    def run(self):
        for data_item in self.list_of_text:
            yield {"text": data_item}
