"""Agent integration layer.

Everything that touches ``libagent`` / ``trezorlib`` lives behind this package,
so that upstream-internal coupling is localized to one seam (guarded by
``tests/test_coupling.py``).
"""
