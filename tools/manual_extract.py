"""
Manual character extraction with precise boundaries determined by visual inspection.

Text Y boundaries: y=155-168 (14 pixels) - contains all letter content including
dots (i) and descenders (g, j, y, q).

For each screenshot, specify the exact x boundaries of each character.
"""

import cv2
import numpy as np
from pathlib import Path
import shutil

# Text region in DS native coordinates
TEXT_Y_START = 155
TEXT_Y_END = 169  # 14 pixels tall (inclusive would be 168, but Python slicing needs 169)
TEXT_X_OFFSET = 14  # X offset from screen edge to text start

def char_to_filename(char: str) -> str:
    """Convert character to safe filename."""
    special = {
        ' ': 'space', '.': 'period', ',': 'comma', '!': 'exclaim',
        '?': 'question', "'": 'apostrophe', '"': 'quote',
        ':': 'colon', ';': 'semicolon', '-': 'hyphen',
        '/': 'slash', '(': 'lparen', ')': 'rparen',
        'è': 'e_grave', 'à': 'a_grave', 'é': 'e_acute',
        'ì': 'i_grave', 'ò': 'o_grave', 'ù': 'u_grave',
    }
    if char in special:
        return special[char]
    if char.isupper() and char.isascii():
        return f'upper_{char}'
    return char


def extract_char(img, x_start, x_end):
    """Extract a character from the image.

    x_start and x_end are relative to TEXT_X_OFFSET.
    """
    line = img[TEXT_Y_START:TEXT_Y_END, TEXT_X_OFFSET:]
    return line[:, x_start:x_end]


def extract_and_save(img_path, char_specs, output_dir):
    """Extract characters from an image based on specifications.

    char_specs: list of (char, x_start, x_end) tuples
    """
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"  Error: Could not load {img_path}")
        return []

    extracted = []
    for char, x_start, x_end in char_specs:
        char_img = extract_char(img, x_start, x_end)

        filename = char_to_filename(char) + '.png'
        filepath = output_dir / filename

        if not filepath.exists():
            cv2.imwrite(str(filepath), char_img)
            extracted.append(char)
            print(f"  '{char}' x={x_start}-{x_end} (w={x_end-x_start}) -> {filename}")

    return extracted


def main():
    output_dir = Path("templates/western")

    # Clear existing templates
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_path = Path("game-data/letters")

    # Screenshot 1: "Ti chiami bjkxyAB, giusto?"
    # Manually determined character boundaries (x relative to TEXT_X_OFFSET)
    print("\nScreenshot 1: Ti chiami bjkxyAB, giusto?")
    extract_and_save(
        base_path / "Screenshot 2026-02-21 alle 10.32.59.png",
        [
            ('T', 2, 7),     # x=2-6, width 5
            ('i', 7, 10),    # x=7-9, width 3 (includes anti-aliasing)
            # space at 10-14
            ('c', 15, 20),   # x=15-19, width 5
            ('h', 20, 26),   # x=20-25, width 6 (includes leading gray)
            # 'i' after h shares column with h, skip for now
            ('a', 29, 35),   # x=29-34, width 6
            ('m', 35, 44),   # x=35-43, width 9 (wide letter)
            # space
            ('b', 49, 54),   # x=49-53, width 5
            ('j', 54, 59),   # x=54-58, width 5 (includes descender)
            ('k', 59, 65),   # x=59-64, width 6
            ('x', 65, 71),   # x=65-70, width 6
            ('y', 71, 77),   # x=71-76, width 6 (includes descender)
            ('A', 77, 83),   # x=77-82, width 6
            ('B', 83, 90),   # x=83-89, width 7
            (',', 90, 94),   # x=90-93, width 4
            # space
            ('g', 99, 104),  # x=99-103, width 5
            # 'i' skip (would overlap with 'u')
            ('u', 107, 113), # x=107-112, width 6
            ('s', 113, 119), # x=113-118, width 6
            ('t', 119, 125), # x=119-124, width 6
            ('o', 125, 131), # x=125-130, width 6
            ('?', 131, 138), # x=131-137, width 7
        ],
        output_dir
    )

    # Screenshot 2: "Ti chiami DEFGHJK, giusto?"
    print("\nScreenshot 2: Ti chiami DEFGHJK, giusto?")
    extract_and_save(
        base_path / "Screenshot 2026-02-21 alle 10.33.37.png",
        [
            ('D', 49, 55),
            ('E', 55, 60),
            ('F', 60, 65),
            ('G', 65, 72),
            ('H', 72, 78),
            ('J', 78, 83),
            ('K', 83, 90),
        ],
        output_dir
    )

    # Screenshot 3: "Ti chiami LMOQTUV, giusto?"
    print("\nScreenshot 3: Ti chiami LMOQTUV, giusto?")
    extract_and_save(
        base_path / "Screenshot 2026-02-21 alle 10.34.23.png",
        [
            ('L', 49, 54),
            ('M', 54, 62),
            ('O', 62, 69),
            ('Q', 69, 76),
            # T already extracted
            ('U', 83, 89),
            ('V', 89, 95),
        ],
        output_dir
    )

    # Screenshot 4: "Ti chiami WXYZ012, giusto?"
    print("\nScreenshot 4: Ti chiami WXYZ012, giusto?")
    extract_and_save(
        base_path / "Screenshot 2026-02-21 alle 10.34.56.png",
        [
            ('W', 49, 58),
            ('X', 58, 64),
            ('Y', 64, 70),
            ('Z', 70, 76),
            ('0', 76, 81),
            ('1', 81, 85),
            ('2', 85, 90),
        ],
        output_dir
    )

    # Screenshot 5: "Ti chiami 3456789, giusto?"
    print("\nScreenshot 5: Ti chiami 3456789, giusto?")
    extract_and_save(
        base_path / "Screenshot 2026-02-21 alle 10.35.19.png",
        [
            ('3', 49, 54),
            ('4', 54, 59),
            ('5', 59, 64),
            ('6', 64, 69),
            ('7', 69, 74),
            ('8', 74, 79),
            ('9', 79, 84),
        ],
        output_dir
    )

    # Count results
    templates = list(output_dir.glob("*.png"))
    print(f"\n=== Extracted {len(templates)} templates ===")

    # Verify templates by checking their content
    print("\nVerifying templates...")
    for t in sorted(templates):
        img = cv2.imread(str(t), cv2.IMREAD_GRAYSCALE)
        var = np.var(img)
        has_dark = img.min() < 100
        print(f"  {t.name}: {img.shape}, var={var:.0f}, has_dark={has_dark}")


if __name__ == "__main__":
    main()
