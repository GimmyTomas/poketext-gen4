"""
Tool to extract character templates from game screenshots.

Usage:
    python tools/extract_templates.py <screenshot> "<text_line1>" ["<text_line2>"]

The screenshot should be at DS native resolution (256x192) or an integer multiple.
The text should match exactly what's shown in the textbox.
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Character dimensions in DS native resolution
# Pokemon Gen 4 uses a variable-width font, but most characters are close to 6 pixels wide
# Height is consistently 14 pixels for the main text area

CHAR_HEIGHT = 14  # Height of character cell
LINE_HEIGHT = 16  # Distance between line tops

# Textbox text region coordinates (DS native 256x192)
TEXT_X = 14       # X start of text
TEXT_Y_LINE1 = 152  # Y start of first line
TEXT_Y_LINE2 = 168  # Y start of second line


class CharacterWidths:
    """Character width definitions for the Pokemon Gen 4 font.

    Measured from actual game screenshots at native DS resolution.
    Each width includes the character plus its natural spacing.
    """

    # Character width table (measured from game)
    # Format: character -> width in pixels
    WIDTHS = {
        # Lowercase letters
        'a': 5, 'b': 5, 'c': 5, 'd': 5, 'e': 5,
        'f': 4, 'g': 5, 'h': 5, 'i': 3, 'j': 4,
        'k': 5, 'l': 3, 'm': 7, 'n': 5, 'o': 6,
        'p': 5, 'q': 5, 'r': 4, 's': 5, 't': 4,
        'u': 5, 'v': 5, 'w': 7, 'x': 5, 'y': 5, 'z': 5,

        # Uppercase letters
        'A': 6, 'B': 6, 'C': 6, 'D': 6, 'E': 5,
        'F': 5, 'G': 6, 'H': 6, 'I': 4, 'J': 5,
        'K': 6, 'L': 5, 'M': 7, 'N': 6, 'O': 6,
        'P': 5, 'Q': 6, 'R': 6, 'S': 5, 'T': 6,
        'U': 6, 'V': 6, 'W': 7, 'X': 6, 'Y': 6, 'Z': 5,

        # Numbers
        '0': 5, '1': 4, '2': 5, '3': 5, '4': 5,
        '5': 5, '6': 5, '7': 5, '8': 5, '9': 5,

        # Punctuation
        ' ': 4,
        '.': 3, ',': 3, '!': 3, '?': 5,
        "'": 3, '"': 5, ':': 3, ';': 3,
        '-': 4, '/': 4, '(': 4, ')': 4,

        # Accented (Italian/Western)
        'à': 5, 'è': 5, 'é': 5, 'ì': 3, 'ò': 6, 'ù': 5,
        'á': 5, 'í': 3, 'ó': 6, 'ú': 5,
        'â': 5, 'ê': 5, 'î': 3, 'ô': 6, 'û': 5,
        'ä': 5, 'ë': 5, 'ï': 3, 'ö': 6, 'ü': 5,
        'ñ': 5, 'ç': 5,
    }

    DEFAULT_WIDTH = 5

    @classmethod
    def get_width(cls, char: str) -> int:
        return cls.WIDTHS.get(char, cls.DEFAULT_WIDTH)


def extract_textbox_region(image: np.ndarray) -> np.ndarray:
    """Extract the textbox region from a screenshot."""
    height, width = image.shape[:2]

    # Calculate scale factor
    scale = width // 256
    if scale < 1:
        scale = 1

    # Scale coordinates
    x = TEXT_X * scale
    y1 = TEXT_Y_LINE1 * scale
    w = 220 * scale
    h = 32 * scale

    return image[y1:y1+h, x:x+w], scale


def normalize_image(image: np.ndarray) -> np.ndarray:
    """Normalize image to DS native resolution."""
    height, width = image.shape[:2]

    if width != 256 or height != 192:
        scale = width // 256
        if scale > 1:
            return cv2.resize(image, (256, 192), interpolation=cv2.INTER_AREA)

    return image


def extract_characters(image: np.ndarray, text: str, line: int = 1) -> dict:
    """
    Extract individual character images from a text line.

    Uses the CharacterWidths table to determine character boundaries.

    Args:
        image: Normalized screenshot (256x192)
        text: The text content of the line
        line: Line number (1 or 2)

    Returns:
        Dictionary mapping characters to their images
    """
    # Get the line region
    y_start = TEXT_Y_LINE1 if line == 1 else TEXT_Y_LINE2
    line_region = image[y_start:y_start + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]

    characters = {}
    x = 0

    for char in text:
        width = CharacterWidths.get_width(char)

        if x + width > line_region.shape[1]:
            print(f"  Warning: Character '{char}' at x={x} exceeds line width")
            break

        # Extract character region
        char_img = line_region[:, x:x + width]

        # Store non-space characters
        if char != ' ' and char not in characters:
            characters[char] = char_img.copy()

        x += width

    return characters


def save_templates(characters: dict, output_dir: Path, prefix: str = ""):
    """Save extracted characters as template images."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Character to filename mapping for special characters
    special_names = {
        ' ': 'space',
        '.': 'period',
        ',': 'comma',
        '!': 'exclaim',
        '?': 'question',
        "'": 'apostrophe',
        '"': 'quote',
        ':': 'colon',
        ';': 'semicolon',
        '-': 'hyphen',
        '/': 'slash',
        '(': 'lparen',
        ')': 'rparen',
        '[': 'lbracket',
        ']': 'rbracket',
        '+': 'plus',
        '=': 'equals',
        '*': 'asterisk',
        '&': 'ampersand',
        '%': 'percent',
        '#': 'hash',
        '@': 'at',
        'à': 'a_grave',
        'è': 'e_grave',
        'é': 'e_acute',
        'ì': 'i_grave',
        'ò': 'o_grave',
        'ù': 'u_grave',
    }

    saved = []
    for char, img in characters.items():
        # Determine filename
        if char in special_names:
            name = special_names[char]
        elif char.isupper():
            name = f"upper_{char}"
        else:
            name = char

        filename = f"{prefix}{name}.png" if prefix else f"{name}.png"
        filepath = output_dir / filename

        # Save (don't overwrite existing unless forced)
        if not filepath.exists():
            cv2.imwrite(str(filepath), img)
            saved.append(char)
            print(f"  Saved: {filename} ('{char}')")
        else:
            print(f"  Skipped: {filename} (already exists)")

    return saved


def analyze_screenshot(image_path: str, line1_text: str, line2_text: str = ""):
    """Analyze a screenshot and extract character templates."""

    print(f"Loading: {image_path}")
    image = cv2.imread(image_path)

    if image is None:
        print(f"Error: Could not load image: {image_path}")
        return

    print(f"Image size: {image.shape[1]}x{image.shape[0]}")

    # Normalize to DS resolution
    normalized = normalize_image(image)
    print(f"Normalized to: {normalized.shape[1]}x{normalized.shape[0]}")

    # Extract text region for visualization
    text_region = normalized[TEXT_Y_LINE1:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]

    # Save text region for inspection
    cv2.imwrite("debug_text_region.png", text_region)

    # Enlarge for better visibility
    enlarged = cv2.resize(text_region, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("debug_text_region_4x.png", enlarged)
    print("Saved debug_text_region.png and debug_text_region_4x.png")

    # Extract characters from line 1
    all_chars = {}

    if line1_text:
        print(f"\nLine 1: '{line1_text}'")
        chars1 = extract_characters(normalized, line1_text, line=1)
        all_chars.update(chars1)
        print(f"  Extracted {len(chars1)} unique characters")

    if line2_text:
        print(f"\nLine 2: '{line2_text}'")
        chars2 = extract_characters(normalized, line2_text, line=2)
        all_chars.update(chars2)
        print(f"  Extracted {len(chars2)} unique characters")

    # Save templates
    output_dir = Path("templates/western")
    print(f"\nSaving templates to: {output_dir}")
    saved = save_templates(all_chars, output_dir)
    print(f"\nTotal new characters saved: {len(saved)}")

    return all_chars


def interactive_calibration(image_path: str):
    """Interactive tool to calibrate character positions."""

    print(f"Loading: {image_path}")
    image = cv2.imread(image_path)

    if image is None:
        print(f"Error: Could not load image")
        return

    normalized = normalize_image(image)

    # Draw grid lines on the text area
    debug = normalized.copy()

    # Draw text region bounds
    cv2.rectangle(debug, (TEXT_X, TEXT_Y_LINE1), (TEXT_X + 220, TEXT_Y_LINE2 + CHAR_HEIGHT), (0, 255, 0), 1)

    # Draw line separators
    cv2.line(debug, (TEXT_X, TEXT_Y_LINE2), (TEXT_X + 220, TEXT_Y_LINE2), (255, 0, 0), 1)

    # Draw vertical grid every 6 pixels (default char width)
    for x in range(TEXT_X, TEXT_X + 220, 6):
        cv2.line(debug, (x, TEXT_Y_LINE1), (x, TEXT_Y_LINE2 + CHAR_HEIGHT), (128, 128, 128), 1)

    cv2.imwrite("debug_calibration.png", debug)

    # Enlarge
    enlarged = cv2.resize(debug, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("debug_calibration_4x.png", enlarged)

    print("Saved debug_calibration.png and debug_calibration_4x.png")
    print("Check these images to verify text alignment.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print('  python tools/extract_templates.py screenshot.png "First line" "Second line"')
        print('  python tools/extract_templates.py screenshot.png --calibrate')
        sys.exit(1)

    image_path = sys.argv[1]

    if len(sys.argv) > 2 and sys.argv[2] == "--calibrate":
        interactive_calibration(image_path)
    else:
        line1 = sys.argv[2] if len(sys.argv) > 2 else ""
        line2 = sys.argv[3] if len(sys.argv) > 3 else ""
        analyze_screenshot(image_path, line1, line2)
