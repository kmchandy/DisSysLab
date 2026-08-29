"""The office reference, shipped with the code it describes.

These documents used to live inside the `office-builder` skill. That
made the language and its description two artifacts on two release
paths: the skill installs from GitHub, the parser from PyPI, and every
grammar change meant re-stamping the skill and asking each user to save
it again. They drifted, and holding them together took a suite of tests
whose only job was to notice.

Here they cannot drift onto different versions, because there is only
one version. `dsl grammar` prints them.
"""
