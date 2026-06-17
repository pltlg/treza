"""Device detection and status (model, firmware, lock state).

Two tiers, by cost:

* ``is_device_present()`` / ``enumerate_transports()`` — cheap USB enumeration,
  no connection, no on-device prompt. Suitable for frequent polling (tray).
* ``read_status()`` — connects and reads the device *features* (public info:
  model, firmware, label, initialized/locked). Reading features does NOT require
  PIN or a physical confirmation, so it is also prompt-free, but it is heavier.

trezorlib 0.20 recognizes the Trezor Safe 3 (``models.TREZOR_SAFE3`` / internal
``T3B1``), so model reporting works across the Safe family.
"""
from __future__ import annotations

import dataclasses
import logging

from trezorlib.client import get_default_client
from trezorlib.transport import enumerate_devices

log = logging.getLogger(__name__)

APP_NAME = "Treza"


@dataclasses.dataclass(frozen=True)
class DeviceStatus:
    """Snapshot of the connected device (or absence thereof)."""

    present: bool
    model_name: str | None = None
    internal_name: str | None = None
    label: str | None = None
    firmware_version: str | None = None
    initialized: bool | None = None
    unlocked: bool | None = None
    vendor: str | None = None
    error: str | None = None

    @property
    def summary(self) -> str:
        """Human-readable one-liner for the status panel / tray tooltip."""
        if not self.present:
            return "No Trezor connected"
        if self.error:
            return f"Trezor connected (details unavailable: {self.error})"
        name = self.model_name or self.internal_name or "Trezor"
        bits = [name]
        if self.firmware_version:
            bits.append(f"fw {self.firmware_version}")
        if self.initialized is False:
            bits.append("not initialized")
        elif self.unlocked is False:
            bits.append("locked")
        return " — ".join(bits)


def enumerate_transports() -> list:
    """Return connected Trezor transports (empty list if none). Prompt-free."""
    try:
        return list(enumerate_devices())
    except Exception:  # noqa: BLE001 — enumeration must never raise to the UI
        log.exception("device enumeration failed")
        return []


def is_device_present() -> bool:
    """True if at least one Trezor is connected. Cheap; safe to poll."""
    return bool(enumerate_transports())


def read_status(app_name: str = APP_NAME) -> DeviceStatus:
    """Read model/firmware/lock status from the first connected device.

    Degrades gracefully: if the device is present but cannot be read, returns
    ``present=True`` with ``error`` set rather than raising.
    """
    transports = enumerate_transports()
    if not transports:
        return DeviceStatus(present=False)

    transport = transports[0]
    try:
        client = get_default_client(app_name=app_name, path_or_transport=transport)
        model = getattr(client, "model", None)
        features = getattr(client, "features", None)
        version = getattr(client, "version", None)
        fw = ".".join(str(x) for x in version) if version else None
        return DeviceStatus(
            present=True,
            model_name=getattr(model, "name", None),
            internal_name=getattr(model, "internal_name", None),
            firmware_version=fw,
            label=getattr(features, "label", None) if features else None,
            initialized=getattr(features, "initialized", None) if features else None,
            unlocked=getattr(features, "unlocked", None) if features else None,
            vendor=getattr(features, "vendor", None) if features else None,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("reading device status failed")
        return DeviceStatus(present=True, error=str(exc))
