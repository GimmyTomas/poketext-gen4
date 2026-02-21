"""Character template extraction with precise boundary detection.

Font structure:
- Dark pixels (81): Character body
- Gray pixels (162): Shadow/anti-aliasing at edges
- White pixels (251): Background

Boundary rules:
- Left boundary: First dark pixel column
- Right boundary: Last gray pixel column before next dark or white
- Characters do not overlap
"""

import cv2
import numpy as np
from pathlib import Path
import shutil


# Text region in DS native coordinates
TEXT_Y_START = 154  # First row with dark pixels
TEXT_Y_END = 167    # Exclusive (154-166 inclusive = 13 pixels)
TEXT_X = 14         # X offset from screen edge

# Pixel values
DARK = 81
GRAY = 162
WHITE = 251


def char_to_filename(char: str) -> str:
    """Convert character to safe filename."""
    special = {
        ' ': 'space', '.': 'period', ',': 'comma', '!': 'exclaim',
        '?': 'question', "'": 'apostrophe', '"': 'quote',
        ':': 'colon', ';': 'semicolon', '-': 'hyphen',
        '/': 'slash', '(': 'lparen', ')': 'rparen',
        'è': 'e_grave', 'à': 'a_grave', 'é': 'e_acute',
        'ì': 'i_grave', 'ò': 'o_grave', 'ù': 'u_grave',
        'È': 'upper_E_grave', 'À': 'upper_A_grave', 'É': 'upper_E_acute',
        'Ì': 'upper_I_grave', 'Ò': 'upper_O_grave', 'Ù': 'upper_U_grave',
        '+': 'plus', '=': 'equals', '*': 'asterisk',
        '@': 'at', '#': 'hash', '%': 'percent',
        '…': 'ellipsis', '·': 'dot', '×': 'times',
    }
    if char in special:
        return special[char]
    if char.isupper() and char.isascii():
        return f'upper_{char}'
    return char


def find_character_boundaries(line: np.ndarray) -> list:
    """Find character boundaries using dark/gray/white pixel analysis.

    Returns list of (start_x, end_x) tuples for each character.
    """
    boundaries = []
    x = 0
    width = line.shape[1]

    while x < width:
        col = line[:, x]
        has_dark = (col == DARK).any()

        if not has_dark:
            x += 1
            continue

        # Found start of character (dark pixel)
        char_start = x

        # Find end of character
        while x < width:
            col = line[:, x]
            has_dark = (col == DARK).any()
            has_gray = (col == GRAY).any()
            is_white = not has_dark and not has_gray

            if has_dark:
                x += 1
            elif has_gray:
                # Check next column
                if x + 1 < width:
                    next_col = line[:, x + 1]
                    next_dark = (next_col == DARK).any()
                    if next_dark:
                        # This gray is end of current char
                        boundaries.append((char_start, x))
                        x += 1
                        break
                    else:
                        x += 1
                else:
                    boundaries.append((char_start, x))
                    x += 1
                    break
            else:  # White
                # End of character was previous column
                boundaries.append((char_start, x - 1))
                break

    return boundaries


def extract_line(img: np.ndarray, y_start: int, text: str, output_dir: Path, line_num: int = 1):
    """Extract characters from a line of text."""
    line = img[y_start:y_start + (TEXT_Y_END - TEXT_Y_START), TEXT_X:TEXT_X + 230]

    # Find character boundaries
    boundaries = find_character_boundaries(line)

    # Remove spaces from text for matching
    chars = [c for c in text if c != ' ']

    print(f"  Line {line_num}: \"{text}\"")
    print(f"    Found {len(boundaries)} chars, expected {len(chars)}")

    if len(boundaries) != len(chars):
        print(f"    WARNING: Mismatch! Boundaries: {boundaries[:10]}...")
        return []

    extracted = []
    for (start, end), char in zip(boundaries, chars):
        char_img = line[:, start:end + 1]  # +1 because end is inclusive
        filename = char_to_filename(char) + '.png'
        filepath = output_dir / filename

        if not filepath.exists():
            cv2.imwrite(str(filepath), char_img)
            extracted.append(char)
            print(f"    '{char}' : x={start}-{end} (w={end - start + 1}) -> {filename}")

    return extracted


def main():
    output_dir = Path("templates/western")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = Path("game-data/letters")

    # Define all screenshots with their text content
    # Format: (filename, line1_text, line2_text or None)
    screenshots = [
        # 2026 naming screenshots (single line)
        ("Screenshot 2026-02-21 alle 10.32.59.png", "Ti chiami bjkxyAB, giusto?", None),
        ("Screenshot 2026-02-21 alle 10.33.37.png", "Ti chiami DEFGHJK, giusto?", None),
        ("Screenshot 2026-02-21 alle 10.34.23.png", "Ti chiami LMOQTUV, giusto?", None),
        ("Screenshot 2026-02-21 alle 10.34.56.png", "Ti chiami WXYZ012, giusto?", None),
        ("Screenshot 2026-02-21 alle 10.35.19.png", "Ti chiami 3456789, giusto?", None),
        ("Screenshot 2026-02-21 alle 10.36.37.png", "Ti chiami ÀÈÉÌÒÙ-, giusto?", None),
        ("Screenshot 2026-02-21 alle 10.37.41.png", "Ti chiami àèéìòù, giusto?", None),  # Need to verify exact chars
        ("Screenshot 2026-02-21 alle 10.38.32.png", "Ti chiami ;;!'\"\", giusto?", None),  # Punctuation
        ("Screenshot 2026-02-21 alle 10.39.12.png", "Ti chiami ()…·×@#, giusto?", None),  # Special

        # 2024 dialogue screenshots (two lines)
        ("Screenshot 2024-01-21 alle 13.50.51.png", "C è venuto a cercarti poco", "fa."),
        ("Screenshot 2024-01-21 alle 13.50.56.png", "Non so di che cosa si trattasse, ma", "diceva che dovresti prendere un"),
        ("Screenshot 2024-01-21 alle 13.51.01.png", "diceva che dovresti prendere un", "traghetto a Nevepoli."),
        ("Screenshot 2024-01-21 alle 13.51.05.png", "Sai quant'è impaziente. Se n'è andato", "prima che potessi chiedere qualcosa."),
        ("Screenshot 2024-01-21 alle 13.51.11.png", "Come stanno andando le cose, tesoro?", None),
        ("Screenshot 2024-01-21 alle 13.51.14.png", "Il progetto con il Prof. Rowan fa", "progressi?"),
    ]

    for filename, line1, line2 in screenshots:
        path = base / filename
        if not path.exists():
            print(f"Skipping {filename} - not found")
            continue

        print(f"\n{filename}:")
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

        # Extract line 1
        extract_line(img, TEXT_Y_START, line1, output_dir, 1)

        # Extract line 2 if present (starts at y=171)
        if line2:
            extract_line(img, 171, line2, output_dir, 2)

    # Count results
    templates = list(output_dir.glob("*.png"))
    print(f"\n=== Extracted {len(templates)} templates ===")

    # Verify templates
    print("\nVerifying templates...")
    problems = []
    for t in sorted(templates):
        img = cv2.imread(str(t), cv2.IMREAD_GRAYSCALE)
        has_dark = (img == DARK).any()
        has_gray = (img == GRAY).any()

        if not has_dark:
            problems.append((t.name, "no dark pixels"))
        elif img.shape[0] != TEXT_Y_END - TEXT_Y_START:
            problems.append((t.name, f"wrong height: {img.shape[0]}"))

    if problems:
        print("Problems found:")
        for name, issue in problems:
            print(f"  {name}: {issue}")
    else:
        print("All templates OK!")


if __name__ == "__main__":
    main()
