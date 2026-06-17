"""Unit tests for the identity model, export, and persistence (no hardware)."""
from __future__ import annotations

import pytest
from libagent.device.fake_device import FakeDevice

from treza.agent.identities import (
    ED25519,
    NIST256,
    IdentityStore,
    SshIdentity,
    export_public_key,
)


def test_identity_string_basic() -> None:
    ident = SshIdentity(user="alice", host="example.com")
    assert ident.identity_string == "ssh://alice@example.com"
    assert ident.curve == ED25519
    assert ident.key_type == "ssh-ed25519"


def test_identity_string_with_port() -> None:
    ident = SshIdentity(user="bob", host="srv", port=2222, curve=NIST256)
    assert ident.identity_string == "ssh://bob@srv:2222"
    assert ident.key_type == "ecdsa-sha2-nistp256"


def test_invalid_curve_rejected() -> None:
    with pytest.raises(ValueError):
        SshIdentity(user="x", host="h", curve="rsa")


def test_empty_host_rejected() -> None:
    with pytest.raises(ValueError):
        SshIdentity(user="x", host="")


def test_config_line_roundtrip() -> None:
    ident = SshIdentity(user="alice", host="example.com", port=2200, curve=NIST256)
    line = ident.to_config_line()
    assert line == "<ssh://alice@example.com:2200|nist256p1>"


def test_store_roundtrip(tmp_path) -> None:
    store = IdentityStore(path=tmp_path / "identities.conf")
    assert store.load() == []

    a = SshIdentity(user="alice", host="a.example", curve=ED25519)
    b = SshIdentity(user="bob", host="b.example", port=22, curve=NIST256)

    store.add(a)
    store.add(b)
    store.add(a)  # duplicate is a no-op

    loaded = store.load()
    assert loaded == [a, b]

    store.remove(a)
    assert store.load() == [b]


def test_export_public_key_format_with_fake_device() -> None:
    # FakeDevice only supports NIST256; this exercises the real
    # libagent.formats.export_public_key path without hardware.
    ident = SshIdentity(user="tester", host="localhost", curve=NIST256)
    with FakeDevice() as device:
        line = export_public_key(device, ident)
    parts = line.split()
    assert parts[0] == "ecdsa-sha2-nistp256"
    assert parts[-1] == "ssh://tester@localhost"
    # The blob is valid base64 and non-trivial.
    import base64

    assert len(base64.b64decode(parts[1])) > 32
