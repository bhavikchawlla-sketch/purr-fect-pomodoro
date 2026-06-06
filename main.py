#!/usr/bin/env python3
"""
Comnyang — Desktop Pet Cat Application

A pixel-art cat that lives on your Linux desktop, reacts to your input,
and helps with productivity.

Usage:
    python main.py

Inspired by Comnyang. Built with PyQt6, pynput, psutil, and Pillow.
"""

import os
import sys

# Force X11 backend for reliable transparency and input tracking on Linux.
# Must be set before any Qt imports.
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from core.sprite_generator import generate_if_missing
from core.animation import AnimationEngine
from core.color_filter import COLOR_PRESETS, get_tinted_frames
from core.window import CatWindow
from input_tracking.tracker import InputTracker
from productivity.pomodoro import PomodoroTimer
from productivity.stretch_reminder import StretchReminder
from monitoring.process_monitor import ProcessMonitor


def get_sprites_dir() -> str:
    """Return the absolute path to the sprites directory."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")


class Comnyang:
    """
    Main application controller that wires all components together.

    Components:
    - AnimationEngine: Cycles through sprite frames
    - CatWindow: Displays the cat and handles user interaction
    - InputTracker: Detects keyboard/mouse input
    - ProcessMonitor: Detects AI/developer tools
    - PomodoroTimer: 25/5 work-break timer
    - StretchReminder: 45-minute stretch notifications

    State Priority (highest to lowest):
        stretch > typing > tracking > focused > idle
    """

    def __init__(self):
        self._sprites_dir = get_sprites_dir()

        # Generate pixel-art sprites if they don't exist
        print("🐱 Checking sprites...")
        generate_if_missing(self._sprites_dir)
        print("🐱 Sprites ready!")

        # --- Core Components ---
        self._animation = AnimationEngine(self._sprites_dir, fps=7)
        self._window = CatWindow(self._animation)
        self._input_tracker = InputTracker()
        self._process_monitor = ProcessMonitor()
        self._pomodoro = PomodoroTimer()
        self._stretch = StretchReminder()

        # --- Internal State ---
        self._current_color = "default"
        self._ai_tools_active = False
        self._is_stretching = False

        # Timer to revert from stretch animation
        self._stretch_revert_timer = QTimer()
        self._stretch_revert_timer.setSingleShot(True)
        self._stretch_revert_timer.timeout.connect(self._end_stretch_animation)

        # --- Connect Signals ---
        self._connect_input_tracking()
        self._connect_process_monitor()
        self._connect_pomodoro()
        self._connect_stretch()
        self._connect_window()

        # --- Start Everything ---
        self._animation.start()
        self._input_tracker.start()
        self._process_monitor.start()
        self._stretch.start()

        print("🐱 Comnyang is alive! Right-click the cat for options.")

    def _connect_input_tracking(self) -> None:
        """Connect input tracker signals to animation state changes."""
        self._input_tracker.typing_detected.connect(self._on_typing)
        self._input_tracker.mouse_activity_detected.connect(self._on_mouse)
        self._input_tracker.input_idle.connect(self._on_idle)

    def _connect_process_monitor(self) -> None:
        """Connect process monitor to focused mode."""
        self._process_monitor.ai_tool_detected.connect(self._on_ai_tool)

    def _connect_pomodoro(self) -> None:
        """Connect Pomodoro timer to window display."""
        self._pomodoro.tick.connect(self._on_pomodoro_tick)
        self._pomodoro.phase_changed.connect(self._on_pomodoro_phase)

    def _connect_stretch(self) -> None:
        """Connect stretch reminder to animation."""
        self._stretch.stretch_time.connect(self._on_stretch_time)

    def _connect_window(self) -> None:
        """Connect window UI actions to controllers."""
        self._window.pomodoro_start_requested.connect(self._pomodoro.start)
        self._window.pomodoro_stop_requested.connect(self._on_pomodoro_stop)
        self._window.pomodoro_skip_requested.connect(self._pomodoro.skip)
        self._window.color_changed.connect(self._on_color_changed)
        self._window.stretch_toggle_requested.connect(self._on_stretch_toggle)

    # --- Input Handling ---

    def _on_typing(self) -> None:
        """Handle keyboard typing detection."""
        if self._is_stretching:
            return  # Stretch has highest priority
        self._animation.set_state("typing")

    def _on_mouse(self) -> None:
        """Handle mouse activity detection."""
        if self._is_stretching:
            return
        current = self._animation.get_state()
        # Don't override typing with mouse
        if current != "typing":
            self._animation.set_state("tracking")

    def _on_idle(self) -> None:
        """Handle input idle — return to focused or idle state."""
        if self._is_stretching:
            return
        if self._ai_tools_active:
            self._animation.set_state("focused")
        else:
            self._animation.set_state("idle")

    # --- Process Monitoring ---

    def _on_ai_tool(self, detected: bool) -> None:
        """Handle AI tool detection state change."""
        self._ai_tools_active = detected
        if self._is_stretching:
            return
        # Only switch to focused if currently idle
        current = self._animation.get_state()
        if detected and current == "idle":
            self._animation.set_state("focused")
        elif not detected and current == "focused":
            self._animation.set_state("idle")

    # --- Pomodoro ---

    def _on_pomodoro_tick(self, remaining: int) -> None:
        """Update timer display on each Pomodoro tick."""
        time_str = self._pomodoro.format_time()
        self._window.update_timer(time_str, self._pomodoro.get_phase())

    def _on_pomodoro_phase(self, phase: str) -> None:
        """Handle Pomodoro phase transitions."""
        if phase == "idle":
            self._window.update_timer("", "idle")
        elif phase == "work":
            self._window.update_timer(
                self._pomodoro.format_time(), "work"
            )
        elif phase == "break":
            self._window.update_timer(
                self._pomodoro.format_time(), "break"
            )

    def _on_pomodoro_stop(self) -> None:
        """Stop Pomodoro and clear display."""
        self._pomodoro.stop()
        self._window.update_timer("", "idle")

    # --- Stretch Reminder ---

    def _on_stretch_time(self) -> None:
        """Handle stretch reminder trigger."""
        self._is_stretching = True
        self._animation.set_state("stretch")
        self._window._sound_engine.play("level_up")
        self._window.set_speech("Time to stretch! 🧘", 5)
        # Revert after 10 seconds
        self._stretch_revert_timer.start(10_000)

    def _end_stretch_animation(self) -> None:
        """Revert from stretch animation back to normal state."""
        self._is_stretching = False
        self._window._sound_engine.play("meow")
        self._window.set_speech("Ah, much better!", 3)
        if self._ai_tools_active:
            self._animation.set_state("focused")
        else:
            self._animation.set_state("idle")

    def _on_stretch_toggle(self, enabled: bool) -> None:
        """Toggle stretch reminder on/off."""
        if enabled:
            self._stretch.start()
        else:
            self._stretch.stop()

    # --- Color Customization ---

    def _on_color_changed(self, color_name: str) -> None:
        """Apply color tint to all sprite states."""
        self._current_color = color_name
        color_rgb = COLOR_PRESETS.get(color_name)

        if color_rgb is None:
            # Default: reload original sprites
            self._animation.reload_all_from_dir()
            return

        # Tint each animation state
        for state_name in ["idle", "typing", "tracking", "focused", "stretch", "walk"]:
            state_dir = os.path.join(self._sprites_dir, state_name)
            if os.path.isdir(state_dir):
                tinted_pixmaps = get_tinted_frames(state_dir, color_rgb)
                self._animation.reload_frames(state_name, tinted_pixmaps)

    def cleanup(self) -> None:
        """Clean up all resources before exit."""
        self._input_tracker.stop()
        self._process_monitor.stop()
        self._pomodoro.stop()
        self._stretch.stop()
        self._animation.stop()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Comnyang")
    app.setQuitOnLastWindowClosed(True)

    # Create the desktop pet
    pet = Comnyang()

    # Clean up on exit
    app.aboutToQuit.connect(pet.cleanup)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
