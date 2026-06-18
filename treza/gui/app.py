"""GUI application bootstrap."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .controller import AgentController
from .icons import app_icon
from .main_window import MainWindow
from .onboarding import OnboardingWizard
from .theme import apply_theme, watch_system_theme
from .tray import TrayIcon


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Treza")
    app.setApplicationDisplayName("Treza")
    app.setWindowIcon(app_icon())

    # Follow the OS light/dark theme (and live-update when it changes).
    apply_theme(app)
    watch_system_theme(app)

    controller = AgentController()
    window = MainWindow(controller)

    has_tray = QSystemTrayIcon.isSystemTrayAvailable()
    # With a tray, closing the window hides to tray and the app keeps serving.
    app.setQuitOnLastWindowClosed(not has_tray)
    tray = None
    if has_tray:
        tray = TrayIcon(controller, window)
        tray.show()

    controller.start_polling()

    # First run: no identities config yet -> guide the user through setup.
    if not controller.store.path.exists():
        OnboardingWizard(controller).exec()
        window._refresh_table()

    window.show()
    exit_code = app.exec()
    controller.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
