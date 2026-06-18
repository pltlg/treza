"""First-run onboarding wizard (M4).

Walks a new user through: intro -> device check -> create first identity ->
how to enable the agent and export the key. Adding the identity is wired to the
controller; agent start/export happen back in the main window so the wizard
stays simple and side-effect-light.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from ..agent.identities import ED25519, NIST256, SshIdentity
from .controller import AgentController


class _IntroPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome to Treza")
        layout = QVBoxLayout(self)
        text = QLabel(
            "Treza lets you use your Trezor as an SSH key.\n\n"
            "Your private key never leaves the device — every login is confirmed "
            "on the Trezor itself.\n\n"
            "This wizard will help you connect your device and create your first "
            "SSH identity."
        )
        text.setWordWrap(True)
        layout.addWidget(text)


class _DevicePage(QWizardPage):
    def __init__(self, controller: AgentController) -> None:
        super().__init__()
        self.setTitle("Connect your Trezor")
        layout = QVBoxLayout(self)
        self._label = QLabel("Checking…")
        self._label.setWordWrap(True)
        layout.addWidget(self._label)
        hint = QLabel(
            "Plug in and unlock your Trezor. On Linux you may need udev rules; "
            "on Windows, disable the built-in ssh-agent service (see the README)."
        )
        hint.setWordWrap(True)
        hint.setEnabled(False)  # subdued but palette-aware
        layout.addWidget(hint)
        controller.deviceStatusChanged.connect(lambda s: self._label.setText(s.summary))


class _IdentityPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Create your first SSH identity")
        self.setSubTitle("A separate key is derived per user@host.")
        self._user = QLineEdit()
        self._host = QLineEdit()
        self._host.setPlaceholderText("e.g. github.com")
        self._port = QSpinBox()
        self._port.setRange(0, 65535)
        self._port.setSpecialValueText("(default)")
        self._curve = QComboBox()
        self._curve.addItem("Ed25519 (recommended)", ED25519)
        self._curve.addItem("NIST P-256 (ecdsa)", NIST256)

        form = QFormLayout(self)
        form.addRow("User", self._user)
        form.addRow("Host", self._host)
        form.addRow("Port", self._port)
        form.addRow("Key type", self._curve)

        self._host.textChanged.connect(self.completeChanged)

    def isComplete(self) -> bool:  # noqa: N802 (Qt signature)
        return bool(self._host.text().strip())

    def identity(self) -> SshIdentity:
        return SshIdentity(
            user=self._user.text().strip(),
            host=self._host.text().strip(),
            port=self._port.value() or None,
            curve=self._curve.currentData(),
        )


class _FinishPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("You're set")
        layout = QVBoxLayout(self)
        pipe = (
            r"\\.\pipe\openssh-ssh-agent" if sys.platform == "win32" else "$SSH_AUTH_SOCK"
        )
        text = QLabel(
            "Click Finish to open Treza.\n\n"
            "Then press “Start agent”, select your identity, and use "
            "“Copy public key” to add it to a server or GitHub.\n\n"
            f"Standard SSH clients connect automatically via {pipe}."
        )
        text.setWordWrap(True)
        layout.addWidget(text)


class OnboardingWizard(QWizard):
    """Returns the created identity (or None) after the user finishes."""

    def __init__(self, controller: AgentController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Treza setup")
        self._intro = _IntroPage()
        self._device = _DevicePage(controller)
        self._identity = _IdentityPage()
        self._finish = _FinishPage()
        for page in (self._intro, self._device, self._identity, self._finish):
            self.addPage(page)

    def accept(self) -> None:  # noqa: N802 (Qt signature)
        try:
            self.controller.add_identity(self._identity.identity())
        except ValueError:
            pass
        super().accept()
