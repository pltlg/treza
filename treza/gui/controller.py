"""Qt-facing controller around the headless agent core.

Owns the `IdentityStore` and the (optional) running `AgentManager`, and exposes
everything the UI needs as Qt signals/slots. The agent's `on_state_change`
callback fires on a worker thread; emitting a Qt signal from there is safe —
Qt delivers it as a queued call on the controller's (main) thread.
"""
from __future__ import annotations

import dataclasses
import threading

from PySide6.QtCore import QObject, QTimer, Signal

from ..agent import agentclient, device
from ..agent.device import DeviceStatus
from ..agent.identities import IdentityStore, SshIdentity
from ..agent.manager import AgentManager, AgentState

_POLL_MS = 2000


class AgentController(QObject):
    """Single point of contact between the GUI and the agent core."""

    stateChanged = Signal(object)         # AgentState
    deviceStatusChanged = Signal(object)  # DeviceStatus
    errorOccurred = Signal(str)
    publicKeyReady = Signal(object, str)  # (SshIdentity, authorized_keys line)

    def __init__(self) -> None:
        super().__init__()
        self.store = IdentityStore()
        self._mgr: AgentManager | None = None
        self._state = AgentState.STOPPED
        self._cached_status: DeviceStatus | None = None

        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_MS)
        self._timer.timeout.connect(self._poll_device)

    # -- lifecycle ----------------------------------------------------------

    def start_polling(self) -> None:
        self._poll_device()
        self._timer.start()

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._mgr is not None and self._state in (
            AgentState.RUNNING,
            AgentState.WAITING_CONFIRMATION,
        )

    @property
    def sock_path(self) -> str | None:
        return self._mgr.sock_path if self._mgr else None

    # -- identities ---------------------------------------------------------

    def identities(self) -> list[SshIdentity]:
        return self.store.load()

    def add_identity(self, identity: SshIdentity) -> None:
        self.store.add(identity)
        self._restart_if_running()

    def remove_identity(self, identity: SshIdentity) -> None:
        self.store.remove(identity)
        self._restart_if_running()

    # -- agent control ------------------------------------------------------

    def start_agent(self) -> None:
        if self.is_running:
            return
        from libagent.device.trezor import Trezor

        from ..agent.ui_bridge import CallbackUI

        identities = self.store.load()
        ui = CallbackUI(Trezor)
        self._mgr = AgentManager(
            Trezor, identities, ui=ui, on_state_change=self._on_state_change
        )
        try:
            self._mgr.start()
        except Exception as exc:  # noqa: BLE001
            self._mgr = None
            self._set_state(AgentState.ERROR)
            self.errorOccurred.emit(f"Failed to start agent: {exc}")

    def stop_agent(self) -> None:
        mgr, self._mgr = self._mgr, None
        if mgr is not None:
            mgr.stop()
        self._set_state(AgentState.STOPPED)

    def _restart_if_running(self) -> None:
        if self.is_running:
            self.stop_agent()
            self.start_agent()

    # -- public-key export (runs off the GUI thread) ------------------------

    def export_public_key_async(self, identity: SshIdentity) -> None:
        """Read the identity's public key from the running agent, off-thread.

        Reading via the agent avoids opening a second device session. Derivation
        triggers an on-device confirmation, so this must not block the UI.
        """
        if not self.is_running or self._mgr is None:
            self.errorOccurred.emit("Start the agent before exporting a public key.")
            return
        sock_path = self._mgr.sock_path
        identities = self.store.load()
        try:
            index = identities.index(identity)
        except ValueError:
            self.errorOccurred.emit("Unknown identity.")
            return

        def worker() -> None:
            try:
                pairs = agentclient.list_identities(sock_path, timeout=60.0)
                if index >= len(pairs):
                    raise RuntimeError("agent did not return this identity's key")
                blob, _comment = pairs[index]
                line = agentclient.authorized_keys_line(blob, identity.identity_string)
                self.publicKeyReady.emit(identity, line)
            except Exception as exc:  # noqa: BLE001
                self.errorOccurred.emit(f"Could not export public key: {exc}")

        threading.Thread(target=worker, name="treza-export", daemon=True).start()

    # -- internals ----------------------------------------------------------

    def _on_state_change(self, state: AgentState, error: Exception | None) -> None:
        # Called from the agent worker thread; Signal emission is queued to here.
        self._set_state(state)
        if state is AgentState.ERROR and error is not None:
            self.errorOccurred.emit(f"Agent error: {error}")

    def _set_state(self, state: AgentState) -> None:
        self._state = state
        self.stateChanged.emit(state)

    def _poll_device(self) -> None:
        present = device.is_device_present()
        if not present:
            status = DeviceStatus(present=False)
        elif self._mgr is None and (
            self._cached_status is None
            or not self._cached_status.present
            or self._cached_status.error
        ):
            # Safe to open a session for full details only when not serving.
            status = device.read_status()
        elif self._cached_status is not None and self._cached_status.present:
            status = dataclasses.replace(self._cached_status, present=True)
        else:
            status = DeviceStatus(present=True)

        if status != self._cached_status:
            self._cached_status = status
            self.deviceStatusChanged.emit(status)

    def shutdown(self) -> None:
        self._timer.stop()
        if self._mgr is not None:
            self.stop_agent()
