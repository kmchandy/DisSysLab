# examples.NASA_RSS_counts

from __future__ import annotations
from dsl.ops.transforms.term_frequency import docfreq_cooccurrence_from_messages

# Example 1 (NASA-style)


def count_terms(messages):
    """Compute doc-frequency co-occurrence counts of scientific terms with target orgs."""
    return docfreq_cooccurrence_from_messages(
        messages,
        primary_key="Organizations",
        secondary_key="Scientific Terms",
        targets=["JPL", "Ames", "LIGO"],
        primary_aliases={
            "JPL": [
                r"\bjpl\b",
                r"\bjet propulsion laboratory\b",
                r"\bnasa(?:'s)? jet propulsion laboratory\b",
                r"\bjpl[-/ ]?caltech\b",
            ],
            "Ames": [
                r"\bames\b",
                r"\bames research center\b",
                r"\bnasa(?:'s)? ames\b",
            ],
            "LIGO": [
                r"\bligo\b",
                r"\blaser interferometer gravitational[- ]wave observatory\b",
                r"\bligo laboratory\b",
                r"\bligo (?:hanford|livingston)\b",
            ],
        },
        slug_secondary_terms=True,  # "solar flares" -> "solar_flares"
    )
