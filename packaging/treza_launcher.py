"""Frozen-app entry point.

PyInstaller runs its entry script as top-level `__main__`, which breaks the
relative imports in ``treza/__main__.py``. Importing ``treza`` as a package
here keeps the package context intact.
"""
import sys

from treza.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
