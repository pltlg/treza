"""Tests for AgentManager using libagent's FakeDevice (no hardware).

These exercise the real serve loop / state machine end-to-end: the manager
stands up the actual libagent SSH-agent on a private socket/pipe, and we talk
the agent protocol to it to confirm it lists the expected identity.
"""
from __future__ import annotations

import os
import sys

from libagent.device.fake_device import FakeDevice

from treza.agent.agentclient import request_identities_count
from treza.agent.identities import NIST256, SshIdentity
from treza.agent.manager import AgentManager, AgentState


def _unique_sock_path() -> str:
    token = os.urandom(8).hex()
    if sys.platform == "win32":
        return rf"\\.\pipe\treza-test-{token}"
    import tempfile

    return os.path.join(tempfile.gettempdir(), f"treza-test-{token}.sock")


def test_state_machine_transitions() -> None:
    """op-start/op-end bracket a device operation with WAITING_CONFIRMATION."""
    seen: list[AgentState] = []
    mgr = AgentManager(
        FakeDevice,
        [SshIdentity(user="t", host="h", curve=NIST256)],
        on_state_change=lambda s, _e: seen.append(s),
    )
    mgr._set_state(AgentState.RUNNING)
    mgr._on_op_start()
    mgr._on_op_end()
    assert seen == [
        AgentState.RUNNING,
        AgentState.WAITING_CONFIRMATION,
        AgentState.RUNNING,
    ]


def test_serve_and_list_identities_fakedevice() -> None:
    identities = [SshIdentity(user="tester", host="localhost", curve=NIST256)]
    mgr = AgentManager(FakeDevice, identities, sock_path=_unique_sock_path())
    mgr.start()
    try:
        assert mgr.state is AgentState.RUNNING
        count = request_identities_count(mgr.sock_path)
        assert count == 1, f"expected the agent to list 1 identity, got {count}"
    finally:
        mgr.stop()
    assert mgr.state is AgentState.STOPPED
