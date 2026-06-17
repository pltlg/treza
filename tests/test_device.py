"""Tests for device detection/status.

Connection-free paths are deterministic (monkeypatched enumeration + pure
formatting). The real-device read is marked ``hardware`` and runs only with a
Trezor attached (``pytest -m hardware``).
"""
from __future__ import annotations

import pytest

from treza.agent import device
from treza.agent.device import DeviceStatus


def test_summary_no_device() -> None:
    assert DeviceStatus(present=False).summary == "No Trezor connected"


def test_summary_full() -> None:
    s = DeviceStatus(
        present=True,
        model_name="Trezor Safe 3",
        firmware_version="2.8.7",
        initialized=True,
        unlocked=True,
    )
    assert s.summary == "Trezor Safe 3 — fw 2.8.7"


def test_summary_locked_and_uninitialized() -> None:
    assert "locked" in DeviceStatus(present=True, model_name="Trezor", unlocked=False).summary
    assert "not initialized" in DeviceStatus(present=True, initialized=False).summary


def test_read_status_absent(monkeypatch) -> None:
    monkeypatch.setattr(device, "enumerate_transports", lambda: [])
    status = device.read_status()
    assert status.present is False
    assert status.summary == "No Trezor connected"


def test_enumerate_never_raises(monkeypatch) -> None:
    def boom():
        raise RuntimeError("usb exploded")

    monkeypatch.setattr(device, "enumerate_devices", boom)
    # enumerate_transports swallows the error and returns [].
    assert device.enumerate_transports() == []
    assert device.is_device_present() is False


@pytest.mark.hardware
def test_read_status_real_device() -> None:
    status = device.read_status()
    assert status.present, "connect a Trezor to run hardware tests"
    assert status.error is None, f"status read failed: {status.error}"
    assert status.model_name or status.internal_name
    print(f"\nDevice: {status.summary} (label={status.label!r})")
