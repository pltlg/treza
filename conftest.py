"""Ensure the project root is importable so `treza` and `tests` resolve."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
