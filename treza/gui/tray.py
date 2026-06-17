"""System-tray icon: agent status at a glance + quick controls (M3)."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ..agent.manager import AgentState
from .controller import AgentController
from .icons import status_icon
from .main_window import _STATE_TEXT, MainWindow


class TrayIcon(QSystemTrayIcon):
    def __init__(self, controller: AgentController, window: MainWindow) -> None:
        super().__init__()
        self.controller = controller
        self.window = window
        window._tray_active = True  # makes the window hide-to-tray on close

        menu = QMenu()
        self._toggle_action = menu.addAction("Start agent")
        self._toggle_action.triggered.connect(self._toggle)
        show_action = menu.addAction("Show window")
        show_action.triggered.connect(self._show_window)
        menu.addSeparator()
        quit_action = menu.addAction("Quit Treza")
        quit_action.triggered.connect(self._quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)
        controller.stateChanged.connect(self._on_state)
        self._on_state(controller.state)

    def _on_state(self, state: AgentState) -> None:
        self.setIcon(status_icon(state))
        self.setToolTip(f"Treza — {_STATE_TEXT.get(state, str(state))}")
        running = state in (AgentState.RUNNING, AgentState.WAITING_CONFIRMATION)
        self._toggle_action.setText("Stop agent" if running else "Start agent")
        if state is AgentState.WAITING_CONFIRMATION:
            self.showMessage(
                "Treza", "Confirm the operation on your Trezor.",
                QSystemTrayIcon.Information, 5000,
            )

    def _toggle(self) -> None:
        if self.controller.is_running:
            self.controller.stop_agent()
        else:
            self.controller.start_agent()

    def _show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window()

    def _quit(self) -> None:
        self.window._tray_active = False
        self.hide()
        self.controller.shutdown()
        QApplication.instance().quit()
