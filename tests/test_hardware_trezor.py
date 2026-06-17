"""Hardware acceptance tests — require a connected, unlocked Trezor.

Run tomorrow with the Safe 3 attached:

    .venv\\Scripts\\python.exe -m pytest -m hardware -s

Each test prompts for physical confirmation ON THE DEVICE. This is the
Milestone 0 gate (real key derivation + signing) plus the Milestone 1
real-device serve check, as one command.
"""
from __future__ import annotations

import pytest
from libagent.device.trezor import Trezor

from tests.agent_protocol import request_identities_count
from treza.agent.identities import ED25519, NIST256, SshIdentity, export_public_key
from treza.agent.manager import AgentManager, AgentState
from treza.agent.ui_bridge import CallbackUI

pytestmark = pytest.mark.hardware

IDENTITY_STR = "treza-hwtest@example.com"


@pytest.fixture(autouse=True)
def _attach_ui():
    """Install a console UI so on-device prompts are announced."""
    Trezor.ui = CallbackUI(
        Trezor,
        on_button_request=lambda _c: print("\n  >>> CONFIRM ON THE DEVICE <<<", flush=True),
    )
    yield
    Trezor._session = None


@pytest.mark.parametrize("curve", [ED25519, NIST256])
def test_export_public_key_real(curve: str) -> None:
    ident = SshIdentity(user="treza-hwtest", host="example.com", curve=curve)
    with Trezor() as dev:
        line = export_public_key(dev, ident)
    print(f"\n{curve}: {line}")
    assert line.split()[0] == ident.key_type


def test_agent_serves_real_device() -> None:
    identities = [SshIdentity(user="treza-hwtest", host="example.com", curve=ED25519)]
    mgr = AgentManager(Trezor, identities)
    mgr.start()
    try:
        assert mgr.state is AgentState.RUNNING
        # Listing identities derives the pubkey on-device (confirm when prompted).
        assert request_identities_count(mgr.sock_path, timeout=60.0) == 1
    finally:
        mgr.stop()
