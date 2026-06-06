"""
Comnyang Color Filter
=====================

Provides color-tinting functionality for sprite images.  Loads PNG frames
from disk, optionally applies a luminosity-preserving tint, converts to
``QPixmap`` for use in the PyQt6 UI, and caches the results.

Tinting algorithm
-----------------
1. Convert the source RGBA image to **grayscale** using Pillow's
   ``ImageOps.grayscale`` (ITU-R BT.601 luminosity weights).
2. Build look-up tables (LUTs) that map each grayscale value to the
   corresponding tinted R, G, B value.
3. Apply the LUTs and re-attach the original alpha channel.

This produces a monochrome-shaded version of the sprite that takes on the
requested hue while retaining all original lighting detail.
"""

from __future__ import annotations

import os
from typing import Optional

from PIL import Image, ImageOps

from PyQt6.QtGui import QPixmap, QImage

# ---------------------------------------------------------------------------
# Colour presets
# ---------------------------------------------------------------------------

COLOR_PRESETS: dict[str, Optional[tuple[int, int, int]]] = {
    "default": None,
    "black": (40, 40, 40),
    "white": (240, 235, 230),
    "grey": (150, 150, 155),
    "calico": (210, 160, 100),
    "siamese": (180, 160, 140),
}

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

# Keyed by (directory_path, color_tuple_or_none).
# Values are lists of QPixmap, one per frame in sorted filename order.
_pixmap_cache: dict[tuple[str, Optional[tuple[int, int, int]]], list[QPixmap]] = {}

# ---------------------------------------------------------------------------
# Core tinting
# ---------------------------------------------------------------------------


def tint_image(image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """
    Apply a luminosity-preserving colour tint to a Pillow RGBA image.

    Parameters
    ----------
    image : PIL.Image.Image
        Source image in RGBA mode.
    color : tuple[int, int, int]
        Target tint colour as ``(R, G, B)`` in 0-255 range.

    Returns
    -------
    PIL.Image.Image
        New RGBA image with the tint applied.  Alpha channel is preserved
        from the original.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Separate alpha channel
    r, g, b, alpha = image.split()

    # Convert to grayscale (luminosity)
    gray = ImageOps.grayscale(image.convert("RGB"))

    # Build LUTs: map grayscale 0-255 → tinted channel 0-255
    tr, tg, tb = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    lut = (
        tuple(min(255, int(v * tr + 0.5)) for v in range(256))
        + tuple(min(255, int(v * tg + 0.5)) for v in range(256))
        + tuple(min(255, int(v * tb + 0.5)) for v in range(256))
    )

    # Apply LUT to grayscale→RGB conversion
    tinted_rgb = gray.convert("RGB").point(lut)

    # Re-attach original alpha
    tinted_rgba = tinted_rgb.convert("RGBA")
    tinted_rgba.putalpha(alpha)
    return tinted_rgba


# ---------------------------------------------------------------------------
# PIL → QPixmap conversion
# ---------------------------------------------------------------------------


def _pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    """
    Convert a Pillow RGBA image to a PyQt6 ``QPixmap``.

    The conversion goes through an in-memory bytes buffer to avoid
    temporary files.

    Parameters
    ----------
    pil_image : PIL.Image.Image
        Source image (must be RGBA).

    Returns
    -------
    QPixmap
        Ready-to-use pixmap for painting in a PyQt6 widget.
    """
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")

    data = pil_image.tobytes("raw", "RGBA")
    width, height = pil_image.size

    qimage = QImage(data, width, height, 4 * width, QImage.Format.Format_RGBA8888)
    # QImage does not copy *data* by default — .copy() ensures it owns the
    # buffer so Python's garbage collector cannot pull it away.
    return QPixmap.fromImage(qimage.copy())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_tinted_frames(
    frames_dir: str,
    color: Optional[tuple[int, int, int]] = None,
) -> list[QPixmap]:
    """
    Load PNG frames from *frames_dir*, optionally tint them, and return
    a list of ``QPixmap`` objects.

    Results are cached so repeated calls with the same arguments are free.

    Parameters
    ----------
    frames_dir : str
        Path to a directory containing numbered ``.png`` frame files.
        Files are sorted lexicographically so ``frame_0.png`` comes
        before ``frame_1.png``.
    color : tuple[int, int, int] | None
        Tint colour as ``(R, G, B)``.  Pass ``None`` (the default /
        ``"default"`` preset) to load frames without tinting.

    Returns
    -------
    list[QPixmap]
        Ordered list of pixmaps, one per frame file.

    Raises
    ------
    FileNotFoundError
        If *frames_dir* does not exist.
    """
    cache_key = (os.path.normpath(frames_dir), color)
    if cache_key in _pixmap_cache:
        return _pixmap_cache[cache_key]

    if not os.path.isdir(frames_dir):
        raise FileNotFoundError(f"Frames directory does not exist: {frames_dir}")

    # Collect PNGs in sorted order
    png_files = sorted(
        f for f in os.listdir(frames_dir)
        if f.lower().endswith(".png")
    )

    pixmaps: list[QPixmap] = []
    for filename in png_files:
        filepath = os.path.join(frames_dir, filename)
        img = Image.open(filepath).convert("RGBA")

        if color is not None:
            img = tint_image(img, color)

        pixmaps.append(_pil_to_qpixmap(img))

    _pixmap_cache[cache_key] = pixmaps
    return pixmaps


def clear_cache() -> None:
    """
    Clear the internal QPixmap cache.

    Call this when changing colour themes at runtime to free memory and
    force frames to be re-processed on the next
    :func:`get_tinted_frames` call.
    """
    _pixmap_cache.clear()


def get_preset_color(name: str) -> Optional[tuple[int, int, int]]:
    """
    Look up a colour preset by name.

    Parameters
    ----------
    name : str
        Preset name (case-insensitive).  Must be a key in
        :data:`COLOR_PRESETS`.

    Returns
    -------
    tuple[int, int, int] | None
        The RGB colour tuple, or ``None`` for the ``"default"`` preset.

    Raises
    ------
    KeyError
        If *name* is not a recognised preset.
    """
    key = name.lower().strip()
    if key not in COLOR_PRESETS:
        raise KeyError(
            f"Unknown colour preset {name!r}. "
            f"Available: {', '.join(COLOR_PRESETS)}"
        )
    return COLOR_PRESETS[key]
