"""Headless agent lifecycle manager.

Runs ``libagent``'s SSH-agent serve loop in-process on a worker thread and
exposes a small state machine the GUI/tray can observe. All device I/O happens
on the worker thread; ``on_state_change`` callbacks fire from that thread, so
GUI consumers MUST marshal them onto the UI thread themselves.

The serving chain mirrors ``libagent.ssh.main`` exactly:

    client.Client(device())  ->  JustInTimeConnection  ->  protocol.Handler  ->  serve()

so behavior is identical to the stock ``trezor-agent`` CLI; we add only an event
wrapper around device operations (to drive the "waiting for confirmation" state)
and a stoppable worker thread (instead of ``signal.pause()``).
"""
from __future__ import annotations

import enum
import logging
import os
import sys
import tempfile
import threading
from collections.abc import Callable

from libagent.ssh import JustInTimeConnection, client, protocol, serve

from .identities import SshIdentity
from .ui_bridge import CallbackUI

log = logging.getLogger(__name__)

# OpenSSH on Windows looks for the agent on this well-known pipe.
WINDOWS_OPENSSH_PIPE = r"\\.\pipe\openssh-ssh-agent"


class AgentState(enum.Enum):
    """Lifecycle states surfaced to the UI."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    ERROR = "error"


def default_sock_path() -> str:
    """Default agent socket/pipe path for this OS.

    Windows uses the OpenSSH-compatible named pipe so ``ssh``/``git``/VS Code
    pick it up with no per-client config. Unix uses a private socket path
    (the GUI exports ``SSH_AUTH_SOCK`` pointing here).
    """
    if sys.platform == "win32":
        return WINDOWS_OPENSSH_PIPE
    return tempfile.mktemp(prefix="treza-ssh-agent-")


StateCallback = Callable[[AgentState, "Exception | None"], None]


class _EventClient:
    """Wrap ``client.Client`` to emit start/end events around device ops."""

    def __init__(self, inner: client.Client,
                 on_op_start: Callable[[], None],
                 on_op_end: Callable[[], None]) -> None:
        self._inner = inner
        self._on_op_start = on_op_start
        self._on_op_end = on_op_end

    def export_public_keys(self, identities):
        self._on_op_start()
        try:
            return self._inner.export_public_keys(identities)
        finally:
            self._on_op_end()

    def sign_ssh_challenge(self, blob, identity):
        self._on_op_start()
        try:
            return self._inner.sign_ssh_challenge(blob=blob, identity=identity)
        finally:
            self._on_op_end()

    def __getattr__(self, name):
        return getattr(self._inner, name)


class AgentManager:
    """Start/stop an in-process SSH agent backed by a hardware device."""

    def __init__(
        self,
        device_type: type,
        identities: list[SshIdentity],
        *,
        sock_path: str | None = None,
        ui: CallbackUI | None = None,
        debug: bool = False,
        timeout: float = 0.1,
        on_state_change: StateCallback | None = None,
        on_button_request: Callable[[object], None] | None = None,
    ) -> None:
        self.device_type = device_type
        self.identities = identities
        self.sock_path = sock_path or default_sock_path()
        self.debug = debug
        self.timeout = timeout
        self._on_state_change = on_state_change
        self._ui = ui or CallbackUI(device_type, on_button_request=on_button_request)

        self._state = AgentState.STOPPED
        self._error: Exception | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()  # set on RUNNING or ERROR
        self._lock = threading.Lock()

    # -- public API ---------------------------------------------------------

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def error(self) -> Exception | None:
        return self._error

    @property
    def environ(self) -> dict[str, str]:
        """Environment a child process needs to use this agent (Unix)."""
        return {"SSH_AUTH_SOCK": self.sock_path, "SSH_AGENT_PID": str(os.getpid())}

    def start(self, ready_timeout: float = 10.0) -> None:
        """Start the agent; block until RUNNING or raise on failure."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._ready_event.clear()
        self._error = None
        self._thread = threading.Thread(target=self._run, name="treza-agent", daemon=True)
        self._thread.start()
        if not self._ready_event.wait(timeout=ready_timeout):
            raise TimeoutError("agent did not reach RUNNING state in time")
        if self._state is AgentState.ERROR:
            raise RuntimeError(f"agent failed to start: {self._error!r}") from self._error

    def stop(self, join_timeout: float = 10.0) -> None:
        """Signal the serve loop to exit and wait for the worker to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=join_timeout)
        # Drop the cached device session so the next start reconnects cleanly.
        if hasattr(self.device_type, "_session"):
            self.device_type._session = None

    # -- internals ----------------------------------------------------------

    def _set_state(self, state: AgentState, error: Exception | None = None) -> None:
        with self._lock:
            self._state = state
            if error is not None:
                self._error = error
        if state in (AgentState.RUNNING, AgentState.ERROR):
            self._ready_event.set()
        if self._on_state_change is not None:
            try:
                self._on_state_change(state, error)
            except Exception:  # noqa: BLE001 — never let a UI callback kill the agent
                log.exception("on_state_change callback raised")

    def _on_op_start(self) -> None:
        if self._state is AgentState.RUNNING:
            self._set_state(AgentState.WAITING_CONFIRMATION)

    def _on_op_end(self) -> None:
        if self._state is AgentState.WAITING_CONFIRMATION:
            self._set_state(AgentState.RUNNING)

    def _make_conn(self) -> _EventClient:
        inner = client.Client(self.device_type())
        return _EventClient(inner, self._on_op_start, self._on_op_end)

    def _run(self) -> None:
        try:
            self._set_state(AgentState.STARTING)
            self.device_type.ui = self._ui
            conn = JustInTimeConnection(
                conn_factory=self._make_conn,
                identities=[i.to_libagent() for i in self.identities],
            )
            handler = protocol.Handler(conn=conn, debug=self.debug)
            with serve(handler=handler, sock_path=self.sock_path, timeout=self.timeout):
                self._set_state(AgentState.RUNNING)
                self._stop_event.wait()
        except Exception as exc:  # noqa: BLE001
            log.exception("agent worker failed")
            self._set_state(AgentState.ERROR, error=exc)
            return
        self._set_state(AgentState.STOPPED)
