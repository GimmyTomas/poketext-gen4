"""Textbox detection for Pokemon Gen 4 games."""

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum, auto


class TextboxState(Enum):
    """State of the textbox."""
    CLOSED = auto()           # No textbox visible
    OPEN = auto()             # Textbox open with text
    OPEN_EMPTY = auto()       # Textbox open but empty (text about to appear)
    SCROLLING = auto()        # Text is scrolling to next line
    INSTANT = auto()          # Instant text (we ignore this)


@dataclass
class TextboxRegion:
    """Region of the textbox within the top screen (in DS native coordinates)."""
    # Standard textbox position in DS coordinates (256x192)
    # The textbox appears at the bottom of the top screen
    x: int = 8
    y: int = 144
    width: int = 240
    height: int = 48

    # Text area within the textbox (excluding borders)
    text_x: int = 14
    text_y: int = 155  # Text line 1 starts at y=155
    text_width: int = 220
    text_height: int = 30  # Covers line 1 (155-169) and line 2 (171-185)

    # Line positions (relative to text_y)
    line1_y: int = 0
    line2_y: int = 16


class TextboxDetector:
    """Detects textbox state in Pokemon Gen 4 games."""

    # Color thresholds for white detection (textbox background is white)
    WHITE_THRESHOLD = 235

    # Coordinates for detection strips (in DS native resolution)
    # These are horizontal lines we check to determine textbox state

    def __init__(self, game: str = "diamond_pearl"):
        """
        Initialize the textbox detector.

        Args:
            game: One of "diamond_pearl", "platinum", "hgss"
        """
        self.game = game
        self.region = TextboxRegion()

        # Detection strip coordinates (y positions, relative to screen)
        # Based on the original C++ implementation
        self._setup_detection_strips()

    def _setup_detection_strips(self):
        """Set up the horizontal strips used for textbox detection."""
        # These strips are checked to determine textbox state
        # A white strip indicates the textbox background

        # Strip below second line of text (y=183 in original)
        self.bottom_strip_y = 183

        # Strip between lines (y=168 in original)
        self.mid_strip_y = 168

        # Strip above first line (y=152 in original)
        self.top_strip_y = 152

        # X range for strips (center region only to avoid border pixels)
        # HGSS has wider frame borders that get blended when scaling
        self.strip_x_start = 80   # Skip left border area
        self.strip_x_end = 176    # Skip right border area (96 pixel center strip)

        # Tolerance for white strip detection (game-specific)
        # DP needs strict tolerance (2%) to correctly detect scrolling
        # HGSS needs looser tolerance (20%) due to frame border blending
        if self.game == "hgss":
            self.strip_tolerance = 0.20
        else:
            self.strip_tolerance = 0.02

    def detect_state(self, screen: np.ndarray) -> TextboxState:
        """
        Detect the textbox state from a top screen image.

        Args:
            screen: Top screen image in DS native resolution (256x192, BGR)

        Returns:
            TextboxState indicating the current state
        """
        # Check if textbox is open by looking at key regions

        # 1. Check bottom white line (must be white for textbox to be open)
        if not self._is_strip_white(screen, self.bottom_strip_y):
            return TextboxState.CLOSED

        # 2. Check left border (must NOT be white for textbox to be open)
        if self._is_left_border_white(screen):
            return TextboxState.CLOSED

        # 3. Check right border (must NOT be white for textbox to be open)
        if self._is_right_border_white(screen):
            return TextboxState.CLOSED

        # Textbox is open, determine specific state

        # Check middle strip to detect scrolling
        if self._is_strip_white(screen, self.mid_strip_y):
            # Check top strip
            if self._is_strip_white(screen, self.top_strip_y):
                return TextboxState.OPEN
            else:
                return TextboxState.SCROLLING
        else:
            # Middle strip not white - could be scrolling or different state
            return TextboxState.SCROLLING

    def _is_strip_white(self, screen: np.ndarray, y: int, tolerance: float = None) -> bool:
        """Check if a horizontal strip is mostly white."""
        if tolerance is None:
            tolerance = self.strip_tolerance
        strip = screen[y, self.strip_x_start:self.strip_x_end]

        # Check each pixel's RGB values
        white_pixels = 0
        total_pixels = strip.shape[0]

        for pixel in strip:
            b, g, r = pixel
            if r > self.WHITE_THRESHOLD and g > self.WHITE_THRESHOLD and b > self.WHITE_THRESHOLD:
                white_pixels += 1

        return white_pixels > total_pixels * (1 - tolerance)

    def _is_left_border_white(self, screen: np.ndarray) -> bool:
        """Check if left border of textbox area is white (indicating no textbox)."""
        # Check a strip on the left side of the textbox region
        x_start = 0
        x_end = 8
        y_start = 144
        y_end = 192

        region = screen[y_start:y_end, x_start:x_end]
        mean_val = np.mean(region)

        return mean_val > self.WHITE_THRESHOLD

    def _is_right_border_white(self, screen: np.ndarray) -> bool:
        """Check if right border of textbox area is white (indicating no textbox)."""
        # Check a strip on the right side of the textbox region
        x_start = 248
        x_end = 256
        y_start = 144
        y_end = 192

        region = screen[y_start:y_end, x_start:x_end]
        mean_val = np.mean(region)

        return mean_val > self.WHITE_THRESHOLD

    def extract_text_region(self, screen: np.ndarray) -> np.ndarray:
        """Extract the text region from the screen for OCR."""
        return screen[
            self.region.text_y:self.region.text_y + self.region.text_height,
            self.region.text_x:self.region.text_x + self.region.text_width
        ]

    def is_text_appearing(self, prev_text_region: np.ndarray,
                          curr_text_region: np.ndarray,
                          threshold: int = 50) -> bool:
        """
        Check if new text is appearing (character by character).

        This detects the "slow text" we want to extract by comparing
        consecutive frames to see if new characters are appearing.

        Args:
            prev_text_region: Text region from previous frame
            curr_text_region: Text region from current frame
            threshold: Minimum pixel difference to count as change

        Returns:
            True if text appears to be incrementally appearing
        """
        if prev_text_region.shape != curr_text_region.shape:
            return False

        # Calculate absolute difference
        diff = cv2.absdiff(prev_text_region, curr_text_region)

        # Count changed pixels
        changed_mask = np.any(diff > threshold, axis=2)
        changed_pixels = np.sum(changed_mask)

        # For slow text, we expect small incremental changes (one character)
        # A character is roughly 8x16 pixels = 128 pixels
        # Allow some variance: 50-500 changed pixels indicates one character
        return 50 < changed_pixels < 500

    def has_continue_marker(self, screen: np.ndarray) -> bool:
        """
        Check if the "press button to continue" marker is visible.

        This marker appears at the bottom-right of the textbox when slow text
        has finished typing and the player can press a button to continue.
        It's a small triangle/arrow indicator inside the textbox.

        The key difference from instant text (name entry boxes):
        - Slow text: Has white textbox background with dark triangle marker
        - Instant text: Has uniform gray (name entry box) with NO dark pixels

        Args:
            screen: Top screen image in DS native resolution (256x192, BGR)

        Returns:
            True if the continue marker is present (slow text complete)
        """
        # Inner textbox marker region: y=175-186, x=230-248
        # This is inside the textbox, avoiding the border
        marker_region = screen[175:186, 230:248]

        # Convert to grayscale
        if len(marker_region.shape) == 3:
            gray = cv2.cvtColor(marker_region, cv2.COLOR_BGR2GRAY)
        else:
            gray = marker_region

        # Check for white pixels (textbox background)
        white_pixels = np.sum(gray > 230)

        # Check for dark pixels (the triangle marker shape)
        dark_pixels = np.sum(gray < 100)

        # Continue marker characteristics:
        # - Has white pixels (>40) from textbox background showing
        # - Has dark pixels (>=2) for the small triangle marker
        # Instant text (name entry) has:
        # - Uniform gray (name entry box), NO dark pixels
        return white_pixels > 40 and dark_pixels >= 2

