# components/sources/natural_numbers_source.py

"""Source that generates natural numbers from 0 to max_count-1."""


class NaturalNumberGenerator:
    """
    Generates natural numbers: 0, 1, 2, 3, ..., max_count-1

    Returns messages as dicts: {"value": number}
    Returns None when count reaches max_count.

    Examples:
        >>> gen = NaturalNumberGenerator(max_count=5)
        >>> gen.run()  # 0
        >>> gen.run()  # 1
        >>> gen.run()  # 2
    """

    def __init__(self, max_count=10):
        """
        Args:
            max_count: Maximum number to generate (exclusive)
        """
        self.max_count = max_count
        self.current = 0

    def run(self):
        """
        Returns next natural number or None when exhausted.

        Returns:
            {"value": number} or None
        """
        if self.current >= self.max_count:
            return None

        msg = self.current
        self.current += 1
        return msg
