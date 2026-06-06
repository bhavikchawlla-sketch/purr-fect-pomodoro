"""
Process monitoring module for the Comnyang desktop pet.

Periodically scans the system process list to detect running AI-related tools
(e.g. Cursor, Claude, Copilot, Aider, Cody, VS Code) and emits a PyQt6
signal on state changes so the pet can react accordingly.

Design notes
------------
* All ``psutil`` iteration is wrapped in broad exception handling to
  gracefully tolerate processes that disappear or deny access mid-scan.
* The scan runs on a 15-second ``QTimer``, which is fast enough for a
  desktop pet while remaining negligible in CPU cost.
* ``check_now()`` can be called at any time for a synchronous one-shot
  check that also updates internal state and emits signals if needed.
"""

from __future__ import annotations

import logging
from typing import Optional

import psutil
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TARGET_PROCESSES: list[str] = [
    "cursor",
    "Cursor",
    "antigravity",
    "claude",
    "Claude",
    "code",
    "copilot",
    "aider",
    "cody",
]
"""Default process names / substrings to watch for."""

_SCAN_INTERVAL_MS: int = 15_000
"""Interval between automatic process scans (milliseconds)."""


class ProcessMonitor(QObject):
    """Monitors the system for running AI-related tools.

    Signals
    -------
    ai_tool_detected(bool)
        Emitted when the detected state **changes**.
        ``True`` → at least one AI tool is running.
        ``False`` → no AI tools are running.
    """

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    ai_tool_detected = pyqtSignal(bool)

    def __init__(
        self,
        target_processes: Optional[list[str]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self._target_processes: list[str] = (
            list(target_processes) if target_processes is not None else list(_DEFAULT_TARGET_PROCESSES)
        )
        # Lowercase versions for case-insensitive matching
        self._target_lower: list[str] = [t.lower() for t in self._target_processes]

        self._last_state: bool = False

        # Scan timer
        self._timer = QTimer(self)
        self._timer.setInterval(_SCAN_INTERVAL_MS)
        self._timer.timeout.connect(self._on_timer_tick)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start periodic scanning and run an immediate first check."""
        logger.info("ProcessMonitor: starting (interval=%dms).", _SCAN_INTERVAL_MS)
        self._timer.start()
        # Immediate first scan so the pet reacts at launch.
        self.check_now()

    def stop(self) -> None:
        """Stop periodic scanning.

        Safe to call multiple times.
        """
        logger.info("ProcessMonitor: stopping.")
        self._timer.stop()

    def check_now(self) -> bool:
        """Perform an immediate process scan.

        Returns
        -------
        bool
            ``True`` if at least one target process is currently running.

        Side effects
        ------------
        Emits ``ai_tool_detected`` if the result differs from the
        previously recorded state.
        """
        found = self._scan_processes()
        self._update_state(found)
        return found

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_timer_tick(self) -> None:
        """Callback for the periodic QTimer."""
        self.check_now()

    def _scan_processes(self) -> bool:
        """Iterate over running processes and look for target matches.

        Returns ``True`` if at least one matching process is found.
        """
        try:
            for proc in psutil.process_iter(["name", "cmdline"]):
                try:
                    if self._process_matches(proc):
                        return True
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    # Process vanished, or we lack permissions — skip.
                    continue
                except Exception:  # noqa: BLE001
                    # Defensive: don't let a single rogue process crash
                    # the entire scan loop.
                    logger.debug(
                        "ProcessMonitor: unexpected error inspecting a process.",
                        exc_info=True,
                    )
                    continue
        except Exception:  # noqa: BLE001
            logger.warning(
                "ProcessMonitor: process iteration failed.",
                exc_info=True,
            )

        return False

    def _process_matches(self, proc: psutil.Process) -> bool:
        """Return ``True`` if *proc* matches any target pattern.

        Checks both the process name and the command-line arguments for
        case-insensitive partial matches.
        """
        info = proc.info  # type: ignore[attr-defined]  # populated by process_iter attrs

        # --- Check process name ---
        proc_name: str | None = info.get("name")
        if proc_name and self._matches_any(proc_name):
            return True

        # --- Check command-line arguments ---
        cmdline: list[str] | None = info.get("cmdline")
        if cmdline:
            for arg in cmdline:
                if self._matches_any(arg):
                    return True

        return False

    def _matches_any(self, value: str) -> bool:
        """Case-insensitive partial-match of *value* against targets."""
        value_lower = value.lower()
        return any(target in value_lower for target in self._target_lower)

    def _update_state(self, found: bool) -> None:
        """Emit ``ai_tool_detected`` only on state transitions."""
        if found != self._last_state:
            self._last_state = found
            self.ai_tool_detected.emit(found)
            logger.info(
                "ProcessMonitor: AI tool detected state changed → %s.",
                found,
            )
