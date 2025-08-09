class BaseIO:
    def read(self, prompt: str) -> str:
        raise NotImplementedError

    def write(self, text: str) -> None:
        raise NotImplementedError


class CLIIO(BaseIO):
    def read(self, prompt: str) -> str:
        return input(prompt)

    def write(self, text: str) -> None:
        print(text)


class FakeIO(BaseIO):
    def __init__(self, inputs):
        self.inputs = list(inputs)
        self.outputs = []

    def read(self, prompt: str) -> str:
        return self.inputs.pop(0) if self.inputs else "exit"

    def write(self, text: str) -> None:
        self.outputs.append(text)
