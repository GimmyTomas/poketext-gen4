"""Complete character extraction with precise manual boundaries.

Based on visual analysis of scaled screenshots.
Text region: y=155-169 (14 pixels), x starts at 14.
"""

import cv2
import numpy as np
from pathlib import Path
import shutil

TEXT_Y = 155
TEXT_X = 14
CHAR_HEIGHT = 14


def char_to_filename(char: str) -> str:
    """Convert character to safe filename."""
    special = {
        ' ': 'space', '.': 'period', ',': 'comma', '!': 'exclaim',
        '?': 'question', "'": 'apostrophe', '"': 'quote',
        ':': 'colon', ';': 'semicolon', '-': 'hyphen',
        '/': 'slash', '(': 'lparen', ')': 'rparen',
        'è': 'e_grave', 'à': 'a_grave', 'é': 'e_acute',
        'ì': 'i_grave', 'ò': 'o_grave', 'ù': 'u_grave',
        '+': 'plus', '=': 'equals', '*': 'asterisk',
        '@': 'at', '#': 'hash', '…': 'ellipsis',
    }
    if char in special:
        return special[char]
    if char.isupper() and char.isascii():
        return f'upper_{char}'
    return char


def extract_chars(img_path, specs, output_dir):
    """Extract characters from image.

    specs: list of (char, x_start, x_end) relative to TEXT_X
    """
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"  Error: Could not load {img_path}")
        return []

    line = img[TEXT_Y:TEXT_Y + CHAR_HEIGHT, TEXT_X:]
    extracted = []

    for char, x_start, x_end in specs:
        char_img = line[:, x_start:x_end]
        filename = char_to_filename(char) + '.png'
        filepath = output_dir / filename

        if not filepath.exists():
            cv2.imwrite(str(filepath), char_img)
            extracted.append(char)
            print(f"  '{char}' x={x_start}-{x_end} (w={x_end-x_start}) -> {filename}")

    return extracted


def main():
    output_dir = Path("templates/western")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base = Path("game-data/letters")

    # === 2026 Screenshots: Named characters ===

    # Screenshot 1: "Ti chiami bjkxyAB, giusto?"
    # Word positions: T=2, i=7, chiami=15-44, bjkxyAB=49-90, comma=90, giusto=99-131, ?=131
    print("\nScreenshot 1: Ti chiami bjkxyAB, giusto?")
    extract_chars(base / "Screenshot 2026-02-21 alle 10.32.59.png", [
        ('T', 2, 7),      # T
        ('i', 7, 10),     # i
        ('c', 15, 20),    # c
        ('h', 20, 26),    # h (6 wide)
        ('i', 26, 29),    # i (duplicate, skip)
        ('a', 29, 35),    # a (6 wide)
        ('m', 35, 44),    # m (9 wide)
        ('i', 44, 47),    # i (duplicate)
        ('b', 49, 54),    # b
        ('j', 54, 59),    # j (includes descender)
        ('k', 59, 65),    # k (6 wide)
        ('x', 65, 71),    # x (6 wide)
        ('y', 71, 77),    # y (6 wide)
        ('A', 77, 83),    # A (6 wide)
        ('B', 83, 90),    # B (7 wide)
        (',', 90, 93),    # comma
        ('g', 99, 104),   # g
        ('u', 107, 113),  # u (6 wide)
        ('s', 113, 119),  # s (6 wide)
        ('t', 119, 124),  # t (5 wide)
        ('o', 124, 130),  # o (6 wide)
        ('?', 130, 137),  # ?
    ], output_dir)

    # Screenshot 2: "Ti chiami DEFGHJK, giusto?"
    print("\nScreenshot 2: Ti chiami DEFGHJK, giusto?")
    extract_chars(base / "Screenshot 2026-02-21 alle 10.33.37.png", [
        ('D', 49, 56),    # D (7 wide)
        ('E', 56, 61),    # E (5 wide)
        ('F', 61, 66),    # F (5 wide)
        ('G', 66, 73),    # G (7 wide)
        ('H', 73, 79),    # H (6 wide)
        ('J', 79, 84),    # J (5 wide)
        ('K', 84, 91),    # K (7 wide)
    ], output_dir)

    # Screenshot 3: "Ti chiami LMOQTUV, giusto?"
    print("\nScreenshot 3: Ti chiami LMOQTUV, giusto?")
    extract_chars(base / "Screenshot 2026-02-21 alle 10.34.23.png", [
        ('L', 49, 54),    # L (5 wide)
        ('M', 54, 62),    # M (8 wide)
        ('O', 62, 69),    # O (7 wide)
        ('Q', 69, 76),    # Q (7 wide)
        # T already extracted
        ('U', 83, 89),    # U (6 wide)
        ('V', 89, 95),    # V (6 wide)
    ], output_dir)

    # Screenshot 4: "Ti chiami WXYZ012, giusto?"
    print("\nScreenshot 4: Ti chiami WXYZ012, giusto?")
    extract_chars(base / "Screenshot 2026-02-21 alle 10.34.56.png", [
        ('W', 49, 58),    # W (9 wide)
        ('X', 58, 64),    # X (6 wide)
        ('Y', 64, 70),    # Y (6 wide)
        ('Z', 70, 76),    # Z (6 wide)
        ('0', 76, 81),    # 0 (5 wide)
        ('1', 81, 85),    # 1 (4 wide)
        ('2', 85, 91),    # 2 (6 wide)
    ], output_dir)

    # Screenshot 5: "Ti chiami 3456789, giusto?"
    print("\nScreenshot 5: Ti chiami 3456789, giusto?")
    extract_chars(base / "Screenshot 2026-02-21 alle 10.35.19.png", [
        ('3', 49, 54),    # 3 (5 wide)
        ('4', 54, 59),    # 4 (5 wide)
        ('5', 59, 64),    # 5 (5 wide)
        ('6', 64, 69),    # 6 (5 wide)
        ('7', 69, 74),    # 7 (5 wide)
        ('8', 74, 79),    # 8 (5 wide)
        ('9', 79, 84),    # 9 (5 wide)
    ], output_dir)

    # Screenshot 6: "Ti chiami AEIOU-, giusto?" (accented uppercase vowels and hyphen)
    print("\nScreenshot 6: Ti chiami AEIOU-, giusto?")
    extract_chars(base / "Screenshot 2026-02-21 alle 10.36.37.png", [
        # A, E already have, extract I
        ('I', 61, 65),    # I (4 wide)
        # Skip O, U - already have
        ('-', 79, 84),    # hyphen (5 wide)
    ], output_dir)

    # Screenshot 7: "Ti chiami àèéìòù, giusto?" (accented lowercase)
    print("\nScreenshot 7: Ti chiami àèéìòù, giusto?")
    extract_chars(base / "Screenshot 2026-02-21 alle 10.37.41.png", [
        ('à', 49, 55),    # à (6 wide)
        ('è', 55, 61),    # è (6 wide)
        ('é', 61, 67),    # é (6 wide)
        ('ì', 67, 70),    # ì (3 wide)
        ('ò', 70, 76),    # ò (6 wide)
        ('ù', 76, 82),    # ù (6 wide)
    ], output_dir)

    # === 2024 Screenshots: Missing lowercase and special chars ===

    # Screenshot: "C è venuto a cercarti poco"
    # Word boundaries: C=2-7, è=12-17, venuto=22-50, a=52-57, cercarti=62-115, poco=121-144
    print("\nScreenshot 2024-1: C è venuto a cercarti poco")
    extract_chars(base / "Screenshot 2024-01-21 alle 13.50.51.png", [
        ('C', 2, 8),      # C (6 wide)
        # è already extracted from 2026
        ('v', 22, 27),    # v in "venuto"
        ('e', 27, 32),    # e in "venuto"
        ('n', 32, 38),    # n in "venuto" (6 wide)
        # u, t, o already have
        # a already have
        # c already have
        ('r', 67, 72),    # r in "cercarti"
        # c, a already have
        # r duplicate
        # t, i already have
        ('p', 121, 126),  # p in "poco"
        # o, c, o already have
    ], output_dir)

    # Screenshot: "diceva che dovresti prendere un"
    print("\nScreenshot 2024-2: diceva che dovresti prendere un")
    extract_chars(base / "Screenshot 2024-01-21 alle 13.51.01.png", [
        ('d', 2, 8),      # d in "diceva"
        # i, c, e, v, a already have
        # che: c, h, e already have
        # dovresti: d duplicate, o, v, r, e, s, t, i already have
        # prendere: p, r, e, n, d, e, r, e - have most
        # un: u, n already have
    ], output_dir)

    # Screenshot: "Come stanno andando le cose, tesoro?"
    print("\nScreenshot 2024-3: Come stanno andando le cose, tesoro?")
    extract_chars(base / "Screenshot 2024-01-21 alle 13.51.11.png", [
        # C, o, m, e - have
        # s, t, a, n, n, o - have most
        # a, n, d, a, n, d, o - have
        ('l', 116, 119),  # l in "le" (3 wide)
        # e - have
        # c, o, s, e - have
        # comma - have
        # t, e, s, o, r, o - have
        # ? - have
    ], output_dir)

    # Screenshot: "Il progetto con il Prof. Rowan fa"
    print("\nScreenshot 2024-4: Il progetto con il Prof. Rowan fa")
    extract_chars(base / "Screenshot 2024-01-21 alle 13.51.14.png", [
        # I already extracted from 2026
        # l already extracted
        # p, r, o, g, e, t, t, o - have most
        # c, o, n - have
        # i, l - have
        ('P', 101, 106),  # P in "Prof."
        # r, o - have
        ('f', 111, 115),  # f in "Prof."
        ('.', 115, 118),  # period (3 wide)
        ('R', 122, 128),  # R in "Rowan"
        # o - have
        ('w', 133, 140),  # w in "Rowan" (7 wide)
        # a, n - have
        # f duplicate, a - have
    ], output_dir)

    # === Second line extractions for any missing chars ===
    # Check second lines if needed (y offset = 16)

    # Count results
    templates = list(output_dir.glob("*.png"))
    print(f"\n=== Extracted {len(templates)} templates ===")

    # Verify templates
    print("\nVerifying templates...")
    for t in sorted(templates):
        img = cv2.imread(str(t), cv2.IMREAD_GRAYSCALE)
        var = np.var(img)
        has_dark = img.min() < 100
        status = "OK" if var > 100 and has_dark else "CHECK"
        if status != "OK":
            print(f"  {t.name}: var={var:.0f}, min={img.min()} - {status}")


if __name__ == "__main__":
    main()
