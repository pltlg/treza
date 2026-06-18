"""Treza main window: device status, agent control, identity management."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..agent.device import DeviceStatus
from ..agent.identities import SshIdentity
from ..agent.manager import AgentState
from .add_dialog import AddIdentityDialog
from .controller import AgentController
from .icons import status_pixmap

_STATE_TEXT = {
    AgentState.STOPPED: "Agent stopped",
    AgentState.STARTING: "Agent starting…",
    AgentState.RUNNING: "Agent running",
    AgentState.WAITING_CONFIRMATION: "Waiting for confirmation on your Trezor…",
    AgentState.ERROR: "Agent error",
}


class MainWindow(QMainWindow):
    def __init__(self, controller: AgentController) -> None:
        super().__init__()
        self.controller = controller
        self._export_mode = "copy"
        self.setWindowTitle("Treza — Trezor SSH")
        self.resize(640, 460)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Device status
        self._device_label = QLabel("Checking for Trezor…")
        self._device_label.setStyleSheet("font-weight: 600;")
        root.addWidget(self._device_label)

        # Agent status + control
        agent_row = QHBoxLayout()
        self._state_dot = QLabel()
        self._state_dot.setFixedSize(18, 18)
        self._state_label = QLabel(_STATE_TEXT[AgentState.STOPPED])
        self._toggle_btn = QPushButton("Start agent")
        self._toggle_btn.clicked.connect(self._toggle_agent)
        agent_row.addWidget(self._state_dot)
        agent_row.addWidget(self._state_label, 1)
        agent_row.addWidget(self._toggle_btn)
        root.addLayout(agent_row)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setEnabled(False)  # subdued, but palette-aware (legible in dark mode)
        root.addWidget(self._hint)

        # Identity table
        root.addWidget(QLabel("SSH identities"))
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Identity", "Key type"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._update_action_buttons)
        root.addWidget(self._table, 1)

        # Identity actions
        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("Add…")
        self._remove_btn = QPushButton("Remove")
        self._copy_btn = QPushButton("Copy public key")
        self._save_btn = QPushButton("Save public key…")
        self._add_btn.clicked.connect(self._add_identity)
        self._remove_btn.clicked.connect(self._remove_identity)
        self._copy_btn.clicked.connect(lambda: self._export("copy"))
        self._save_btn.clicked.connect(lambda: self._export("file"))
        for b in (self._add_btn, self._remove_btn, self._copy_btn, self._save_btn):
            btn_row.addWidget(b)
        root.addLayout(btn_row)

        # Wire controller signals
        controller.stateChanged.connect(self._on_state)
        controller.deviceStatusChanged.connect(self._on_device_status)
        controller.errorOccurred.connect(self._on_error)
        controller.publicKeyReady.connect(self._on_public_key)

        self._refresh_table()
        self._on_state(controller.state)

    # -- table --------------------------------------------------------------

    def _refresh_table(self) -> None:
        identities = self.controller.identities()
        self._table.setRowCount(len(identities))
        for row, ident in enumerate(identities):
            name_item = QTableWidgetItem(str(ident))
            name_item.setData(Qt.UserRole, ident)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem(ident.curve))
        self._update_action_buttons()

    def _selected_identity(self) -> SshIdentity | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._table.item(rows[0].row(), 0).data(Qt.UserRole)

    # -- actions ------------------------------------------------------------

    def _add_identity(self) -> None:
        dlg = AddIdentityDialog(self)
        if dlg.exec():
            try:
                self.controller.add_identity(dlg.identity())
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid identity", str(exc))
                return
            self._refresh_table()

    def _remove_identity(self) -> None:
        ident = self._selected_identity()
        if ident is None:
            return
        if QMessageBox.question(self, "Remove identity", f"Remove {ident}?") == \
                QMessageBox.StandardButton.Yes:
            self.controller.remove_identity(ident)
            self._refresh_table()

    def _export(self, mode: str) -> None:
        ident = self._selected_identity()
        if ident is None:
            return
        if not self.controller.is_running:
            QMessageBox.information(
                self, "Start the agent",
                "Start the agent first — the public key is read from it "
                "(and confirmed on your Trezor).",
            )
            return
        self._export_mode = mode
        self.statusBar().showMessage("Confirm on your Trezor to export the public key…")
        self.controller.export_public_key_async(ident)

    def _on_public_key(self, identity: SshIdentity, line: str) -> None:
        self.statusBar().clearMessage()
        if self._export_mode == "copy":
            QApplication.clipboard().setText(line)
            QMessageBox.information(
                self, "Public key copied",
                "The public key was copied to your clipboard:\n\n" + line,
            )
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save public key", f"{identity.host}.pub", "Public key (*.pub)"
            )
            if path:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                QMessageBox.information(self, "Saved", f"Public key written to:\n{path}")

    def _toggle_agent(self) -> None:
        if self.controller.is_running:
            self.controller.stop_agent()
        else:
            self.controller.start_agent()

    # -- signal handlers ----------------------------------------------------

    def _on_state(self, state: AgentState) -> None:
        self._state_dot.setPixmap(status_pixmap(state, 18))
        self._state_label.setText(_STATE_TEXT.get(state, str(state)))
        running = state in (AgentState.RUNNING, AgentState.WAITING_CONFIRMATION)
        self._toggle_btn.setText("Stop agent" if running else "Start agent")
        if running and self.controller.sock_path:
            self._hint.setText(f"Listening on {self.controller.sock_path}")
        elif state is AgentState.STOPPED:
            self._hint.setText("")
        self._update_action_buttons()

    def _on_device_status(self, status: DeviceStatus) -> None:
        self._device_label.setText(status.summary)

    def _on_error(self, message: str) -> None:
        self.statusBar().clearMessage()
        QMessageBox.warning(self, "Treza", message)

    def _update_action_buttons(self) -> None:
        has_sel = self._selected_identity() is not None
        running = self.controller.is_running
        self._remove_btn.setEnabled(has_sel)
        self._copy_btn.setEnabled(has_sel and running)
        self._save_btn.setEnabled(has_sel and running)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        # Hide to tray instead of quitting, if a tray is active.
        if getattr(self, "_tray_active", False):
            event.ignore()
            self.hide()
        else:
            event.accept()
