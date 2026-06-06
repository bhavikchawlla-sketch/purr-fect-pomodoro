"""
Main Window for Comnyang Desktop Pet.

Frameless, transparent, always-on-top window that displays the animated cat
sprite. Supports click-and-drag repositioning, right-click context menu,
floating Pomodoro timer label, gravity physics, wandering, petting, feeding,
floating emotion particles, and speech bubbles.
"""

from __future__ import annotations

import os
import math
import random
import time
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QLabel, QMenu,
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QAction, QFont, QColor,
    QPen, QCursor, QTransform,
)
from PyQt6.QtCore import (
    Qt, QPoint, QTimer, pyqtSignal, QRect,
)

from core.animation import AnimationEngine
from core.color_filter import COLOR_PRESETS, get_tinted_frames
from core.sound import SoundEngine


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
    - Right-click context menu (Pomodoro, color, petting, feeding, sound, quit)
    - Gravity physics and wandering pathfinding
    - Custom particle system (hearts, stars, Zzz, exclamation marks)
    - Retro speech bubbles with developer/productivity quotes
    - Petting interaction via cursor movements
    - Feeding interaction with falling treats
    """

    # Signals
    color_changed = pyqtSignal(str)
    pomodoro_start_requested = pyqtSignal()
    pomodoro_stop_requested = pyqtSignal()
    pomodoro_skip_requested = pyqtSignal()
    stretch_toggle_requested = pyqtSignal(bool)

    def __init__(self, animation_engine: AnimationEngine, parent=None):
        super().__init__(parent)

        self._animation_engine = animation_engine
        self._current_pixmap: QPixmap | None = None
        self._drag_position: QPoint | None = None
        self._timer_text: str = ""
        self._pomodoro_phase: str = "idle"
        self._current_color: str = "default"
        self._stretch_enabled: bool = True

        # --- Interactive Stats ---
        self._happiness: int = 50  # 0 to 100
        self._facing_left: bool = False

        # --- Sound Engine ---
        sounds_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds"
        )
        self._sound_engine = SoundEngine(sounds_dir)

        # --- Particles & Speech ---
        self._particles: list[dict] = []
        self._speech_text: str = ""
        self._speech_timer = QTimer(self)
        self._speech_timer.setSingleShot(True)
        self._speech_timer.timeout.connect(self._clear_speech)

        # --- Feeding Treat State ---
        self._treat_x: int = 0
        self._treat_y: int = -1  # -1 means no active treat falling

        # --- Physics State ---
        self._velocity_y: float = 0.0
        self._target_x: int = -1
        self._is_wandering: bool = False
        self._gravity_enabled: bool = True

        # --- Petting Detection State ---
        self._last_mouse_x: int = -1
        self._mouse_dir_changes: int = 0
        self._last_dir_change_time: float = 0.0
        self._last_mouse_dir: int = 0  # -1 left, 1 right

        # --- Window Setup ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Don't show in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setMouseTracking(True)  # Track hover movement for petting

        # Extra space at top: 50px for speech bubbles, 28px for timer label
        self._timer_area_height = 28
        self._speech_area_height = 50
        self._offset_y = self._timer_area_height + self._speech_area_height

        self.setFixedSize(WINDOW_SIZE, WINDOW_SIZE + self._offset_y)

        # Position at bottom-right of screen by default
        self._position_default()

        # Connect animation engine
        self._animation_engine.frame_changed.connect(self._on_frame_changed)

        # Build context menu
        self._build_context_menu()

        # Start Physics and Wander Timer (60 FPS)
        self._physics_timer = QTimer(self)
        self._physics_timer.timeout.connect(self._update_physics)
        self._physics_timer.start(16)  # ~60 FPS

        # Periodic dialogue timer (every 20s)
        self._dialogue_timer = QTimer(self)
        self._dialogue_timer.timeout.connect(self._on_dialogue_tick)
        self._dialogue_timer.start(20_000)

        # Welcome meow and speech
        QTimer.singleShot(1000, lambda: self._sound_engine.play("meow"))
        QTimer.singleShot(1200, lambda: self.set_speech("Hello! 🐱 Let's code!", 4))

        self.show()

    def _position_default(self) -> None:
        """Position the cat at the bottom-right of the primary screen."""
        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = geo.right() - WINDOW_SIZE - 60
                y = geo.bottom() - WINDOW_SIZE - self._offset_y - 20
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

        # --- Interactive Pet Info ---
        happiness_action = self._context_menu.addAction(f"💖  Happiness: {self._happiness}%")
        happiness_action.setEnabled(False)

        feed_action = QAction("🍖  Feed Treat", self)
        feed_action.triggered.connect(self.feed_treat)
        self._context_menu.addAction(feed_action)

        self._context_menu.addSeparator()

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

        # --- Audio & Stretch Reminder ---
        sound_state = "ON" if self._sound_engine.is_sound_enabled() else "OFF"
        self._action_sound = QAction(f"🔊  Sound Effects: {sound_state}", self)
        self._action_sound.triggered.connect(self._toggle_sound)
        self._context_menu.addAction(self._action_sound)

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
        self._build_context_menu()

    def _toggle_stretch(self) -> None:
        """Toggle stretch reminder on/off."""
        self._stretch_enabled = not self._stretch_enabled
        state = "ON" if self._stretch_enabled else "OFF"
        self._action_stretch.setText(f"🧘  Stretch Reminder: {state}")
        self.stretch_toggle_requested.emit(self._stretch_enabled)

    def _toggle_sound(self) -> None:
        """Toggle audio playback."""
        enabled = not self._sound_engine.is_sound_enabled()
        self._sound_engine.set_sound_enabled(enabled)
        state = "ON" if enabled else "OFF"
        self._action_sound.setText(f"🔊  Sound Effects: {state}")

    def _quit(self) -> None:
        """Quit the application."""
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    # --- Particles System ---

    def spawn_particle(self, x: int, y: int, char: str, color: QColor) -> None:
        """Spawn a floating particle inside the cat window."""
        self._particles.append({
            "x": float(x),
            "y": float(y),
            "vy": -1.0 - random.random() * 1.5,
            "vx": (random.random() - 0.5) * 1.0,
            "char": char,
            "color": color,
            "life": 1.0,
            "decay": 0.02 + random.random() * 0.02
        })

    # --- Speech Bubble API ---

    def set_speech(self, text: str, duration_sec: float = 4.0) -> None:
        """Set a retro speech bubble to display above the cat."""
        self._speech_text = text
        self._speech_timer.start(int(duration_sec * 1000))
        self.update()

    def _clear_speech(self) -> None:
        self._speech_text = ""
        self.update()

    def _on_dialogue_tick(self) -> None:
        """Periodically say cute or motivational messages."""
        if self._speech_text:
            return  # Don't overwrite active speech

        # Don't speak if dragged or stretching
        if self._drag_position is not None or self._animation_engine.get_state() == "stretch":
            return

        quotes_happy = [
            "We are making great progress! 💻",
            "Remember to commit your code! 🚀",
            "You are a coding wizard! ✨",
            "Clean code is happy code! 🧼",
            "Everything is compiling nicely! ✅",
        ]
        quotes_sad = [
            "I'm feeling a bit hungry... 🍗",
            "A little petting would be nice! 💖",
            "Need... more... treats... 🍖",
            "Slowing down? Take a sip of water! 💧",
        ]
        quotes_idle = [
            "Zzz... coding in my dreams... 😴",
            "Standing by for instructions! 🐱",
            "Need a break? Start the Pomodoro! 🍅",
        ]

        state = self._animation_engine.get_state()
        if state == "idle" and random.random() < 0.5:
            self.set_speech(random.choice(quotes_idle), 4)
        else:
            pool = quotes_happy if self._happiness >= 50 else quotes_sad
            self.set_speech(random.choice(pool), 4)

    # --- Interactive Actions ---

    def feed_treat(self) -> None:
        """Trigger the falling treat animation."""
        if self._treat_y >= 0:
            return  # Treat already active
        self._treat_x = WINDOW_SIZE // 2
        self._treat_y = self._speech_area_height
        self.set_speech("Oooh! Food! 🍖", 3)

    # --- Physics & Wander Tick (60 FPS) ---

    def _update_physics(self) -> None:
        # 1. Update treat falling
        if self._treat_y >= 0:
            self._treat_y += 3
            # Collision with cat mouth (at the body height level)
            target_mouth_y = self._offset_y + 40
            if self._treat_y >= target_mouth_y:
                self._treat_y = -1
                self._sound_engine.play("eat")
                self._happiness = min(100, self._happiness + 15)
                self._build_context_menu()
                self.set_speech("Munch munch... Yum! 🍖", 4)
                # Spawn star particles
                for _ in range(6):
                    self.spawn_particle(
                        WINDOW_SIZE // 2 + random.randint(-15, 15),
                        target_mouth_y + random.randint(-5, 5),
                        "★", QColor(255, 215, 0)
                    )

        # 2. Update particles
        active_particles = []
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] += math.sin(time.time() * 10) * 0.05
            p["life"] -= p["decay"]
            if p["life"] > 0:
                active_particles.append(p)
        self._particles = active_particles

        # 3. Update gravity
        try:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen and self._drag_position is None:
                geo = screen.availableGeometry()
                ground_y = geo.bottom() - WINDOW_SIZE - self._offset_y - 20

                if self.y() < ground_y:
                    self._velocity_y += 0.8
                    new_y = min(ground_y, int(self.y() + self._velocity_y))
                    self.move(self.x(), new_y)

                    if new_y == ground_y:
                        # Landed
                        if self._velocity_y > 4.0:
                            self._sound_engine.play("meow")
                            self.spawn_particle(
                                WINDOW_SIZE // 2,
                                self._offset_y + WINDOW_SIZE,
                                "!", QColor(255, 140, 0)
                            )
                        self._velocity_y = 0.0
                elif self.y() > ground_y:
                    self.move(self.x(), ground_y)
        except Exception:
            pass

        if (
            self._drag_position is None
            and self._animation_engine.get_state() not in ("stretch", "typing", "tracking", "focused")
        ):
            if self._is_wandering:
                speed = 2
                if self.x() < self._target_x:
                    self.move(min(self._target_x, self.x() + speed), self.y())
                    self._facing_left = False
                elif self.x() > self._target_x:
                    self.move(max(self._target_x, self.x() - speed), self.y())
                    self._facing_left = True

                if self.x() == self._target_x:
                    self._is_wandering = False
                    self._animation_engine.set_state("idle")
            else:
                # Wander check: 0.1% chance per frame (~6% chance per second)
                if random.random() < 0.001:
                    screen = QApplication.primaryScreen()
                    if screen:
                        geo = screen.availableGeometry()
                        self._target_x = random.randint(
                            geo.left() + 50, geo.right() - WINDOW_SIZE - 50
                        )
                        self._is_wandering = True
                        self._animation_engine.set_state("walk")

        # 5. Decrement happiness slightly over time (0.01 happiness points per frame)
        self._happiness = max(0, self._happiness - 0.005)

        self.update()

    # --- Timer Display ---

    def update_timer(self, text: str, phase: str = "idle") -> None:
        self._timer_text = text
        self._pomodoro_phase = phase

        if phase == "work":
            self._action_start_pomodoro.setText(f"▶  Working... {text}")
            self._action_start_pomodoro.setEnabled(False)
        elif phase == "break":
            self._action_start_pomodoro.setText(f"☕  Break... {text}")
            self._action_start_pomodoro.setEnabled(False)
            # Play notify/arpeggio sound on break start
            if text == "05:00" or text == "00:00":
                self._sound_engine.play("level_up")
        else:
            self._action_start_pomodoro.setText("▶  Start Work (25 min)")
            self._action_start_pomodoro.setEnabled(True)

        self.update()

    # --- Painting ---

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        # --- 1. Draw Speech Bubble ---
        if self._speech_text:
            self._paint_speech_bubble(painter)

        # --- 2. Draw Pomodoro text ---
        if self._timer_text:
            self._draw_timer_text(painter)

        # --- 3. Draw Treat (meat block) ---
        if self._treat_y >= 0:
            self._paint_treat(painter)

        # --- 4. Draw Cat Sprite (with direction flipping) ---
        if self._current_pixmap and not self._current_pixmap.isNull():
            dest_rect = QRect(
                0,
                self._offset_y,
                WINDOW_SIZE,
                WINDOW_SIZE,
            )
            if self._facing_left:
                # Flip sprite horizontally
                flipped = self._current_pixmap.transformed(
                    QTransform().scale(-1, 1)
                )
                painter.drawPixmap(dest_rect, flipped)
            else:
                painter.drawPixmap(dest_rect, self._current_pixmap)

        # --- 5. Draw Particles ---
        self._paint_particles(painter)

        painter.end()

    def _paint_speech_bubble(self, painter: QPainter) -> None:
        """Render a clean retro pixel-art styled speech bubble."""
        font = QFont("monospace", 10, QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text = self._speech_text

        # Compute dimensions
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()
        
        # Max bubble width constraint
        bubble_w = min(WINDOW_SIZE - 20, text_w + 16)
        bubble_h = text_h + 12
        bubble_x = (WINDOW_SIZE - bubble_w) // 2
        bubble_y = 5  # Top margin

        # Draw Bubble Rect
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QColor(255, 255, 230))  # Retro cream
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawRoundedRect(bubble_x, bubble_y, bubble_w, bubble_h, 6, 6)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Draw Little Bubble Tail pointing down to the cat
        tail_path = [
            QPoint(WINDOW_SIZE // 2 - 6, bubble_y + bubble_h),
            QPoint(WINDOW_SIZE // 2 + 6, bubble_y + bubble_h),
            QPoint(WINDOW_SIZE // 2, bubble_y + bubble_h + 8)
        ]
        painter.setBrush(QColor(255, 255, 230))
        painter.drawPolygon(tail_path)
        # Clear the top edge of the polygon so it merges with the bubble rect
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(WINDOW_SIZE // 2 - 5, bubble_y + bubble_h - 2, 10, 4)

        # Draw Text
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(
            QRect(bubble_x + 8, bubble_y + 6, bubble_w - 16, bubble_h - 12),
            Qt.AlignmentFlag.AlignCenter,
            text
        )

    def _paint_treat(self, painter: QPainter) -> None:
        """Draw a tiny pixel-art meat bone treat."""
        bx, by = self._treat_x, self._treat_y
        
        painter.setPen(Qt.PenStyle.NoPen)
        # Bone white ends
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRect(bx - 10, by - 6, 6, 6)
        painter.drawRect(bx - 10, by, 6, 6)
        painter.drawRect(bx + 4, by - 6, 6, 6)
        painter.drawRect(bx + 4, by, 6, 6)
        
        # Meat core
        painter.setBrush(QColor(180, 80, 80))
        painter.drawRect(bx - 6, by - 4, 12, 8)
        
        # Highlight
        painter.setBrush(QColor(220, 120, 120))
        painter.drawRect(bx - 4, by - 4, 8, 2)

    def _paint_particles(self, painter: QPainter) -> None:
        """Render all active floating particles."""
        font = QFont("monospace", 12, QFont.Weight.Bold)
        painter.setFont(font)
        
        for p in self._particles:
            color = QColor(p["color"])
            color.setAlpha(int(p["life"] * 255))
            painter.setPen(color)
            painter.drawText(int(p["x"]), int(p["y"]), p["char"])

    def _draw_timer_text(self, painter: QPainter) -> None:
        text = self._timer_text
        if not text:
            return

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

        pill_w = text_width + 16
        pill_h = text_height + 6
        pill_x = (WINDOW_SIZE - pill_w) // 2
        pill_y = self._speech_area_height + (self._timer_area_height - pill_h) // 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, 8, 8)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        painter.setPen(text_color)
        painter.drawText(
            pill_x + 8,
            pill_y + fm.ascent() + 3,
            text,
        )

    def _on_frame_changed(self, pixmap: QPixmap) -> None:
        self._current_pixmap = pixmap
        self.update()

    # --- Mouse & Interaction Events ---

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self._sound_engine.play("meow")
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._context_menu.exec(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        # 1. Drag repositioning
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_position is not None
        ):
            new_pos = event.globalPosition().toPoint() - self._drag_position
            self.move(new_pos)
            event.accept()
            return

        # 2. Hover Petting Detection
        mouse_x = event.position().x()
        now = time.time()

        if self._last_mouse_x >= 0:
            diff_x = mouse_x - self._last_mouse_x
            if abs(diff_x) > 5:
                # Detect current direction
                current_dir = 1 if diff_x > 0 else -1
                if current_dir != self._last_mouse_dir:
                    # Direction changed!
                    if now - self._last_dir_change_time < 0.8:
                        self._mouse_dir_changes += 1
                        if self._mouse_dir_changes >= 4:
                            # Triggers petting reaction
                            self._happiness = min(100, self._happiness + 5)
                            self._mouse_dir_changes = 0
                            self._sound_engine.play("purr")
                            self.set_speech("Purrr... ♥", 3)
                            self._build_context_menu()
                            # Spawn heart particles
                            self.spawn_particle(
                                int(event.position().x()),
                                int(event.position().y()),
                                "♥", QColor(255, 100, 100)
                            )
                    else:
                        self._mouse_dir_changes = 1
                    self._last_dir_change_time = now
                    self._last_mouse_dir = current_dir

        self._last_mouse_x = mouse_x

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()

    def enterEvent(self, event) -> None:
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        self._last_mouse_x = -1
        self._mouse_dir_changes = 0

    def leaveEvent(self, event) -> None:
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self._last_mouse_x = -1
