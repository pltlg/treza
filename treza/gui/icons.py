"""Programmatically drawn status icons (no binary assets to ship/sign)."""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from ..agent.manager import AgentState

_COLORS = {
    AgentState.STOPPED: "#9aa0a6",            # grey
    AgentState.STARTING: "#f9ab00",           # amber
    AgentState.RUNNING: "#34a853",            # green
    AgentState.WAITING_CONFIRMATION: "#1a73e8",  # blue (acting now)
    AgentState.ERROR: "#ea4335",              # red
}


def status_pixmap(state: AgentState, size: int = 64) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(_COLORS.get(state, "#9aa0a6")))
    p.setPen(Qt.NoPen)
    margin = size // 8
    p.drawEllipse(QRect(margin, margin, size - 2 * margin, size - 2 * margin))
    p.end()
    return pm


def status_icon(state: AgentState, size: int = 64) -> QIcon:
    return QIcon(status_pixmap(state, size))


def app_icon(size: int = 256) -> QIcon:
    """A simple keyhole-on-disc app icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#1a73e8"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRect(0, 0, size, size))
    # keyhole
    p.setBrush(QColor("white"))
    r = size // 5
    cx = size // 2
    p.drawEllipse(QRect(cx - r, size // 4, 2 * r, 2 * r))
    stem = size // 12
    p.drawRect(QRect(cx - stem, size // 2, 2 * stem, size // 3))
    p.end()
    return QIcon(pm)
