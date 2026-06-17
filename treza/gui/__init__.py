"""PySide6 front-end for Treza.

The GUI never touches `trezorlib`/the device directly — all agent and device
interaction goes through `AgentController`, which lives on the Qt main thread
and converts the agent's worker-thread callbacks into Qt signals.
"""
