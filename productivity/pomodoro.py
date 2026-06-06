"""Pomodoro timer module for the Comnyang desktop pet.

Implements a standard Pomodoro technique timer with a three-phase state
machine: IDLE → WORK (25 min) → BREAK (5 min) → IDLE.  The timer emits
Qt signals every second so that UI components can update in real time.

Typical usage::

    timer = PomodoroTimer()
    timer.tick.connect(on_tick)
    timer.phase_changed.connect(on_phase)
    timer.completed.connect(on_cycle_done)
    timer.start()
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class PomodoroTimer(QObject):
    """A Pomodoro technique timer built on top of :class:`QTimer`.

    Signals
    -------
    tick(int)
        Emitted every second with the number of remaining seconds in the
        current phase.
    phase_changed(str)
        Emitted when the phase transitions.  The payload is one of
        ``'work'``, ``'break'``, or ``'idle'``.
    completed()
        Emitted when a full work → break cycle finishes and the timer
        returns to the idle state.
    """

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    tick = pyqtSignal(int)
    phase_changed = pyqtSignal(str)
    completed = pyqtSignal()

    # ------------------------------------------------------------------
    # Duration constants (seconds)
    # ------------------------------------------------------------------
    WORK_DURATION: int = 25 * 60   # 25 minutes
    BREAK_DURATION: int = 5 * 60   # 5 minutes

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Internal state
        self._phase: str = "idle"
        self._remaining: int = 0
        self._cycles_completed: int = 0

        # One-second interval timer driving the countdown
        self._timer = QTimer(self)
        self._timer.setInterval(1_000)  # 1 second
        self._timer.timeout.connect(self._on_tick)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start (or resume) the timer.

        If the timer is idle it begins a new *work* phase.  If it was
        previously paused it resumes the countdown from where it left off.
        """
        if self._phase == "idle":
            self._begin_phase("work")
        # Resume a paused timer (remaining > 0 but timer not active)
        if not self._timer.isActive():
            self._timer.start()

    def pause(self) -> None:
        """Pause the current countdown without resetting progress."""
        self._timer.stop()

    def stop(self) -> None:
        """Stop the timer and reset all state back to idle."""
        self._timer.stop()
        self._phase = "idle"
        self._remaining = 0
        self.phase_changed.emit("idle")

    def skip(self) -> None:
        """Skip the remainder of the current phase and advance.

        * ``work``  → begins the *break* phase.
        * ``break`` → returns to *idle* and emits :pyqtSignal:`completed`.
        * ``idle``  → no-op.
        """
        if self._phase == "work":
            self._begin_phase("break")
        elif self._phase == "break":
            self._finish_cycle()
        # If already idle, skip is a no-op.

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        """Return ``True`` if the countdown timer is actively ticking."""
        return self._timer.isActive()

    def get_phase(self) -> str:
        """Return the current phase: ``'idle'``, ``'work'``, or ``'break'``."""
        return self._phase

    def get_remaining(self) -> int:
        """Return the remaining seconds in the current phase."""
        return self._remaining

    def format_time(self) -> str:
        """Return the remaining time formatted as ``MM:SS``."""
        minutes, seconds = divmod(self._remaining, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def cycles_completed(self) -> int:
        """The number of full work+break cycles completed so far."""
        return self._cycles_completed

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _begin_phase(self, phase: str) -> None:
        """Transition into *phase* and start the countdown."""
        self._phase = phase
        self._remaining = (
            self.WORK_DURATION if phase == "work" else self.BREAK_DURATION
        )
        self.phase_changed.emit(phase)
        # Ensure the timer is ticking
        if not self._timer.isActive():
            self._timer.start()

    def _finish_cycle(self) -> None:
        """Mark the current work+break cycle as complete and go idle."""
        self._timer.stop()
        self._cycles_completed += 1
        self._phase = "idle"
        self._remaining = 0
        self.phase_changed.emit("idle")
        self.completed.emit()

    def _on_tick(self) -> None:
        """Slot connected to the internal QTimer's ``timeout`` signal."""
        self._remaining -= 1
        self.tick.emit(self._remaining)

        if self._remaining <= 0:
            if self._phase == "work":
                self._begin_phase("break")
            elif self._phase == "break":
                self._finish_cycle()
