"""Bridge between libagent's device UI callbacks and Signet's app layer.

``libagent.device.ui.UI`` is the object trezorlib calls back into when the
device needs interaction. We subclass it to surface those events to the GUI:

* ``button_request`` — the device is waiting for physical confirmation
  (drives the tray's "waiting for Trezor" state). Upstream's body is a literal
  ``# XXX: show notification to the user?`` — this is the intended hook.
* ``get_pin`` / ``get_pairing_code`` — only used by older devices that enter
  PIN on the host. The Trezor Safe family enters PIN on-device, so the default
  (GnuPG pinentry) path is normally never hit; we still allow an override.

The callbacks are plain callables, NOT Qt signals, so this module has no Qt
dependency and is unit-testable headless. The Qt layer wires signals to these.
"""
from __future__ import annotations

from collections.abc import Callable

from libagent.device.ui import UI

ButtonCallback = Callable[[object], None]
PinProvider = Callable[[object], str]
PairingProvider = Callable[[], str]


class CallbackUI(UI):
    """A ``libagent`` UI that forwards device events to injected callbacks."""

    def __init__(
        self,
        device_type: type,
        *,
        on_button_request: ButtonCallback | None = None,
        pin_provider: PinProvider | None = None,
        pairing_provider: PairingProvider | None = None,
        config: dict | None = None,
    ) -> None:
        super().__init__(device_type=device_type, config=config or {})
        self._on_button_request = on_button_request
        self._pin_provider = pin_provider
        self._pairing_provider = pairing_provider

    def button_request(self, _code=None):
        """Device is waiting for the user to confirm on its screen."""
        if self._on_button_request is not None:
            self._on_button_request(_code)

    def get_pin(self, _code=None):
        """Provide a PIN (host-entry devices only)."""
        if self._pin_provider is not None:
            return self._pin_provider(_code)
        return super().get_pin(_code)

    def get_pairing_code(self):
        """Provide a pairing code (devices that require host pairing)."""
        if self._pairing_provider is not None:
            return self._pairing_provider()
        return super().get_pairing_code()
