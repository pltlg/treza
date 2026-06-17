"""Dialog for creating a new SSH identity."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
)

from ..agent.identities import ED25519, NIST256, SshIdentity


class AddIdentityDialog(QDialog):
    """Collect user / host / port / curve for a new identity."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add SSH identity")

        self._user = QLineEdit()
        self._user.setPlaceholderText("e.g. git or your login name")
        self._host = QLineEdit()
        self._host.setPlaceholderText("e.g. github.com or server.example.com")
        self._port = QSpinBox()
        self._port.setRange(0, 65535)
        self._port.setSpecialValueText("(default)")
        self._port.setValue(0)
        self._curve = QComboBox()
        self._curve.addItem("Ed25519 (recommended)", ED25519)
        self._curve.addItem("NIST P-256 (ecdsa)", NIST256)

        form = QFormLayout(self)
        form.addRow("User", self._user)
        form.addRow("Host", self._host)
        form.addRow("Port", self._port)
        form.addRow("Key type", self._curve)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        if not self._host.text().strip():
            self._host.setFocus()
            return
        self.accept()

    def identity(self) -> SshIdentity:
        port = self._port.value() or None
        return SshIdentity(
            user=self._user.text().strip(),
            host=self._host.text().strip(),
            port=port,
            curve=self._curve.currentData(),
        )
