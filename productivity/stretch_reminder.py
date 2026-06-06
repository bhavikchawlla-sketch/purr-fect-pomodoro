"""Stretch reminder module for the Comnyang desktop pet.

Periodically reminds the user to stand up and stretch using a
:class:`QTimer` and (optionally) a native desktop notification via
``notify-send``.

Typical usage::

    reminder = StretchReminder()
    reminder.stretch_time.connect(on_stretch)
    reminder.start()
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class StretchReminder(QObject):
    """Emits :pyqtSignal:`stretch_time` at a configurable interval.

    In addition to the Qt signal, each reminder also fires a desktop
    notification through ``notify-send`` (Linux).  The notification is
    best-effort: if the command is unavailable the error is logged and
    silently ignored.

    Parameters
    ----------
    interval : int, optional
        The reminder interval in **seconds**.  Defaults to
        :const:`INTERVAL` (45 minutes).  Pass a shorter value in tests
        to avoid long waits.
    parent : QObject, optional
        Optional Qt parent for ownership.
    """

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    stretch_time = pyqtSignal()

    # ------------------------------------------------------------------
    # Default interval (seconds)
    # ------------------------------------------------------------------
    INTERVAL: int = 45 * 60  # 45 minutes

    # ------------------------------------------------------------------
    # Desktop notification content
    # ------------------------------------------------------------------
    _NOTIFY_TITLE: str = "Comnyang 🐱"
    _NOTIFY_BODY: str = (
        "Time to stretch! Stand up and move around for a minute. 🧘"
    )

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(
        self,
        interval: Optional[int] = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._interval: int = interval if interval is not None else self.INTERVAL
        self._enabled: bool = False

        # Repeating timer that fires once every ``_interval`` seconds.
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval * 1_000)  # ms
        self._timer.timeout.connect(self._on_timeout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the periodic stretch reminder."""
        self._enabled = True
        self._timer.start()

    def stop(self) -> None:
        """Stop the periodic stretch reminder."""
        self._timer.stop()
        self._enabled = False

    def reset(self) -> None:
        """Reset the timer countdown.

        If the reminder is currently running the countdown restarts from
        the full interval.  If it is stopped this is a no-op.
        """
        if self._enabled:
            self._timer.stop()
            self._timer.start()

    def is_enabled(self) -> bool:
        """Return ``True`` if the reminder cycle is active."""
        return self._enabled

    def trigger(self) -> None:
        """Manually trigger a stretch reminder.

        This is useful for testing or for a *"remind me now"* UI action.
        The method emits the signal and sends the desktop notification
        regardless of whether the timer is currently running.
        """
        self._emit_reminder()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _on_timeout(self) -> None:
        """Slot connected to the internal QTimer's ``timeout`` signal."""
        self._emit_reminder()

    def _emit_reminder(self) -> None:
        """Emit the stretch signal and fire a desktop notification."""
        self.stretch_time.emit()
        self._send_desktop_notification()

    @staticmethod
    def _send_desktop_notification() -> None:
        """Send a desktop notification via ``notify-send``.

        The call is wrapped in a broad ``except`` clause so that the
        feature degrades gracefully on systems where ``notify-send`` is
        not installed or not functional.
        """
        try:
            subprocess.Popen(  # noqa: S603
                [
                    "notify-send",
                    "-u", "normal",
                    "-i", "dialog-information",
                    StretchReminder._NOTIFY_TITLE,
                    StretchReminder._NOTIFY_BODY,
                ],
            )
        except FileNotFoundError:
            logger.warning(
                "notify-send not found — desktop notifications are disabled."
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send desktop notification.")
