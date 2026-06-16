# dissyslab/__init__.py
"""DisSysLab — build offices of specialist agents in plain English.

Most users interact via the `dsl` command-line tool. The
programmatic API below is for tools and tests that build
networks directly without going through office.md:

    from dissyslab import network    # builder helper for Network
    from dissyslab import Agent      # base class for stateful agents
    from dissyslab import Network    # core Network container

For framework internals (parser, compiler, codegen, sources,
sinks, etc.) import from the relevant submodule directly —
for example, `from dissyslab.core import ExceptionThread` or
`from dissyslab.builder import PortReference`.

See the docs/ folder for the user guide.
"""

from dissyslab.core import Agent
from dissyslab.network import Network
from dissyslab.builder import network

__all__ = ['Agent', 'Network', 'network']

__version__ = '1.6.0'
