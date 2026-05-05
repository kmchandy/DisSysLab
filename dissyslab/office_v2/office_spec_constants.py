"""
Shared constants for office_v2.

Lives in its own module so that ``agent_spec.py`` and
``office_spec.py`` can both reference ``EXTERNAL`` without creating a
circular import between them.
"""

# Reserved node identity for "this network's boundary".
# Mirrors the literal already used by ``dissyslab.network.Network`` so
# that boundary edges in OfficeSpec line up with the runtime convention
# without translation.
EXTERNAL: str = "external"
