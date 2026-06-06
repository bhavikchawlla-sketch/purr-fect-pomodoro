"""
Animation Engine for Comnyang Desktop Pet.

Manages sprite frame cycling using QTimer, supports multiple animation states,
and preloads all frames for smooth transitions.
"""

import os
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap


class AnimationEngine(QObject):
    """
    Sprite animation engine that cycles through frames using a QTimer.

    Supports multiple named animation states (e.g., 'idle', 'typing', 'tracking').
    Each state maps to a list of QPixmap frames loaded from a directory.

    Signals:
        frame_changed(QPixmap): Emitted on each frame advance with the new pixmap.
    """

    frame_changed = pyqtSignal(QPixmap)

    STATE_PRIORITY = {
        'stretch': 6,
        'typing': 5,
        'tracking': 4,
        'walk': 3,
        'focused': 2,
        'idle': 1,
    }

    def __init__(self, sprites_dir: str, fps: int = 7, parent=None):
        """
        Initialize the animation engine.

        Args:
            sprites_dir: Root directory containing state subdirectories
                         (e.g., sprites_dir/idle/, sprites_dir/typing/).
            fps: Frames per second for animation playback.
            parent: Parent QObject.
        """
        super().__init__(parent)

        self._sprites_dir = sprites_dir
        self._fps = fps
        self._current_state = 'idle'
        self._current_frame_index = 0

        # Dict[state_name, List[QPixmap]]
        self._frames: dict[str, list[QPixmap]] = {}

        # Load all sprite frames
        self._load_all_frames()

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)

    def _load_all_frames(self) -> None:
        """Load all sprite frames from the sprites directory."""
        if not os.path.isdir(self._sprites_dir):
            return

        for state_name in os.listdir(self._sprites_dir):
            state_dir = os.path.join(self._sprites_dir, state_name)
            if not os.path.isdir(state_dir):
                continue

            frames = []
            # Sort files to ensure consistent frame ordering
            png_files = sorted(
                f for f in os.listdir(state_dir)
                if f.lower().endswith('.png')
            )

            for filename in png_files:
                filepath = os.path.join(state_dir, filename)
                pixmap = QPixmap(filepath)
                if not pixmap.isNull():
                    frames.append(pixmap)

            if frames:
                self._frames[state_name] = frames

    def reload_frames(self, state: str, pixmaps: list[QPixmap]) -> None:
        """
        Replace frames for a given state with pre-built QPixmaps.

        Used by the color filter to inject tinted frames without
        touching the filesystem.

        Args:
            state: Animation state name.
            pixmaps: List of QPixmap frames.
        """
        if pixmaps:
            self._frames[state] = pixmaps
            # Reset frame index if we're currently in this state
            if self._current_state == state:
                self._current_frame_index = 0
                self._emit_current_frame()

    def reload_all_from_dir(self) -> None:
        """Reload all frames from the sprites directory."""
        self._frames.clear()
        self._load_all_frames()
        self._current_frame_index = 0
        self._emit_current_frame()

    def set_state(self, state: str) -> None:
        """
        Switch to a different animation state.

        Resets the frame index to 0 and immediately emits the first
        frame of the new state.

        Args:
            state: Name of the animation state (e.g., 'idle', 'typing').
        """
        if state == self._current_state:
            return

        if state not in self._frames:
            # Fall back to idle if the requested state has no frames
            if 'idle' in self._frames:
                state = 'idle'
            else:
                return

        self._current_state = state
        self._current_frame_index = 0
        self._emit_current_frame()

    def get_state(self) -> str:
        """Return the current animation state name."""
        return self._current_state

    def get_current_frame(self) -> QPixmap | None:
        """Return the current frame QPixmap, or None if no frames loaded."""
        frames = self._frames.get(self._current_state, [])
        if not frames:
            return None
        return frames[self._current_frame_index % len(frames)]

    def start(self) -> None:
        """Start the animation timer."""
        interval_ms = max(1, 1000 // self._fps)
        self._timer.start(interval_ms)
        self._emit_current_frame()

    def stop(self) -> None:
        """Stop the animation timer."""
        self._timer.stop()

    def is_running(self) -> bool:
        """Return True if the animation timer is active."""
        return self._timer.isActive()

    def set_fps(self, fps: int) -> None:
        """Change the animation speed."""
        self._fps = max(1, fps)
        if self._timer.isActive():
            self._timer.setInterval(1000 // self._fps)

    def has_state(self, state: str) -> bool:
        """Check if frames exist for a given state."""
        return state in self._frames and len(self._frames[state]) > 0

    def available_states(self) -> list[str]:
        """Return list of states that have loaded frames."""
        return list(self._frames.keys())

    def _advance_frame(self) -> None:
        """Advance to the next frame and emit the signal."""
        frames = self._frames.get(self._current_state, [])
        if not frames:
            return

        self._current_frame_index = (
            (self._current_frame_index + 1) % len(frames)
        )
        self._emit_current_frame()

    def _emit_current_frame(self) -> None:
        """Emit the frame_changed signal with the current frame."""
        frame = self.get_current_frame()
        if frame is not None:
            self.frame_changed.emit(frame)
