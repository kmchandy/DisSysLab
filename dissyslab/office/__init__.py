# dissyslab/office/__init__.py
"""
dissyslab.office — source/sink registry catalogue.

After the v2 cutover, this subpackage holds only
``utils.SOURCE_REGISTRY`` / ``utils.SINK_REGISTRY`` and the
``expand_shortcut`` helper. The compiler, codegen, and CLI for
``dsl build`` / ``dsl run`` all live in ``dissyslab.office_v2``.

Long-run direction: the registry should migrate into a built-in
role library; once that lands this subpackage goes away. Until
then, ``dissyslab.office_v2.compiler._build_source`` and
``_build_sink`` reach into ``utils`` to instantiate registry-backed
components.
"""
