"""Screen layout detection for DS video recordings."""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple


# DS native resolution
DS_WIDTH = 256
DS_HEIGHT = 192


class ScreenPosition(Enum):
    """Position of the top screen in the video."""
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()


@dataclass
class ScreenLayout:
    """Detected screen layout information."""
    top_screen_pos: ScreenPosition
    top_screen_rect: Tuple[int, int, int, int]  # (x, y, width, height)
    bottom_screen_rect: Optional[Tuple[int, int, int, int]]
    scale_factor: float  # Relative to DS native resolution

    @property
    def is_integer_scale(self) -> bool:
        """Check if scale is an integer multiple (sharp pixels)."""
        return abs(self.scale_factor - round(self.scale_factor)) < 0.01


def detect_screen_layout(frame: np.ndarray) -> ScreenLayout:
    """
    Detect the screen layout from a video frame.

    The top screen is typically larger than the bottom screen in recordings.
    It can be positioned on the left, right, top, or bottom of the frame.

    Args:
        frame: A video frame (BGR format from OpenCV)

    Returns:
        ScreenLayout with detected positions and scale
    """
    height, width = frame.shape[:2]

    # Common layouts:
    # 1. Side by side: top screen on right (larger), bottom on left (smaller)
    # 2. Side by side: top screen on left (larger), bottom on right (smaller)
    # 3. Stacked: top screen above, bottom screen below
    # 4. Top screen only

    # For now, implement the most common case: side by side with top screen larger
    # We detect this by looking for a vertical split where one side is larger

    # Heuristic: if width > height * 1.5, likely side by side
    if width > height * 1.5:
        # Side by side layout
        # The larger portion is the top screen
        # Common ratios: 3:1 (top is 3x size of bottom) or 2:1

        # Try to find the split point by looking for a consistent vertical line
        # For now, use a simple heuristic based on common aspect ratios

        # If top screen is on the right and 3x larger:
        # total_width = bottom_width + top_width = w + 3w = 4w
        # So top_width = 3/4 * total_width

        # Check if right side is larger (more common)
        split_3_4 = int(width * 0.25)  # Bottom screen would be 1/4 width
        split_1_4 = int(width * 0.75)  # Top screen starts at 3/4

        # For 2x scaling: top is 512 wide, bottom is 256, total 768
        # split at 256 (1/3)
        split_1_3 = int(width / 3)
        split_2_3 = int(width * 2 / 3)

        # Estimate scale from height (top screen should be close to height)
        # DS height is 192, so scale = frame_height / 192
        estimated_scale = height / DS_HEIGHT
        top_screen_width = int(DS_WIDTH * estimated_scale)

        # Determine if top screen is on left or right
        # by checking which side has dimensions closer to expected
        right_width = width - split_1_3
        left_width = split_2_3

        # The top screen width should be approximately scale * 256
        if abs(right_width - top_screen_width) < abs(left_width - top_screen_width):
            # Top screen is on the right
            return ScreenLayout(
                top_screen_pos=ScreenPosition.RIGHT,
                top_screen_rect=(width - top_screen_width, 0, top_screen_width, height),
                bottom_screen_rect=(0, 0, width - top_screen_width, height),
                scale_factor=estimated_scale
            )
        else:
            # Top screen is on the left
            return ScreenLayout(
                top_screen_pos=ScreenPosition.LEFT,
                top_screen_rect=(0, 0, top_screen_width, height),
                bottom_screen_rect=(top_screen_width, 0, width - top_screen_width, height),
                scale_factor=estimated_scale
            )

    elif height > width * 1.5:
        # Stacked layout (top screen above bottom screen)
        estimated_scale = width / DS_WIDTH
        top_screen_height = int(DS_HEIGHT * estimated_scale)

        return ScreenLayout(
            top_screen_pos=ScreenPosition.TOP,
            top_screen_rect=(0, 0, width, top_screen_height),
            bottom_screen_rect=(0, top_screen_height, width, height - top_screen_height),
            scale_factor=estimated_scale
        )

    else:
        # Assume top screen only or 1:1 aspect
        estimated_scale = min(width / DS_WIDTH, height / DS_HEIGHT)

        return ScreenLayout(
            top_screen_pos=ScreenPosition.LEFT,
            top_screen_rect=(0, 0, width, height),
            bottom_screen_rect=None,
            scale_factor=estimated_scale
        )


def extract_top_screen(frame: np.ndarray, layout: ScreenLayout) -> np.ndarray:
    """Extract the top screen region from a frame."""
    x, y, w, h = layout.top_screen_rect
    return frame[y:y+h, x:x+w]


def normalize_to_ds_resolution(screen: np.ndarray, layout: ScreenLayout) -> np.ndarray:
    """
    Scale the screen image to DS native resolution (256x192).

    This makes template matching consistent regardless of recording resolution.
    """
    return cv2.resize(screen, (DS_WIDTH, DS_HEIGHT), interpolation=cv2.INTER_AREA)
