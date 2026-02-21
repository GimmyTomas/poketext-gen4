"""
Interactive tool to measure character widths from screenshots.
Outputs a pixel-by-pixel view of the text region.
"""

import cv2
import numpy as np
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Text region coordinates (DS native 256x192)
TEXT_X = 14
TEXT_Y_LINE1 = 152
TEXT_Y_LINE2 = 168
CHAR_HEIGHT = 14


def create_measurement_image(image_path: str, output_name: str = "measure"):
    """Create images for measuring character widths."""

    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        return

    h, w = image.shape[:2]
    print(f"Image size: {w}x{h}")

    # Normalize if needed
    if w != 256:
        scale = w // 256
        if scale > 1:
            image = cv2.resize(image, (256, 192), interpolation=cv2.INTER_AREA)

    # Extract text region (both lines)
    text_region = image[TEXT_Y_LINE1:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]

    # Create enlarged version with pixel grid
    scale = 8
    enlarged = cv2.resize(text_region, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)

    # Draw grid lines
    h, w = enlarged.shape[:2]

    # Vertical lines (every pixel in original = every 8 pixels here)
    for x in range(0, w, scale):
        color = (200, 200, 200) if (x // scale) % 5 != 0 else (100, 100, 255)
        thickness = 1 if (x // scale) % 5 != 0 else 1
        cv2.line(enlarged, (x, 0), (x, h), color, thickness)

    # Horizontal lines
    for y in range(0, h, scale):
        color = (200, 200, 200) if (y // scale) % 5 != 0 else (100, 100, 255)
        cv2.line(enlarged, (0, y), (w, y), color, thickness)

    # Line separator
    line_sep_y = (TEXT_Y_LINE2 - TEXT_Y_LINE1) * scale
    cv2.line(enlarged, (0, line_sep_y), (w, line_sep_y), (0, 255, 0), 2)

    # Add x-coordinate labels at top
    for x in range(0, w, scale * 10):
        label = str(x // scale)
        cv2.putText(enlarged, label, (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    cv2.imwrite(f"{output_name}_grid.png", enlarged)
    print(f"Saved: {output_name}_grid.png")

    # Also save just the text region enlarged (no grid) for reference
    clean_enlarged = cv2.resize(text_region, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f"{output_name}_clean.png", clean_enlarged)
    print(f"Saved: {output_name}_clean.png")

    print("\nOpen the _grid.png image and count pixels to measure character widths.")
    print("The green line separates line 1 (top) from line 2 (bottom).")
    print("Blue lines mark every 5 pixels for easier counting.")


def create_char_width_table():
    """Print a template for the character width table."""

    print("\n" + "=" * 60)
    print("CHARACTER WIDTH MEASUREMENTS")
    print("=" * 60)
    print("""
After measuring the characters in the grid image, fill in the widths below.
Each character should include any trailing whitespace that belongs to it.

Example format (update the CHAR_WIDTHS dict in extract_templates.py):

CHAR_WIDTHS = {
    'a': 5, 'b': 5, 'c': 5, 'd': 5, 'e': 5,
    'f': 4, 'g': 5, 'h': 5, 'i': 2, 'j': 3,
    # ... etc
    'A': 6, 'B': 6, 'C': 6,
    # ... etc
    ' ': 4,  # space
    '.': 2, ',': 2, '!': 2, '?': 5,
    # accented
    'è': 5, 'é': 5, 'à': 5,
    # ... etc
}
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/measure_chars.py <screenshot.png> [output_name]")
        sys.exit(1)

    image_path = sys.argv[1]
    output_name = sys.argv[2] if len(sys.argv) > 2 else "measure"

    create_measurement_image(image_path, output_name)
    create_char_width_table()
