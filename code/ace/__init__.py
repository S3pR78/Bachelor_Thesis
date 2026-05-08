"""Compatibility shim for importing the ACE package with PYTHONPATH=code.

The actual ACE implementation lives in code/src/ace so it can stay next to the
rest of the source modules. This shim makes `import ace` work when the project
is run with PYTHONPATH=code.
"""
from pathlib import Path

_REAL_ACE_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "ace"

# Make submodule imports such as `ace.ace`, `ace.core`, `ace.llm` resolve to
# code/src/ace.
__path__ = [str(_REAL_ACE_PACKAGE)]

# Keep a visible marker for debugging.
__ace_shim__ = True
