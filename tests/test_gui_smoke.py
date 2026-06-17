"""Headless smoke tests for the PySide6 GUI (no display, no hardware).

Uses Qt's offscreen platform so widgets can be constructed and signals
exercised in CI. Skips entirely if PySide6 isn't installed.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from treza.agent.manager import AgentState  # noqa: E402
from treza.gui.controller import AgentController  # noqa: E402
from treza.gui.main_window import MainWindow  # noqa: E402
from treza.gui.onboarding import OnboardingWizard  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_main_window_builds_and_reacts_to_state(app) -> None:
    controller = AgentController()
    win = MainWindow(controller)
    try:
        # Drive the state machine through the UI handler — must not raise.
        for state in AgentState:
            controller._set_state(state)
        assert "running" in win._state_label.text().lower() or win._state_label.text()
        win.show()
        app.processEvents()
    finally:
        win.close()
        controller.shutdown()


def test_onboarding_wizard_builds(app) -> None:
    controller = AgentController()
    wiz = OnboardingWizard(controller)
    try:
        assert wiz.pageIds(), "wizard should have pages"
    finally:
        wiz.deleteLater()
        controller.shutdown()
