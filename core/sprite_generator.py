"""
Comnyang Sprite Generator
=========================

Programmatic pixel-art cat sprite generator using Pillow.
Generates 64×64 RGBA sprite frames for all animation states of the
Comnyang desktop pet.

Each logical "pixel" is drawn as a 2×2 block of actual pixels on the
64×64 canvas, giving a chunky 32×32-logical-pixel art style.

Animation states (4 frames each):
    - idle:     Sitting cat with blink cycle and tail wag
    - typing:   Cat hunched over a tiny keyboard, paws alternating
    - tracking: Cat swiping a paw left → center → right → center
    - focused:  Idle cat with glasses and a pulsing aura
    - stretch:  Cat stretching upward and relaxing back down
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

# Body
BODY_BASE = (0xE8, 0x91, 0x3A)       # Orange / amber base
BODY_SHADOW = (0xD4, 0x78, 0x2A)     # Darker shadow
BODY_HIGHLIGHT = (0xF5, 0xA8, 0x48)  # Lighter highlight
OUTLINE = (0x4A, 0x37, 0x28)         # Dark-brown outline

# Face features
EYE_GREEN = (0x4A, 0xDE, 0x80)       # Bright green iris
EYE_PUPIL = (0x10, 0x10, 0x10)       # Near-black pupil
NOSE_PINK = (0xFF, 0x9F, 0xB3)       # Pink nose
INNER_EAR = (0xFF, 0xB3, 0xC6)       # Pink inner ear
BELLY = (0xF5, 0xDE, 0xB3)           # Cream belly / chest
WHISKER = (0x80, 0x60, 0x50)         # Subtle whisker lines

# Accessories
GLASSES_FRAME = (0x30, 0x30, 0x30)   # Dark glasses frame
GLASSES_LENS = (0x88, 0xCC, 0xFF, 180)  # Blue-tint lens (semi-transparent)
KEYBOARD_BODY = (0x55, 0x55, 0x60)   # Keyboard / laptop body
KEYBOARD_KEY = (0x90, 0x90, 0x95)    # Key caps
KEYBOARD_SCREEN = (0x70, 0xCC, 0xFF) # Tiny laptop screen glow

TRANSPARENT = (0, 0, 0, 0)


# ---------------------------------------------------------------------------
# Low-level drawing helpers
# ---------------------------------------------------------------------------

PIXEL_SIZE = 2  # Each logical pixel = 2×2 actual pixels


def _px(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple, size: int = PIXEL_SIZE) -> None:
    """Draw a single logical pixel at grid position (x, y)."""
    ax, ay = x * size, y * size
    draw.rectangle([ax, ay, ax + size - 1, ay + size - 1], fill=color)


def _rect(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color: tuple, size: int = PIXEL_SIZE) -> None:
    """Draw a filled rectangle of logical pixels."""
    for dy in range(h):
        for dx in range(w):
            _px(draw, x + dx, y + dy, color, size)


def _line_h(draw: ImageDraw.ImageDraw, x: int, y: int, length: int, color: tuple, size: int = PIXEL_SIZE) -> None:
    """Draw a horizontal line of logical pixels."""
    for dx in range(length):
        _px(draw, x + dx, y, color, size)


def _line_v(draw: ImageDraw.ImageDraw, x: int, y: int, length: int, color: tuple, size: int = PIXEL_SIZE) -> None:
    """Draw a vertical line of logical pixels."""
    for dy in range(length):
        _px(draw, x, y + dy, color, size)


def _new_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a blank 64×64 RGBA frame."""
    img = Image.new("RGBA", (64, 64), TRANSPARENT)
    draw = ImageDraw.Draw(img)
    return img, draw


# ---------------------------------------------------------------------------
# Cat part drawers
# ---------------------------------------------------------------------------

def _draw_ears(draw: ImageDraw.ImageDraw, ox: int, oy: int) -> None:
    """Draw the cat's triangular ears at offset (ox, oy)."""
    # Left ear outline
    _px(draw, ox + 5, oy, OUTLINE)
    _px(draw, ox + 4, oy + 1, OUTLINE)
    _px(draw, ox + 6, oy + 1, OUTLINE)
    _px(draw, ox + 3, oy + 2, OUTLINE)
    _px(draw, ox + 7, oy + 2, OUTLINE)
    # Left ear fill
    _px(draw, ox + 5, oy + 1, BODY_BASE)
    _px(draw, ox + 4, oy + 2, INNER_EAR)
    _px(draw, ox + 5, oy + 2, INNER_EAR)
    _px(draw, ox + 6, oy + 2, BODY_BASE)

    # Right ear outline
    _px(draw, ox + 13, oy, OUTLINE)
    _px(draw, ox + 12, oy + 1, OUTLINE)
    _px(draw, ox + 14, oy + 1, OUTLINE)
    _px(draw, ox + 11, oy + 2, OUTLINE)
    _px(draw, ox + 15, oy + 2, OUTLINE)
    # Right ear fill
    _px(draw, ox + 13, oy + 1, BODY_BASE)
    _px(draw, ox + 12, oy + 2, BODY_BASE)
    _px(draw, ox + 13, oy + 2, INNER_EAR)
    _px(draw, ox + 14, oy + 2, INNER_EAR)


def _draw_head(draw: ImageDraw.ImageDraw, ox: int, oy: int, eye_state: str = "open") -> None:
    """
    Draw the cat's head (without ears) at offset (ox, oy).

    Parameters
    ----------
    eye_state : str
        "open", "half", or "closed"
    """
    # Head outline - top
    _line_h(draw, ox + 4, oy + 3, 11, OUTLINE)
    # Head outline - sides
    _line_v(draw, ox + 3, oy + 3, 6, OUTLINE)
    _line_v(draw, ox + 15, oy + 3, 6, OUTLINE)
    # Head outline - bottom (jaw)
    _line_h(draw, ox + 4, oy + 9, 2, OUTLINE)
    _line_h(draw, ox + 13, oy + 9, 2, OUTLINE)
    _line_h(draw, ox + 6, oy + 10, 7, OUTLINE)

    # Head fill
    for row in range(3, 10):
        start = 4
        end = 15
        if row == 9:
            # Jaw narrows
            _line_h(draw, ox + 6, oy + row, 7, BODY_BASE)
            continue
        _line_h(draw, ox + start, oy + row, end - start, BODY_BASE)

    # Tabby stripes on forehead
    _px(draw, ox + 7, oy + 3, BODY_SHADOW)
    _px(draw, ox + 9, oy + 3, BODY_SHADOW)
    _px(draw, ox + 11, oy + 3, BODY_SHADOW)
    _px(draw, ox + 8, oy + 4, BODY_SHADOW)
    _px(draw, ox + 10, oy + 4, BODY_SHADOW)

    # Highlight on cheeks
    _px(draw, ox + 5, oy + 7, BODY_HIGHLIGHT)
    _px(draw, ox + 13, oy + 7, BODY_HIGHLIGHT)

    # ---- Eyes ----
    if eye_state == "open":
        # Left eye
        _px(draw, ox + 6, oy + 5, OUTLINE)
        _px(draw, ox + 7, oy + 5, EYE_GREEN)
        _px(draw, ox + 8, oy + 5, OUTLINE)
        _px(draw, ox + 7, oy + 6, EYE_GREEN)
        # pupil
        _px(draw, ox + 7, oy + 5, EYE_PUPIL)
        _px(draw, ox + 6, oy + 6, OUTLINE)
        _px(draw, ox + 7, oy + 6, EYE_GREEN)
        _px(draw, ox + 8, oy + 6, OUTLINE)
        # Catch light
        _px(draw, ox + 6, oy + 5, EYE_GREEN)
        _px(draw, ox + 7, oy + 5, EYE_PUPIL)

        # Right eye
        _px(draw, ox + 10, oy + 5, OUTLINE)
        _px(draw, ox + 11, oy + 5, EYE_GREEN)
        _px(draw, ox + 12, oy + 5, OUTLINE)
        _px(draw, ox + 10, oy + 6, OUTLINE)
        _px(draw, ox + 11, oy + 6, EYE_GREEN)
        _px(draw, ox + 12, oy + 6, OUTLINE)
        _px(draw, ox + 12, oy + 5, EYE_GREEN)
        _px(draw, ox + 11, oy + 5, EYE_PUPIL)

    elif eye_state == "half":
        # Half-closed: single row slit
        _px(draw, ox + 6, oy + 6, OUTLINE)
        _px(draw, ox + 7, oy + 6, EYE_GREEN)
        _px(draw, ox + 8, oy + 6, OUTLINE)
        _px(draw, ox + 10, oy + 6, OUTLINE)
        _px(draw, ox + 11, oy + 6, EYE_GREEN)
        _px(draw, ox + 12, oy + 6, OUTLINE)
        # Eyelid lines above
        _line_h(draw, ox + 6, oy + 5, 3, BODY_SHADOW)
        _line_h(draw, ox + 10, oy + 5, 3, BODY_SHADOW)

    elif eye_state == "closed":
        # Closed: horizontal lines
        _line_h(draw, ox + 6, oy + 6, 3, OUTLINE)
        _line_h(draw, ox + 10, oy + 6, 3, OUTLINE)

    # ---- Nose ----
    _px(draw, ox + 9, oy + 7, NOSE_PINK)

    # ---- Mouth ----
    _px(draw, ox + 8, oy + 8, OUTLINE)
    _px(draw, ox + 10, oy + 8, OUTLINE)
    _px(draw, ox + 9, oy + 8, BODY_BASE)

    # ---- Whiskers ----
    # Left whiskers
    _px(draw, ox + 3, oy + 6, WHISKER)
    _px(draw, ox + 4, oy + 7, WHISKER)
    _px(draw, ox + 3, oy + 8, WHISKER)
    _px(draw, ox + 4, oy + 8, WHISKER)
    # Right whiskers
    _px(draw, ox + 15, oy + 6, WHISKER)
    _px(draw, ox + 14, oy + 7, WHISKER)
    _px(draw, ox + 15, oy + 8, WHISKER)
    _px(draw, ox + 14, oy + 8, WHISKER)


def _draw_sitting_body(draw: ImageDraw.ImageDraw, ox: int, oy: int, bob: int = 0) -> None:
    """Draw the cat's sitting body at offset (ox, oy) with optional vertical bob."""
    by = oy + bob

    # Torso outline
    _line_v(draw, ox + 4, by + 11, 7, OUTLINE)
    _line_v(draw, ox + 14, by + 11, 7, OUTLINE)
    _line_h(draw, ox + 5, by + 11, 9, OUTLINE)

    # Torso fill
    for row in range(12, 18):
        _line_h(draw, ox + 5, by + row, 9, BODY_BASE)

    # Belly / chest
    _line_h(draw, ox + 7, by + 12, 5, BELLY)
    _line_h(draw, ox + 7, by + 13, 5, BELLY)
    _line_h(draw, ox + 8, by + 14, 3, BELLY)

    # Shadow on sides
    _line_v(draw, ox + 5, by + 14, 3, BODY_SHADOW)
    _line_v(draw, ox + 13, by + 14, 3, BODY_SHADOW)

    # Highlight on shoulders
    _px(draw, ox + 6, by + 12, BODY_HIGHLIGHT)
    _px(draw, ox + 12, by + 12, BODY_HIGHLIGHT)

    # ---- Front paws ----
    # Left paw
    _line_h(draw, ox + 5, by + 18, 3, OUTLINE)
    _px(draw, ox + 5, by + 17, OUTLINE)
    _px(draw, ox + 7, by + 17, OUTLINE)
    _px(draw, ox + 6, by + 17, BODY_BASE)

    # Right paw
    _line_h(draw, ox + 11, by + 18, 3, OUTLINE)
    _px(draw, ox + 11, by + 17, OUTLINE)
    _px(draw, ox + 13, by + 17, OUTLINE)
    _px(draw, ox + 12, by + 17, BODY_BASE)

    # Paw pads (lighter)
    _px(draw, ox + 6, by + 18, BELLY)
    _px(draw, ox + 12, by + 18, BELLY)


def _draw_tail(draw: ImageDraw.ImageDraw, ox: int, oy: int, raise_level: int = 0) -> None:
    """
    Draw the cat's tail. raise_level shifts tip upward (0 = resting, 2 = raised).
    """
    base_y = oy + 16
    # Tail curves to the right
    _px(draw, ox + 15, base_y, OUTLINE)
    _px(draw, ox + 16, base_y - 1, OUTLINE)
    _px(draw, ox + 17, base_y - 1 - raise_level, OUTLINE)
    _px(draw, ox + 18, base_y - 2 - raise_level, OUTLINE)
    _px(draw, ox + 19, base_y - 3 - raise_level, OUTLINE)

    # Tail body fill (slightly inside outline — single pixel tail is fine for this scale)
    _px(draw, ox + 16, base_y, BODY_BASE)
    _px(draw, ox + 17, base_y - raise_level, BODY_BASE)
    _px(draw, ox + 18, base_y - 1 - raise_level, BODY_BASE)

    # Tail tip highlight
    _px(draw, ox + 19, base_y - 3 - raise_level, BODY_HIGHLIGHT)


def _draw_glasses(draw: ImageDraw.ImageDraw, ox: int, oy: int) -> None:
    """Draw tiny pixel-art glasses on the cat's face."""
    # Left lens frame (3×2 rectangle)
    _rect(draw, ox + 5, oy + 5, 4, 2, GLASSES_FRAME)
    _rect(draw, ox + 6, oy + 5, 2, 2, GLASSES_LENS)

    # Right lens frame
    _rect(draw, ox + 10, oy + 5, 4, 2, GLASSES_FRAME)
    _rect(draw, ox + 11, oy + 5, 2, 2, GLASSES_LENS)

    # Bridge
    _px(draw, ox + 9, oy + 5, GLASSES_FRAME)

    # Temple arms
    _px(draw, ox + 4, oy + 5, GLASSES_FRAME)
    _px(draw, ox + 14, oy + 5, GLASSES_FRAME)


def _draw_aura(draw: ImageDraw.ImageDraw, ox: int, oy: int, intensity: int) -> None:
    """
    Draw a subtle glowing aura around the cat silhouette.

    Parameters
    ----------
    intensity : int
        Aura brightness 0-3 (maps to alpha / spread).
    """
    alpha = 40 + intensity * 25  # 40, 65, 90, 115
    color = (255, 230, 150, alpha)

    # Aura dots around the silhouette
    aura_points = [
        (ox + 3, oy + 1), (ox + 15, oy + 1),
        (ox + 2, oy + 5), (ox + 16, oy + 5),
        (ox + 2, oy + 10), (ox + 16, oy + 10),
        (ox + 3, oy + 15), (ox + 15, oy + 15),
        (ox + 3, oy + 18), (ox + 15, oy + 18),
        (ox + 9, oy - 1),
    ]
    # Extra sparkle points at higher intensities
    if intensity >= 1:
        aura_points += [
            (ox + 1, oy + 3), (ox + 17, oy + 3),
            (ox + 1, oy + 8), (ox + 17, oy + 8),
        ]
    if intensity >= 2:
        aura_points += [
            (ox + 1, oy + 13), (ox + 17, oy + 13),
            (ox + 9, oy - 2),
        ]
    if intensity >= 3:
        aura_points += [
            (ox + 0, oy + 6), (ox + 18, oy + 6),
            (ox + 0, oy + 12), (ox + 18, oy + 12),
        ]

    for px_coord, py_coord in aura_points:
        if 0 <= px_coord < 32 and 0 <= py_coord < 32:
            _px(draw, px_coord, py_coord, color)


def _draw_keyboard(draw: ImageDraw.ImageDraw, ox: int, oy: int) -> None:
    """Draw a tiny laptop / keyboard in front of the cat."""
    # Laptop screen (small rectangle)
    _rect(draw, ox + 6, oy + 14, 7, 3, OUTLINE)
    _rect(draw, ox + 7, oy + 14, 5, 2, KEYBOARD_SCREEN)

    # Keyboard base
    _rect(draw, ox + 5, oy + 17, 9, 2, OUTLINE)
    _rect(draw, ox + 6, oy + 17, 7, 1, KEYBOARD_BODY)

    # Key rows
    for kx in range(6, 13):
        if kx % 2 == 0:
            _px(draw, ox + kx, oy + 18, KEYBOARD_KEY)
        else:
            _px(draw, ox + kx, oy + 18, KEYBOARD_BODY)


def _draw_typing_paw(draw: ImageDraw.ImageDraw, ox: int, oy: int,
                     left_down: bool, right_down: bool) -> None:
    """Draw paws in typing position."""
    left_y = oy + 16 if left_down else oy + 15
    right_y = oy + 16 if right_down else oy + 15

    # Left paw
    _px(draw, ox + 5, left_y, OUTLINE)
    _px(draw, ox + 6, left_y, BODY_BASE)
    _px(draw, ox + 7, left_y, OUTLINE)
    _px(draw, ox + 6, left_y + 1, BELLY)

    # Right paw
    _px(draw, ox + 11, right_y, OUTLINE)
    _px(draw, ox + 12, right_y, BODY_BASE)
    _px(draw, ox + 13, right_y, OUTLINE)
    _px(draw, ox + 12, right_y + 1, BELLY)


def _draw_typing_body(draw: ImageDraw.ImageDraw, ox: int, oy: int) -> None:
    """Draw the cat body in a hunched-over typing pose (no front paws)."""
    # Torso outline — hunched forward, slightly narrower/shorter
    _line_v(draw, ox + 4, oy + 10, 6, OUTLINE)
    _line_v(draw, ox + 14, oy + 10, 6, OUTLINE)
    _line_h(draw, ox + 5, oy + 10, 9, OUTLINE)

    # Torso fill
    for row in range(11, 16):
        _line_h(draw, ox + 5, oy + row, 9, BODY_BASE)

    # Belly
    _line_h(draw, ox + 7, oy + 11, 5, BELLY)
    _line_h(draw, ox + 8, oy + 12, 3, BELLY)

    # Shadow
    _line_v(draw, ox + 5, oy + 13, 2, BODY_SHADOW)
    _line_v(draw, ox + 13, oy + 13, 2, BODY_SHADOW)


# ---------------------------------------------------------------------------
# Stretch body helpers
# ---------------------------------------------------------------------------

def _draw_stretch_body(draw: ImageDraw.ImageDraw, ox: int, oy: int,
                       phase: int) -> None:
    """
    Draw the cat in various stretch poses.

    phase:
        0 = starting (body low, compact)
        1 = extending (body mid, paws reaching)
        2 = full stretch (body tall, paws high)
        3 = relaxing back down
    """
    if phase == 0:
        # Low compact body
        _line_v(draw, ox + 4, oy + 12, 7, OUTLINE)
        _line_v(draw, ox + 14, oy + 12, 7, OUTLINE)
        _line_h(draw, ox + 5, oy + 12, 9, OUTLINE)
        for row in range(13, 19):
            _line_h(draw, ox + 5, oy + row, 9, BODY_BASE)
        _line_h(draw, ox + 7, oy + 13, 5, BELLY)
        _line_h(draw, ox + 8, oy + 14, 3, BELLY)
        # Paws on ground
        _line_h(draw, ox + 5, oy + 19, 3, OUTLINE)
        _line_h(draw, ox + 11, oy + 19, 3, OUTLINE)
        _px(draw, ox + 6, oy + 19, BELLY)
        _px(draw, ox + 12, oy + 19, BELLY)

    elif phase == 1:
        # Extending upward — taller body, paws reaching up
        _line_v(draw, ox + 4, oy + 10, 8, OUTLINE)
        _line_v(draw, ox + 14, oy + 10, 8, OUTLINE)
        _line_h(draw, ox + 5, oy + 10, 9, OUTLINE)
        for row in range(11, 18):
            _line_h(draw, ox + 5, oy + row, 9, BODY_BASE)
        _line_h(draw, ox + 7, oy + 11, 5, BELLY)
        _line_h(draw, ox + 8, oy + 12, 3, BELLY)
        # Paws reaching up
        _line_v(draw, ox + 5, oy + 8, 2, OUTLINE)
        _px(draw, ox + 6, oy + 8, OUTLINE)
        _px(draw, ox + 5, oy + 9, BODY_BASE)
        _line_v(draw, ox + 13, oy + 8, 2, OUTLINE)
        _px(draw, ox + 12, oy + 8, OUTLINE)
        _px(draw, ox + 13, oy + 9, BODY_BASE)
        # Ground paws
        _line_h(draw, ox + 5, oy + 18, 3, OUTLINE)
        _line_h(draw, ox + 11, oy + 18, 3, OUTLINE)

    elif phase == 2:
        # Full stretch — tallest, paws high above head
        _line_v(draw, ox + 5, oy + 8, 11, OUTLINE)
        _line_v(draw, ox + 13, oy + 8, 11, OUTLINE)
        _line_h(draw, ox + 6, oy + 8, 7, OUTLINE)
        for row in range(9, 19):
            _line_h(draw, ox + 6, oy + row, 7, BODY_BASE)
        _line_h(draw, ox + 7, oy + 10, 5, BELLY)
        _line_h(draw, ox + 8, oy + 11, 3, BELLY)
        # Paws way up
        _line_v(draw, ox + 5, oy + 5, 3, OUTLINE)
        _px(draw, ox + 6, oy + 5, OUTLINE)
        _px(draw, ox + 5, oy + 6, BODY_BASE)
        _px(draw, ox + 5, oy + 7, BODY_BASE)
        _line_v(draw, ox + 13, oy + 5, 3, OUTLINE)
        _px(draw, ox + 12, oy + 5, OUTLINE)
        _px(draw, ox + 13, oy + 6, BODY_BASE)
        _px(draw, ox + 13, oy + 7, BODY_BASE)
        # Ground paws
        _line_h(draw, ox + 6, oy + 19, 3, OUTLINE)
        _line_h(draw, ox + 10, oy + 19, 3, OUTLINE)

    elif phase == 3:
        # Relaxing — same as phase 0 but slightly taller
        _line_v(draw, ox + 4, oy + 11, 7, OUTLINE)
        _line_v(draw, ox + 14, oy + 11, 7, OUTLINE)
        _line_h(draw, ox + 5, oy + 11, 9, OUTLINE)
        for row in range(12, 18):
            _line_h(draw, ox + 5, oy + row, 9, BODY_BASE)
        _line_h(draw, ox + 7, oy + 12, 5, BELLY)
        _line_h(draw, ox + 8, oy + 13, 3, BELLY)
        # Paws settling
        _line_h(draw, ox + 5, oy + 18, 3, OUTLINE)
        _line_h(draw, ox + 11, oy + 18, 3, OUTLINE)
        _px(draw, ox + 6, oy + 18, BELLY)
        _px(draw, ox + 12, oy + 18, BELLY)
        # Shadow
        _line_v(draw, ox + 5, oy + 15, 2, BODY_SHADOW)
        _line_v(draw, ox + 13, oy + 15, 2, BODY_SHADOW)


def _draw_tracking_paw(draw: ImageDraw.ImageDraw, ox: int, oy: int,
                       position: int) -> None:
    """
    Draw a swiping paw for the tracking state.

    position: 0 = left, 1 = center, 2 = right, 3 = center (return)
    """
    paw_x_offsets = {0: -3, 1: 0, 2: 3, 3: 0}
    paw_y = oy + 13
    paw_x = ox + 4 + paw_x_offsets[position]

    # Arm extending from body
    arm_base_x = ox + 4
    _px(draw, arm_base_x, oy + 14, OUTLINE)
    _px(draw, arm_base_x, oy + 13, BODY_BASE)

    # Paw
    _px(draw, paw_x, paw_y, OUTLINE)
    _px(draw, paw_x + 1, paw_y, BODY_BASE)
    _px(draw, paw_x + 2, paw_y, OUTLINE)
    _px(draw, paw_x, paw_y - 1, OUTLINE)
    _px(draw, paw_x + 1, paw_y - 1, BODY_BASE)
    _px(draw, paw_x + 2, paw_y - 1, OUTLINE)
    # Paw pad
    _px(draw, paw_x + 1, paw_y, BELLY)

    # Connect paw to arm
    if position == 0:
        _px(draw, arm_base_x - 1, oy + 13, BODY_BASE)
        _px(draw, arm_base_x - 2, oy + 13, BODY_BASE)
    elif position == 2:
        _px(draw, arm_base_x + 1, oy + 14, BODY_BASE)
        _px(draw, arm_base_x + 2, oy + 14, BODY_BASE)


# ---------------------------------------------------------------------------
# Frame generators per animation state
# ---------------------------------------------------------------------------

def _generate_idle_frames(sprites_dir: str) -> None:
    """Generate the 4 idle animation frames."""
    out = Path(sprites_dir) / "idle"
    out.mkdir(parents=True, exist_ok=True)

    eye_states = ["open", "half", "closed", "open"]
    tail_raises = [0, 1, 2, 0]
    body_bobs = [0, 0, 0, 1]

    for i in range(4):
        img, draw = _new_frame()
        ox, oy = 3, 3  # base offset to centre cat on canvas

        _draw_ears(draw, ox, oy)
        _draw_head(draw, ox, oy, eye_state=eye_states[i])
        _draw_sitting_body(draw, ox, oy + body_bobs[i])
        _draw_tail(draw, ox, oy, raise_level=tail_raises[i])

        img.save(str(out / f"idle_{i}.png"))


def _generate_typing_frames(sprites_dir: str) -> None:
    """Generate the 4 typing animation frames."""
    out = Path(sprites_dir) / "typing"
    out.mkdir(parents=True, exist_ok=True)

    # (left_down, right_down) for each frame
    paw_states = [
        (True, False),   # Frame 0: left paw down
        (False, True),   # Frame 1: right paw down
        (False, False),  # Frame 2: both paws up
        (True, True),    # Frame 3: both paws slamming
    ]

    for i in range(4):
        img, draw = _new_frame()
        ox, oy = 3, 2

        _draw_ears(draw, ox, oy)
        _draw_head(draw, ox, oy, eye_state="open")
        _draw_typing_body(draw, ox, oy)
        _draw_keyboard(draw, ox, oy)
        _draw_typing_paw(draw, ox, oy, *paw_states[i])
        _draw_tail(draw, ox, oy - 1, raise_level=1)

        img.save(str(out / f"typing_{i}.png"))


def _generate_tracking_frames(sprites_dir: str) -> None:
    """Generate the 4 tracking animation frames."""
    out = Path(sprites_dir) / "tracking"
    out.mkdir(parents=True, exist_ok=True)

    for i in range(4):
        img, draw = _new_frame()
        ox, oy = 3, 3

        _draw_ears(draw, ox, oy)
        _draw_head(draw, ox, oy, eye_state="open")
        _draw_sitting_body(draw, ox, oy)
        _draw_tracking_paw(draw, ox, oy, position=i)
        _draw_tail(draw, ox, oy, raise_level=1)

        img.save(str(out / f"tracking_{i}.png"))


def _generate_focused_frames(sprites_dir: str) -> None:
    """Generate the 4 focused animation frames (idle + glasses + aura)."""
    out = Path(sprites_dir) / "focused"
    out.mkdir(parents=True, exist_ok=True)

    for i in range(4):
        img, draw = _new_frame()
        ox, oy = 3, 3

        # Aura goes behind everything
        _draw_aura(draw, ox, oy, intensity=i)

        _draw_ears(draw, ox, oy)
        _draw_head(draw, ox, oy, eye_state="open")
        _draw_glasses(draw, ox, oy)
        _draw_sitting_body(draw, ox, oy)
        _draw_tail(draw, ox, oy, raise_level=0)

        img.save(str(out / f"focused_{i}.png"))


def _generate_stretch_frames(sprites_dir: str) -> None:
    """Generate the 4 stretch animation frames."""
    out = Path(sprites_dir) / "stretch"
    out.mkdir(parents=True, exist_ok=True)

    head_offsets_y = [3, 1, -1, 2]
    eye_states = ["open", "half", "closed", "open"]

    for i in range(4):
        img, draw = _new_frame()
        ox = 3
        head_oy = head_offsets_y[i]

        # For stretch we draw head at varying heights
        # Only draw ears + head for phases where head is visible above body
        if i == 2:
            # Full stretch — head is higher, no ears (paws cover area)
            _draw_head(draw, ox, head_oy + 2, eye_state=eye_states[i])
            _draw_ears(draw, ox, head_oy + 2)
        else:
            _draw_ears(draw, ox, head_oy + 2)
            _draw_head(draw, ox, head_oy + 2, eye_state=eye_states[i])

        _draw_stretch_body(draw, ox, head_oy + 2, phase=i)
        _draw_tail(draw, ox, head_oy + 4, raise_level=1 if i in (1, 2) else 0)

        img.save(str(out / f"stretch_{i}.png"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_all(sprites_dir: str) -> None:
    """
    Generate all sprite frames into the given directory.

    Creates sub-directories ``idle/``, ``typing/``, ``tracking/``,
    ``focused/``, and ``stretch/``, each containing 4 numbered PNG frames.

    Parameters
    ----------
    sprites_dir : str
        Root directory for sprite output.  Will be created if it does not
        exist.
    """
    Path(sprites_dir).mkdir(parents=True, exist_ok=True)

    _generate_idle_frames(sprites_dir)
    _generate_typing_frames(sprites_dir)
    _generate_tracking_frames(sprites_dir)
    _generate_focused_frames(sprites_dir)
    _generate_stretch_frames(sprites_dir)


def generate_if_missing(sprites_dir: str) -> None:
    """
    Generate sprites only if *sprites_dir* is empty or does not exist.

    This is intended as a startup convenience so the application can call
    this once and skip regeneration on subsequent launches.

    Parameters
    ----------
    sprites_dir : str
        Root directory for sprite output.
    """
    sprites_path = Path(sprites_dir)
    if not sprites_path.exists():
        generate_all(sprites_dir)
        return
    # Check if any subdirectory has PNG files
    has_pngs = any(
        f.suffix.lower() == ".png"
        for d in sprites_path.iterdir() if d.is_dir()
        for f in d.iterdir()
    )
    if not has_pngs:
        generate_all(sprites_dir)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "sprites"
    )
    print(f"Generating sprites in: {os.path.abspath(dest)}")
    generate_all(dest)
    print("Done — generated 20 frames across 5 animation states.")
