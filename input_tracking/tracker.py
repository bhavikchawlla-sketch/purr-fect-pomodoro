"""
Input tracking module for the Comnyang desktop pet.

Monitors keyboard and mouse activity using pynput listeners running in daemon
threads, and exposes state changes as PyQt6 signals emitted safely on the Qt
main thread via a polling QTimer.

Thread-safety strategy
----------------------
* pynput callbacks (running in background threads) only perform simple float /
  string assignments — these are atomic on CPython thanks to the GIL.
* A fast QTimer (200 ms) running on the Qt event-loop reads those values and
  emits the appropriate Qt signals, keeping all signal emission on the main
  thread.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from pynput import keyboard, mouse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IDLE_THRESHOLD_SECONDS: float = 3.0
"""Duration of inactivity (in seconds) before the user is considered idle."""

_POLL_INTERVAL_MS: int = 200
"""How often the QTimer polls the shared state (milliseconds)."""


class InputTracker(QObject):
    """Tracks keyboard and mouse activity, emitting Qt signals on changes.

    Signals
    -------
    typing_detected
        Emitted when keyboard activity is detected (since the last poll).
    mouse_activity_detected
        Emitted when mouse movement, clicks, or scrolling are detected.
    input_idle
        Emitted **once** when the user transitions from active → idle
        (no input for ``_IDLE_THRESHOLD_SECONDS``).
    """

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    typing_detected = pyqtSignal()
    mouse_activity_detected = pyqtSignal()
    input_idle = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # Shared state — written by pynput threads, read by QTimer on main
        # thread.  Simple float/str assignments are effectively atomic under
        # CPython's GIL.
        self._last_input_time: float = 0.0
        self._last_input_type: str = "none"  # 'keyboard' | 'mouse' | 'none'

        # Internal bookkeeping (only touched by the main-thread timer)
        self._is_idle: bool = True
        self._prev_checked_time: float = 0.0
        self._prev_checked_type: str = "none"

        # Listeners (created in start())
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None

        # Polling timer
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._on_poll_tick)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the input listeners and the polling timer."""
        logger.info("InputTracker: starting listeners and poll timer.")

        # Initialise timestamps so we don't immediately emit idle.
        self._last_input_time = time.time()
        self._prev_checked_time = self._last_input_time
        self._last_input_type = "none"
        self._prev_checked_type = "none"
        self._is_idle = False

        # --- Keyboard listener ---
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
        )
        self._keyboard_listener.daemon = True
        self._keyboard_listener.start()

        # --- Mouse listener ---
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
        )
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

        # --- Start polling timer ---
        self._poll_timer.start()

    def stop(self) -> None:
        """Stop the input listeners and the polling timer.

        Safe to call multiple times.
        """
        logger.info("InputTracker: stopping listeners and poll timer.")

        self._poll_timer.stop()

        if self._keyboard_listener is not None:
            try:
                self._keyboard_listener.stop()
            except Exception:  # noqa: BLE001
                logger.debug("InputTracker: keyboard listener stop raised.", exc_info=True)
            self._keyboard_listener = None

        if self._mouse_listener is not None:
            try:
                self._mouse_listener.stop()
            except Exception:  # noqa: BLE001
                logger.debug("InputTracker: mouse listener stop raised.", exc_info=True)
            self._mouse_listener = None

    # ------------------------------------------------------------------
    # pynput callbacks (run in background daemon threads)
    # ------------------------------------------------------------------
    # These ONLY update primitive shared state.  No Qt signal emission here.

    def _on_key_press(self, _key: keyboard.Key | keyboard.KeyCode | None) -> None:
        self._last_input_time = time.time()
        self._last_input_type = "keyboard"

    def _on_mouse_move(self, _x: int, _y: int) -> None:
        self._last_input_time = time.time()
        self._last_input_type = "mouse"

    def _on_mouse_click(
        self,
        _x: int,
        _y: int,
        _button: mouse.Button,
        _pressed: bool,
    ) -> None:
        self._last_input_time = time.time()
        self._last_input_type = "mouse"

    def _on_mouse_scroll(
        self,
        _x: int,
        _y: int,
        _dx: int,
        _dy: int,
    ) -> None:
        self._last_input_time = time.time()
        self._last_input_type = "mouse"

    # ------------------------------------------------------------------
    # QTimer poll callback (runs on the Qt main thread)
    # ------------------------------------------------------------------

    def _on_poll_tick(self) -> None:
        """Check shared state and emit signals on the main thread."""
        now = time.time()
        current_time = self._last_input_time
        current_type = self._last_input_type

        # Detect new input since last poll
        if current_time > self._prev_checked_time:
            # There has been new input — reset idle state.
            self._is_idle = False

            if current_type == "keyboard":
                self.typing_detected.emit()
            elif current_type == "mouse":
                self.mouse_activity_detected.emit()

        # Check for idle transition
        elapsed_since_last_input = now - current_time
        if elapsed_since_last_input > _IDLE_THRESHOLD_SECONDS and not self._is_idle:
            self._is_idle = True
            self.input_idle.emit()
            logger.debug(
                "InputTracker: user went idle (%.1fs since last input).",
                elapsed_since_last_input,
            )

        # Bookkeeping for next tick
        self._prev_checked_time = current_time
        self._prev_checked_type = current_type
