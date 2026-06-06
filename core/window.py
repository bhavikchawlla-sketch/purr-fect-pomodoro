"""
Main Window for Comnyang Desktop Pet.

Frameless, transparent, always-on-top window that displays the animated cat
sprite. Supports click-and-drag repositioning, right-click context menu,
and a floating Pomodoro timer label.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QMenu, QSystemTrayIcon,
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QAction, QIcon, QFont, QColor,
    QPen, QCursor,
)
from PyQt6.QtCore import (
    Qt, QPoint, QTimer, pyqtSignal, QSize, QRect,
)

from core.animation import AnimationEngine
from core.color_filter import COLOR_PRESETS, get_tinted_frames


# Display scale: each pixel-art pixel rendered at this size
DISPLAY_SCALE = 3
SPRITE_SIZE = 64
WINDOW_SIZE = SPRITE_SIZE * DISPLAY_SCALE  # 192px


class CatWindow(QWidget):
    """
    The main transparent window that displays the desktop pet cat.

    Features:
    - Frameless, transparent, always-on-top overlay
    - Click-and-drag repositioning
    - Right-click context menu (Pomodoro, color, quit)
    - Floating timer label above the cat
    - Smooth sprite rendering with pixel-art scaling
    """

    # Emitted when user selects a color from the context menu
    color_changed = pyqtSignal(str)
    # Emitted when user toggles Pomodoro from context menu
    pomodoro_start_requested = pyqtSignal()
    pomodoro_stop_requested = pyqtSignal()
    pomodoro_skip_requested = pyqtSignal()
    # Emitted when stretch reminder toggle is requested
    stretch_toggle_requested = pyqtSignal(bool)

    def __init__(self, animation_engine: AnimationEngine, parent=None):
        """
        Initialize the cat window.

        Args:
            animation_engine: The AnimationEngine providing sprite frames.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._animation_engine = animation_engine
        self._current_pixmap: QPixmap | None = None
        self._drag_position: QPoint | None = None
        self._timer_text: str = ""
        self._pomodoro_phase: str = "idle"
        self._current_color: str = "default"
        self._stretch_enabled: bool = True

        # --- Window Setup ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Don't show in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # Window size: sprite area + space for timer text above
        self._timer_area_height = 28
        self.setFixedSize(WINDOW_SIZE, WINDOW_SIZE + self._timer_area_height)

        # Position at bottom-right of screen by default
        self._position_default()

        # Connect animation engine
        self._animation_engine.frame_changed.connect(self._on_frame_changed)

        # Build context menu
        self._build_context_menu()

        self.show()

    def _position_default(self) -> None:
        """Position the cat at the bottom-right of the primary screen."""
        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = geo.right() - WINDOW_SIZE - 60
                y = geo.bottom() - WINDOW_SIZE - self._timer_area_height - 20
                self.move(x, y)
        except Exception:
            self.move(800, 500)

    def _build_context_menu(self) -> None:
        """Build the right-click context menu."""
        self._context_menu = QMenu(self)
        self._context_menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                color: #E0E0E0;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 6px 0px;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
                margin: 2px 6px;
            }
            QMenu::item:selected {
                background-color: #4A90D9;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #555;
                margin: 4px 12px;
            }
        """)

        # --- Pomodoro Section ---
        pomodoro_header = self._context_menu.addAction("🍅  Pomodoro Timer")
        pomodoro_header.setEnabled(False)

        self._action_start_pomodoro = QAction("▶  Start Work (25 min)", self)
        self._action_start_pomodoro.triggered.connect(
            self.pomodoro_start_requested.emit
        )
        self._context_menu.addAction(self._action_start_pomodoro)

        self._action_stop_pomodoro = QAction("⏹  Stop Timer", self)
        self._action_stop_pomodoro.triggered.connect(
            self.pomodoro_stop_requested.emit
        )
        self._context_menu.addAction(self._action_stop_pomodoro)

        self._action_skip_pomodoro = QAction("⏭  Skip Phase", self)
        self._action_skip_pomodoro.triggered.connect(
            self.pomodoro_skip_requested.emit
        )
        self._context_menu.addAction(self._action_skip_pomodoro)

        self._context_menu.addSeparator()

        # --- Stretch Reminder ---
        self._action_stretch = QAction("🧘  Stretch Reminder: ON", self)
        self._action_stretch.triggered.connect(self._toggle_stretch)
        self._context_menu.addAction(self._action_stretch)

        self._context_menu.addSeparator()

        # --- Color Submenu ---
        color_menu = self._context_menu.addMenu("🎨  Change Color")
        color_menu.setStyleSheet(self._context_menu.styleSheet())
        for color_name in COLOR_PRESETS:
            display_name = color_name.capitalize()
            if color_name == self._current_color:
                display_name = f"✓ {display_name}"
            action = QAction(display_name, self)
            action.setData(color_name)
            action.triggered.connect(
                lambda checked, cn=color_name: self._on_color_selected(cn)
            )
            color_menu.addAction(action)

        self._context_menu.addSeparator()

        # --- Quit ---
        quit_action = QAction("✕  Quit Comnyang", self)
        quit_action.triggered.connect(self._quit)
        self._context_menu.addAction(quit_action)

    def _on_color_selected(self, color_name: str) -> None:
        """Handle color selection from context menu."""
        self._current_color = color_name
        self.color_changed.emit(color_name)
        # Rebuild menu to update checkmarks
        self._build_context_menu()

    def _toggle_stretch(self) -> None:
        """Toggle stretch reminder on/off."""
        self._stretch_enabled = not self._stretch_enabled
        state = "ON" if self._stretch_enabled else "OFF"
        self._action_stretch.setText(f"🧘  Stretch Reminder: {state}")
        self.stretch_toggle_requested.emit(self._stretch_enabled)

    def _quit(self) -> None:
        """Quit the application."""
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    # --- Timer Display ---

    def update_timer(self, text: str, phase: str = "idle") -> None:
        """
        Update the timer text displayed above the cat.

        Args:
            text: Timer text (e.g., '24:59') or empty string to hide.
            phase: Current Pomodoro phase for styling ('work', 'break', 'idle').
        """
        self._timer_text = text
        self._pomodoro_phase = phase

        # Update menu text
        if phase == "work":
            self._action_start_pomodoro.setText(f"▶  Working... {text}")
            self._action_start_pomodoro.setEnabled(False)
        elif phase == "break":
            self._action_start_pomodoro.setText(f"☕  Break... {text}")
            self._action_start_pomodoro.setEnabled(False)
        else:
            self._action_start_pomodoro.setText("▶  Start Work (25 min)")
            self._action_start_pomodoro.setEnabled(True)

        self.update()

    # --- Painting ---

    def paintEvent(self, event) -> None:
        """Custom paint: draw timer text + scaled sprite with transparency."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # Keep pixel art crispy — no smoothing
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, False
        )

        # --- Draw timer text above the cat ---
        if self._timer_text:
            self._draw_timer_text(painter)

        # --- Draw the cat sprite ---
        if self._current_pixmap and not self._current_pixmap.isNull():
            dest_rect = QRect(
                0,
                self._timer_area_height,
                WINDOW_SIZE,
                WINDOW_SIZE,
            )
            painter.drawPixmap(dest_rect, self._current_pixmap)

        painter.end()

    def _draw_timer_text(self, painter: QPainter) -> None:
        """Draw the Pomodoro timer text with a pill-shaped background."""
        text = self._timer_text
        if not text:
            return

        # Choose color based on phase
        if self._pomodoro_phase == "work":
            bg_color = QColor(220, 60, 60, 200)    # Red pill
            text_color = QColor(255, 255, 255)
        elif self._pomodoro_phase == "break":
            bg_color = QColor(60, 179, 113, 200)    # Green pill
            text_color = QColor(255, 255, 255)
        else:
            bg_color = QColor(80, 80, 80, 180)      # Grey pill
            text_color = QColor(200, 200, 200)

        font = QFont("monospace", 11, QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()

        # Pill background
        pill_w = text_width + 16
        pill_h = text_height + 6
        pill_x = (WINDOW_SIZE - pill_w) // 2
        pill_y = (self._timer_area_height - pill_h) // 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, 8, 8)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Text
        painter.setPen(text_color)
        painter.drawText(
            pill_x + 8,
            pill_y + fm.ascent() + 3,
            text,
        )

    # --- Frame Updates ---

    def _on_frame_changed(self, pixmap: QPixmap) -> None:
        """Handle new frame from animation engine."""
        self._current_pixmap = pixmap
        self.update()

    # --- Drag Handling ---

    def mousePressEvent(self, event) -> None:
        """Start drag on left click, show menu on right click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._context_menu.exec(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """Move the window while dragging."""
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_position is not None
        ):
            new_pos = event.globalPosition().toPoint() - self._drag_position
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """End drag."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()

    def enterEvent(self, event) -> None:
        """Change cursor on hover."""
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def leaveEvent(self, event) -> None:
        """Reset cursor."""
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
