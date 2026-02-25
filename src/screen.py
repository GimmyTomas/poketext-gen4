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


def _find_screen_boundary(frame: np.ndarray, expected_width: int) -> Optional[int]:
    """
    Find the left boundary of the DS screen using edge detection.

    Some recordings have timer overlays (LiveSplit) that offset the DS screen.
    This function finds strong vertical edges that might indicate screen boundaries.

    Args:
        frame: Video frame (BGR)
        expected_width: Expected width of the DS top screen

    Returns:
        X coordinate of the left boundary, or None if no strong boundary found
    """
    height, width = frame.shape[:2]

    # Expected x position (top screen on right edge)
    expected_x = width - expected_width

    # Convert to grayscale and find vertical edges
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_x = np.abs(sobel_x)

    # Sum along columns to find strong vertical lines
    col_edges = np.sum(sobel_x, axis=0)

    # Look for the strongest edge in a wide region around expected boundary
    search_start = max(0, expected_x - 100)
    search_end = min(width, expected_x + 100)

    if search_end > search_start:
        search_region = col_edges[search_start:search_end]
        max_edge_idx = np.argmax(search_region)
        max_edge_val = search_region[max_edge_idx]

        # Threshold: edge must be significantly strong (> 50% of max overall)
        if max_edge_val > np.max(col_edges) * 0.5:
            return search_start + max_edge_idx

    return None


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
        # Determine if simple detection would put screen on LEFT or RIGHT
        would_be_right = abs(right_width - top_screen_width) < abs(left_width - top_screen_width)
        simple_x = (width - top_screen_width) if would_be_right else 0

        # Use edge detection to find the actual screen boundary
        # This helps when there's a timer overlay (like LiveSplit) that offsets the screen
        top_x = _find_screen_boundary(frame, top_screen_width)

        # Only use edge detection result if it differs significantly from simple detection
        # OR if simple detection would put screen at x=0 but edge detection finds otherwise
        if top_x is not None and (abs(top_x - simple_x) > 10 or (simple_x == 0 and top_x > 10)):
            return ScreenLayout(
                top_screen_pos=ScreenPosition.RIGHT if top_x > 0 else ScreenPosition.LEFT,
                top_screen_rect=(top_x, 0, top_screen_width, height),
                bottom_screen_rect=(0, 0, top_x, height) if top_x > 0 else (top_screen_width, 0, width - top_screen_width, height),
                scale_factor=estimated_scale
            )
        elif would_be_right:
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
    Uses INTER_LINEAR for speed (5-6x faster than INTER_AREA with same OCR quality).
    """
    return cv2.resize(screen, (DS_WIDTH, DS_HEIGHT), interpolation=cv2.INTER_LINEAR)
