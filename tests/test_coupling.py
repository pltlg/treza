"""Upstream-coupling guard.

Signet depends on libagent internals that are NOT a stable public API. If an
upstream upgrade renames or moves any of these, this test fails loudly so we
fix the single adapter seam (signet/agent/) instead of discovering it at
runtime on a user's machine. Keep this list in sync with what the agent layer
actually imports.
"""
from __future__ import annotations

import importlib

import pytest

SYMBOLS = [
    ("libagent.ssh", "serve"),
    ("libagent.ssh", "parse_config"),
    ("libagent.ssh", "JustInTimeConnection"),
    ("libagent.ssh.protocol", "Handler"),
    ("libagent.ssh.client", "Client"),
    ("libagent.server", "unix_domain_socket_server"),
    ("libagent.device.trezor", "Trezor"),
    ("libagent.device.interface", "Identity"),
    ("libagent.device.interface", "string_to_identity"),
    ("libagent.device.ui", "UI"),
    ("libagent.formats", "export_public_key"),
    ("libagent.formats", "decompress_pubkey"),
    ("libagent.formats", "CURVE_ED25519"),
    ("libagent.formats", "CURVE_NIST256"),
]

METHODS = [
    ("libagent.device.ui", "UI", ["button_request", "get_pin", "get_pairing_code"]),
    ("libagent.device.interface", "Identity", ["get_bip32_address", "to_string"]),
    ("libagent.ssh.client", "Client", ["sign_ssh_challenge", "export_public_keys"]),
]


@pytest.mark.parametrize(("module", "attr"), SYMBOLS)
def test_symbol_present(module: str, attr: str) -> None:
    mod = importlib.import_module(module)
    assert hasattr(mod, attr), f"libagent changed: {module}.{attr} is gone"


@pytest.mark.parametrize(("module", "cls_name", "methods"), METHODS)
def test_methods_present(module: str, cls_name: str, methods: list[str]) -> None:
    cls = getattr(importlib.import_module(module), cls_name)
    missing = [m for m in methods if not hasattr(cls, m)]
    assert not missing, f"libagent changed: {module}.{cls_name} missing {missing}"
