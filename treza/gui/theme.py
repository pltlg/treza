"""Light/dark theming that follows the OS color scheme.

Uses the Fusion style with a palette chosen from the system color scheme
(`QStyleHints.colorScheme`, Qt 6.5+). Fusion honors palettes fully, so this
gives reliable, consistent dark/light on Windows, macOS, and Linux — and updates
live when the user toggles their OS theme.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def _dark_palette() -> QPalette:
    p = QPalette()
    window = QColor(53, 53, 53)
    base = QColor(35, 35, 35)
    text = QColor(220, 220, 220)
    disabled = QColor(127, 127, 127)
    highlight = QColor(42, 130, 218)

    p.setColor(QPalette.Window, window)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Base, base)
    p.setColor(QPalette.AlternateBase, window)
    p.setColor(QPalette.ToolTipBase, window)
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, window)
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.BrightText, QColor(255, 80, 80))
    p.setColor(QPalette.Link, highlight)
    p.setColor(QPalette.Highlight, highlight)
    p.setColor(QPalette.HighlightedText, Qt.black)
    p.setColor(QPalette.PlaceholderText, disabled)
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, disabled)
    return p


def is_dark(app: QApplication) -> bool:
    """True if the OS is currently in dark mode."""
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:  # noqa: BLE001 — older Qt without colorScheme()
        return False


def apply_theme(app: QApplication) -> None:
    """Apply the palette matching the current OS color scheme."""
    app.setStyle("Fusion")
    if is_dark(app):
        app.setPalette(_dark_palette())
    else:
        app.setPalette(app.style().standardPalette())


def watch_system_theme(app: QApplication) -> None:
    """Re-apply the theme whenever the OS color scheme changes."""
    try:
        app.styleHints().colorSchemeChanged.connect(lambda _scheme: apply_theme(app))
    except Exception:  # noqa: BLE001
        pass
