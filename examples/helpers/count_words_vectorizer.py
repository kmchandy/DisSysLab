import sklearn.feature_extraction.text as text


class CountWordsVectorizer:
    def __init__(
        self,
        vocabulary,  # list of words used to vectorize text
        input_field="text",  # field in the input dict containing text to vectorize
        output_field="vector"  # field in the output dict to store the vectorized result
    ):
        self.vocabulary = vocabulary
        self.input_field = input_field
        self.output_field = output_field

    def __call__(self, msg):
        vectorizer = text.CountVectorizer(vocabulary=self.vocabulary)
        msg[self.output_field] = vectorizer.transform(
            [msg[self.input_field]]).toarray()
        return msg

    run = __call__
