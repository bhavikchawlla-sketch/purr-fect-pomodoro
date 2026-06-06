"""
Comnyang Retro Sound Generator
==============================

Synthesizes cute 8-bit sound effects programmatically on first launch and
plays them using native Linux sound commands (paplay, aplay, pw-play) in
non-blocking subprocesses.
"""

from __future__ import annotations

import math
import os
import struct
import subprocess
import wave
import logging

logger = logging.getLogger(__name__)

# Sound settings
SAMPLE_RATE = 22050
NUM_CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit audio


class SoundEngine:
    """
    Synthesizes and plays retro sound effects.
    """

    def __init__(self, sounds_dir: str):
        self._sounds_dir = sounds_dir
        self._player: str | None = None
        self._sound_enabled: bool = True

        # Ensure directory exists
        os.makedirs(self._sounds_dir, exist_ok=True)

        # Detect the best player available on the system
        self._detect_player()

        # Generate sound files if missing
        self._generate_sounds_if_missing()

    def _detect_player(self) -> None:
        """Find an available command line audio player."""
        for player in ["paplay", "pw-play", "aplay"]:
            try:
                # Check if command exists
                subprocess.run(
                    ["which", player],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                self._player = player
                logger.info("SoundEngine: detected audio player: %s", player)
                return
            except subprocess.CalledProcessError:
                continue
        logger.warning("SoundEngine: no audio player detected. Sound will be disabled.")

    def set_sound_enabled(self, enabled: bool) -> None:
        """Enable or disable sound effects."""
        self._sound_enabled = enabled

    def is_sound_enabled(self) -> bool:
        """Return True if sound effects are enabled."""
        return self._sound_enabled and self._player is not None

    def play(self, sound_name: str) -> None:
        """Play a synthesized sound effect asynchronously."""
        if not self.is_sound_enabled() or not self._player:
            return

        sound_path = os.path.join(self._sounds_dir, f"{sound_name}.wav")
        if not os.path.exists(sound_path):
            return

        try:
            # Run the command asynchronously
            subprocess.Popen(
                [self._player, sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logger.debug("SoundEngine: failed to play sound: %s", sound_name, exc_info=True)

    def _write_wav(self, filename: str, data: bytes) -> None:
        """Write raw 16-bit PCM bytes to a WAV file."""
        filepath = os.path.join(self._sounds_dir, filename)
        with wave.open(filepath, "wb") as wav:
            wav.setnchannels(NUM_CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(data)

    def _generate_sounds_if_missing(self) -> None:
        """Generate all sound effects if they are not already on disk."""
        if not os.path.exists(os.path.join(self._sounds_dir, "meow.wav")):
            self._write_wav("meow.wav", self._synth_meow())
        if not os.path.exists(os.path.join(self._sounds_dir, "purr.wav")):
            self._write_wav("purr.wav", self._synth_purr())
        if not os.path.exists(os.path.join(self._sounds_dir, "eat.wav")):
            self._write_wav("eat.wav", self._synth_eat())
        if not os.path.exists(os.path.join(self._sounds_dir, "level_up.wav")):
            self._write_wav("level_up.wav", self._synth_level_up())

    # --- Synthesizers ---

    def _synth_meow(self) -> bytes:
        """Synthesize a cute rising-falling cat meow."""
        duration = 0.45  # seconds
        num_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(num_samples):
            t = i / SAMPLE_RATE

            # Frequency profile: starts at 380Hz, rises to 680Hz, falls to 320Hz
            if t < 0.2:
                freq = 380 + (680 - 380) * (t / 0.2)
            else:
                freq = 680 - (680 - 320) * ((t - 0.2) / (duration - 0.2))

            # Amplitude envelope: rise quickly, then decay slowly
            if t < 0.05:
                amp = t / 0.05
            else:
                amp = 1.0 - (t - 0.05) / (duration - 0.05)

            # Generate triangle wave for retro sound
            phase = freq * t * 2 * math.pi
            val = amp * 0.5 * (math.sin(phase) + 0.3 * math.sin(2 * phase))
            val = max(-1.0, min(1.0, val))

            sample = int(val * 32767)
            samples.append(struct.pack("<h", sample))

        return b"".join(samples)

    def _synth_purr(self) -> bytes:
        """Synthesize a low-frequency purr rumble."""
        duration = 1.2  # seconds
        num_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(num_samples):
            t = i / SAMPLE_RATE

            # Base low rumble (55Hz) modulated by a 5Hz sine envelope
            carrier = math.sin(2 * math.pi * 55 * t)
            modulator = 0.6 + 0.4 * math.sin(2 * math.pi * 6 * t)
            
            # Add some subtle high-frequency throat friction noise
            noise = (hash(i) % 100 - 50) / 500.0  # simple deterministic noise

            val = (carrier * modulator + noise) * 0.25
            val = max(-1.0, min(1.0, val))

            sample = int(val * 32767)
            samples.append(struct.pack("<h", sample))

        return b"".join(samples)

    def _synth_eat(self) -> bytes:
        """Synthesize a staccato chewing crunch sound."""
        duration = 0.5  # seconds
        num_samples = int(SAMPLE_RATE * duration)
        samples = []

        for i in range(num_samples):
            t = i / SAMPLE_RATE

            # Create 4 distinct quick chewing crunches
            crunch_cycle = int(t * 8)
            cycle_t = (t * 8) % 1.0

            if cycle_t < 0.25:
                # Crunchy noise: high-frequency sweep with rapid decay
                freq = 1200 - 800 * (cycle_t / 0.25)
                noise = (hash(i) % 100 - 50) / 50.0
                envelope = 1.0 - (cycle_t / 0.25)
                val = noise * envelope * math.sin(2 * math.pi * freq * t) * 0.35
            else:
                val = 0.0

            val = max(-1.0, min(1.0, val))
            sample = int(val * 32767)
            samples.append(struct.pack("<h", sample))

        return b"".join(samples)

    def _synth_level_up(self) -> bytes:
        """Synthesize an ascending major arpeggio."""
        duration = 0.6  # seconds
        num_samples = int(SAMPLE_RATE * duration)
        samples = []

        # Frequencies of C5, E5, G5, C6
        notes = [523.25, 659.25, 783.99, 1046.50]
        num_notes = len(notes)
        note_duration = duration / num_notes

        for i in range(num_samples):
            t = i / SAMPLE_RATE
            note_idx = min(int(t / note_duration), num_notes - 1)
            freq = notes[note_idx]

            # Decay envelope for each note
            note_t = t % note_duration
            envelope = 1.0 - (note_t / note_duration)

            # Square/sine wave blend for retro chiptune sound
            phase = freq * t * 2 * math.pi
            val = 0.25 * (math.sin(phase) + (1.0 if math.sin(phase) > 0 else -1.0)) * envelope

            val = max(-1.0, min(1.0, val))
            sample = int(val * 32767)
            samples.append(struct.pack("<h", sample))

        return b"".join(samples)
