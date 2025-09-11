# dsl/block_lib/transforms/transform_lib/simple_transform_classes.py
from dsl.block_lib.transforms.transform import Transform


class UpperCase(Transform):
    """Transform that converts input text to uppercase."""

    def __init__(self,  name: str = "ToUpperCase"):
        super().__init__(func=lambda x: x.upper(), name=name)
