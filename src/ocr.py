"""Custom OCR for Pokemon Gen 4 text using template matching."""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List


@dataclass
class CharacterTemplate:
    """A template for a single character."""
    char: str
    template: np.ndarray
    width: int
    height: int
    variance: float  # Precomputed variance for fast filtering


class CharacterWidths:
    """Character width definitions for the Pokemon Gen 4 font.

    Measured from actual game screenshots at native DS resolution.
    Each width includes the character plus its natural spacing.
    """

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
        '&': 6, '#': 6, '%': 6, '+': 5, '*': 5,
        '=': 5, '@': 7,

        # Accented (Italian/Western)
        'à': 5, 'è': 5, 'é': 5, 'ì': 3, 'ò': 6, 'ù': 5,
        'À': 6, 'È': 5, 'É': 5, 'Ì': 4, 'Ò': 6, 'Ù': 6,

        # Special characters
        '♀': 6, '♂': 6, '×': 5, '…': 7, '·': 3, '«': 6,
        '■': 8,  # Pocket icons
    }

    DEFAULT_WIDTH = 5

    @classmethod
    def get_width(cls, char: str) -> int:
        return cls.WIDTHS.get(char, cls.DEFAULT_WIDTH)


class PokemonOCR:
    """
    Custom OCR using template matching.

    Pokemon Gen 4 uses a variable-width font, making template matching
    with width tables highly effective and more accurate than general-purpose OCR.
    """

    # Character height in DS native resolution
    CHAR_HEIGHT = 15

    # Big text (2x vertically stretched) height
    BIG_CHAR_HEIGHT = 30

    # Stretch factor for big text (empirically determined from "Pum!!!")
    BIG_TEXT_STRETCH = 2.0

    # Lower threshold for big text (stretched templates are fuzzier)
    BIG_TEXT_THRESHOLD = 0.50

    # Minimum match threshold for template matching
    # Higher threshold reduces false positives
    MATCH_THRESHOLD = 0.90

    # Space detection threshold (mean pixel brightness)
    # Set to 245 - only pure whitespace should be detected as space
    SPACE_THRESHOLD = 245

    def __init__(self, templates_dir: Optional[Path] = None, language: str = "en"):
        """
        Initialize the OCR with character templates.

        Args:
            templates_dir: Directory containing character template images
            language: Language code (en, it, fr, de, es, ja)
        """
        self.language = language
        self.templates: Dict[str, CharacterTemplate] = {}

        if templates_dir is None:
            # Default to western templates
            templates_dir = Path(__file__).parent.parent / "templates" / "western"

        if templates_dir.exists():
            self._load_templates(templates_dir)
            self._sort_templates_by_frequency()

    def _load_templates(self, templates_dir: Path):
        """Load character templates from a directory."""
        for template_path in templates_dir.glob("*.png"):
            char = self._filename_to_char(template_path.stem)
            template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)

            if template is not None:
                # Precompute variance for fast filtering during matching
                variance = float(np.var(template))
                self.templates[char] = CharacterTemplate(
                    char=char,
                    template=template,
                    width=template.shape[1],
                    height=template.shape[0],
                    variance=variance
                )

    def _sort_templates_by_frequency(self):
        """Sort templates so common characters are checked first (for early exit)."""
        # Character frequency in English/Italian text (approximate)
        frequency = {
            'e': 100, 'a': 95, 'i': 90, 'o': 85, 'n': 80, 't': 75, 'r': 70,
            's': 65, 'l': 60, 'c': 55, 'u': 50, 'd': 45, 'p': 40, 'm': 35,
            ' ': 100,  # Space is very common
            '.': 30, ',': 25, 'h': 30, 'g': 25, 'b': 20, 'f': 15, 'v': 15,
            'è': 20, 'é': 15, 'à': 15, 'ò': 10, 'ù': 10, 'ì': 10,  # Italian accents
        }
        # Sort by frequency (highest first), unknown chars get 0
        sorted_items = sorted(
            self.templates.items(),
            key=lambda x: frequency.get(x[0].lower(), 0),
            reverse=True
        )
        # Rebuild dict in sorted order (Python 3.7+ maintains insertion order)
        self.templates = dict(sorted_items)

    def _filename_to_char(self, filename: str) -> str:
        """Convert a filename to its character."""
        # Punctuation and special names
        special_chars = {
            "space": " ",
            "period": ".",
            "comma": ",",
            "exclaim": "!",
            "question": "?",
            "apostrophe": "'",  # Normal apostrophe (right single quote)
            "apostrophe_open": "\u2018",  # Left single quote '
            "quote": '"',
            "quote_close": "\u201d",  # Right double quote "
            "colon": ":",
            "semicolon": ";",
            "hyphen": "-",
            "slash": "/",
            "lparen": "(",
            "rparen": ")",
            "plus": "+",
            "equals": "=",
            "asterisk": "*",
            "percent": "%",
            "hash": "#",
            "at": "@",
            "tilde": "~",
            "tilde_inverted": "~",  # Same character, different rendering
            "ellipsis": "…",
            "middot": "·",
            "pokedollar": "₽",
            # Accented characters (lowercase)
            "a_grave": "à",
            "e_grave": "è",
            "e_acute": "é",
            "i_grave": "ì",
            "o_grave": "ò",
            "u_grave": "ù",
            # Accented characters (uppercase)
            "upper_A_grave": "À",
            "upper_E_grave": "È",
            "upper_E_acute": "É",
            "upper_I_grave": "Ì",
            "upper_O_grave": "Ò",
            "upper_U_grave": "Ù",
            # Symbols
            "female": "♀",
            "male": "♂",
            "musical_note": "♪",
            "sun": "☀",
            "cloud": "☁",
            "umbrella": "☂",
            "snowman": "☃",
            "arrow_up": "↑",
            "arrow_down": "↓",
            # Shapes
            "triangle": "△",
            "circle_dot": "◉",
            "square": "□",
            "rhombus": "◇",
            "heart": "♥",
            "diamond": "♦",
            "spade": "♠",
            "clover": "♣",
            "star": "★",
            # Faces
            "smiley": "☺",
            "grinning_face": "😀",
            "astonished_face": "😮",
            "angry_face": "😠",
            "sleeping_zz": "💤",
            # Italian quote variants
            "quote_open_low": '"',  # Low opening quote (Italian style) - output as standard "
            # Pocket/bag icons (output as black square)
            "pocket_medicine": "■",
            "pocket_keyitems": "■",
        }

        if filename in special_chars:
            return special_chars[filename]

        # Handle uppercase: "upper_A" -> "A"
        if filename.startswith("upper_"):
            return filename[6:]

        # Direct character (single letter, number, or unicode)
        return filename

    def recognize_line(self, line_image: np.ndarray, try_stretched: bool = False) -> str:
        """
        Recognize text from a line image using sliding window template matching.

        Args:
            line_image: Image of a single line of text (grayscale or BGR)
            try_stretched: If True, also try vertically stretched templates

        Returns:
            Recognized text string
        """
        if len(line_image.shape) == 3:
            # Preprocess: darken blue pixels before grayscale conversion
            # This helps detect blue icons (pocket symbols) that would otherwise
            # become white/invisible in grayscale
            processed = self._darken_blue_pixels(line_image)
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        else:
            gray = line_image.copy()

        if not self.templates:
            return ""

        # Ensure line height matches template height
        if gray.shape[0] != self.CHAR_HEIGHT:
            gray = gray[:self.CHAR_HEIGHT, :]

        # Find all character matches across the line
        matches = self._find_all_matches(gray, try_stretched=try_stretched)

        # If no matches and not already trying stretched, retry with stretched templates
        if not matches and not try_stretched:
            # Check if there are dark pixels (potential text) that we missed
            if gray.min() < 120:
                matches = self._find_all_matches(gray, try_stretched=True)

        if not matches:
            return ""

        # Build result string from matches, inserting spaces where gaps exist
        result = []
        prev_end = 0

        for char, x, width, score in matches:
            # Check for space gap (more than 2 pixels between characters)
            gap = x - prev_end
            if gap > 3 and result:  # Likely a space
                result.append(' ')

            result.append(char)
            prev_end = x + width

        return "".join(result).strip()

    def recognize_big_text(self, line_image: np.ndarray) -> str:
        """
        Recognize big text (2x vertically stretched) from a line image.

        Big text like "Pum!!!" or "Thud!!!" uses the same font but stretched
        2x vertically. We stretch the templates to match.

        Args:
            line_image: Image of a single line of text (should be ~24 pixels tall for big text)

        Returns:
            Recognized text string
        """
        if len(line_image.shape) == 3:
            processed = self._darken_blue_pixels(line_image)
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        else:
            gray = line_image.copy()

        if not self.templates:
            return ""

        # Big text is ~24 pixels tall (2x normal)
        target_height = min(gray.shape[0], self.BIG_CHAR_HEIGHT)

        # Find all character matches using stretched templates
        matches = self._find_all_matches_big(gray, target_height)

        if not matches:
            return ""

        # Build result string from matches
        result = []
        prev_end = 0

        for char, x, width, score in matches:
            gap = x - prev_end
            if gap > 4 and result:  # Gap threshold for big text
                result.append(' ')
            result.append(char)
            prev_end = x + width

        return "".join(result).strip()

    def _find_all_matches_big(self, gray: np.ndarray, target_height: int) -> List[Tuple[str, int, int, float]]:
        """
        Find all character matches for big text using stretched templates.

        Args:
            gray: Grayscale line image
            target_height: Height of the text region

        Returns:
            List of (character, x_position, width, score) tuples
        """
        matches = []
        x = 0
        line_width = gray.shape[1]
        DARK_THRESHOLD = 130

        while x < line_width - 2:
            check_width = min(4, line_width - x)
            region = gray[:, x:x + check_width]

            if np.mean(region) > self.SPACE_THRESHOLD:
                x += 1
                continue

            col = gray[:, x]
            if col.min() > DARK_THRESHOLD:
                x += 1
                continue

            # Find best match using stretched templates
            best_match = self._find_best_match_big(gray, x, target_height)

            if best_match:
                char, score, width = best_match
                matches.append((char, x, width, score))
                x += width
            else:
                x += 1

        return matches

    def _find_best_match_big(self, gray: np.ndarray, x: int, target_height: int) -> Optional[Tuple[str, float, int]]:
        """
        Find the best matching stretched template at position x.

        Tries multiple stretch factors around 2x to find the best match.
        Prefers wider templates when scores are similar (within 0.1).

        Args:
            gray: Grayscale line image
            x: X position to match at
            target_height: Height of the text region

        Returns:
            Tuple of (character, score, width) or None if no match
        """
        best_score = 0
        best_char = None
        best_width = 0
        line_width = gray.shape[1]

        # Try multiple stretch factors around 2x
        stretch_factors = [1.8, 2.0, 2.2]

        for stretch in stretch_factors:
            for char, template in self.templates.items():
                # Skip low-variance templates
                if template.variance < 500:
                    continue

                # Stretch template vertically
                stretched_height = int(template.height * stretch)
                if stretched_height > target_height or stretched_height < 10:
                    continue

                stretched = cv2.resize(template.template, (template.width, stretched_height),
                                       interpolation=cv2.INTER_LINEAR)

                # Need enough width for template
                if x + template.width > line_width:
                    continue

                # Extract region to match
                region = gray[:stretched_height, x:x + template.width]

                if region.shape[0] != stretched_height or region.shape[1] != template.width:
                    continue

                # Template matching
                result = cv2.matchTemplate(region, stretched, cv2.TM_CCOEFF_NORMED)

                if result.size > 0:
                    score = result[0, 0]

                    # Prefer wider templates when scores are close
                    # This prevents narrow chars (!, i) from matching partial patterns
                    if score > best_score + 0.1:
                        # Clear winner
                        best_score = score
                        best_char = char
                        best_width = template.width
                    elif score > best_score - 0.1 and template.width > best_width:
                        # Similar score but wider template - prefer it
                        best_score = score
                        best_char = char
                        best_width = template.width

        if best_char is not None and best_score >= self.BIG_TEXT_THRESHOLD:
            return (best_char, best_score, best_width)
        return None

    def _find_all_matches(self, gray: np.ndarray, try_stretched: bool = False) -> List[Tuple[str, int, int, float]]:
        """
        Find all character matches in a line using greedy best-match approach.

        Args:
            gray: Grayscale line image
            try_stretched: If True, also try vertically stretched templates

        Returns:
            List of (character, x_position, width, score) tuples
        """
        matches = []
        x = 0
        line_width = gray.shape[1]

        # Dark pixel threshold - characters have pixels around 81
        # Set to 130 to catch columns that are slightly above 120 (e.g., 122)
        # This helps with '1' vs 'l' confusion where the leading edge matters
        DARK_THRESHOLD = 130

        while x < line_width - 2:
            # Check if region is mostly white (space or end of text)
            check_width = min(4, line_width - x)
            region = gray[:, x:x + check_width]

            if np.mean(region) > self.SPACE_THRESHOLD:
                x += 1
                continue

            # Only start matching at columns that have dark pixels (actual character content)
            # This prevents narrow templates like 'l' from matching at shadow/gap columns
            col = gray[:, x]
            if col.min() > DARK_THRESHOLD:
                # No dark pixels in this column - skip to next
                x += 1
                continue

            # Find best match at current position
            best_match = self._find_best_match(gray, x, try_stretched=try_stretched)

            if best_match:
                char, score, template = best_match
                matches.append((char, x, template.width, score))
                x += template.width
            else:
                # No match at this position - move to next pixel
                x += 1

        return matches

    def _find_text_start(self, gray: np.ndarray) -> int:
        """Find where text actually starts in the line image."""
        # Look for the first column that has dark pixels (text)
        for x in range(min(10, gray.shape[1])):
            col = gray[:, x]
            if col.min() < 180:  # Found dark pixel (actual character, not just noise)
                # Templates have ~2 columns of leading whitespace, so we need to
                # start matching 2 pixels before the first dark column
                return max(0, x - 2)
        return 0  # Default to start if no text found

    def _darken_blue_pixels(self, image: np.ndarray) -> np.ndarray:
        """
        Darken blue pixels so they're visible after grayscale conversion.

        Pokemon Gen 4 uses blue icons for pocket/bag categories. These icons
        become nearly white when converted to grayscale because blue has high
        luminance. This method detects blue pixels and darkens them.

        Args:
            image: BGR image

        Returns:
            Modified BGR image with blue pixels darkened
        """
        result = image.copy()

        # Split into BGR channels and convert to int16 to avoid overflow
        b = result[:, :, 0].astype(np.int16)
        g = result[:, :, 1].astype(np.int16)
        r = result[:, :, 2].astype(np.int16)

        # Detect blue pixels: B channel is high (>150), and significantly higher than R and G
        # This matches the blue pocket icons while avoiding other colors
        blue_mask = (b > 150) & (b > r + 40) & (b > g + 40)

        # Darken blue pixels by setting them to dark gray
        result[blue_mask] = [80, 80, 80]

        return result

    def _find_best_match(self, gray: np.ndarray, x: int, try_stretched: bool = False) -> Optional[Tuple[str, float, CharacterTemplate]]:
        """
        Find the best matching template at position x.

        Args:
            gray: Grayscale line image
            x: X position to match at
            try_stretched: If True, also try vertically stretched templates

        Returns:
            Tuple of (character, score, template) or None if no match
        """
        best_score = 0
        best_char = None
        best_template = None
        line_width = gray.shape[1]
        line_height = min(gray.shape[0], self.CHAR_HEIGHT)

        # Try stretch factors: 1.0 (normal), and if try_stretched, also 1.2, 1.5
        stretch_factors = [1.0]
        if try_stretched:
            stretch_factors = [1.0, 1.2, 1.5]

        for stretch in stretch_factors:
            for char, template in self.templates.items():
                # Skip low-variance templates (mostly white/uniform)
                if template.variance < 500:
                    continue

                # Need enough width for template
                if x + template.width > line_width:
                    continue

                # Get template, potentially stretched
                if stretch == 1.0:
                    t = template.template
                    t_height = template.height
                else:
                    # Stretch template vertically
                    new_height = int(template.height * stretch)
                    if new_height > line_height:
                        continue
                    t = cv2.resize(template.template, (template.width, new_height),
                                   interpolation=cv2.INTER_LINEAR)
                    t_height = new_height

                # Extract region to match
                region = gray[:t_height, x:x + template.width]

                if region.shape[0] != t_height or region.shape[1] != template.width:
                    continue

                # Simple template matching
                result = cv2.matchTemplate(region, t, cv2.TM_CCOEFF_NORMED)

                if result.size > 0:
                    score = result[0, 0]  # Single point result for same-size images

                    if score >= self.MATCH_THRESHOLD:
                        # Early exit for very high scores, but only if template is wide enough
                        # This prevents narrow templates (like ') from matching part of a
                        # wider character (like „) and triggering early exit
                        if score > 0.99 and template.width >= 5:
                            return (char, score, template)

                        if best_char is None:
                            best_score = score
                            best_char = char
                            best_template = template
                        elif score > best_score + 0.001:
                            # Better score - use this one
                            best_score = score
                            best_char = char
                            best_template = template
                        elif abs(score - best_score) <= 0.001:
                            # Nearly identical score - use tiebreakers
                            # Prefer alphanumeric over symbols (e.g., 'O' over '○')
                            char_is_alnum = char.isalnum()
                            best_is_alnum = best_char.isalnum()
                            if char_is_alnum and not best_is_alnum:
                                best_score = score
                                best_char = char
                                best_template = template
                            elif template.width > best_template.width:
                                # Prefer wider template
                                best_score = score
                                best_char = char
                                best_template = template

        if best_char is not None and best_score >= self.MATCH_THRESHOLD:
            return (best_char, best_score, best_template)
        return None

    def recognize_line_with_confidence(self, line_image: np.ndarray) -> List[Tuple[str, float]]:
        """
        Recognize text from a line image, returning confidence scores.

        Args:
            line_image: Image of a single line of text (grayscale or BGR)

        Returns:
            List of (character, confidence) tuples
        """
        if len(line_image.shape) == 3:
            processed = self._darken_blue_pixels(line_image)
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        else:
            gray = line_image.copy()

        if not self.templates:
            return []

        if gray.shape[0] != self.CHAR_HEIGHT:
            gray = gray[:self.CHAR_HEIGHT, :]

        result = []
        x = 0
        line_width = gray.shape[1]
        space_width = CharacterWidths.get_width(' ')

        while x < line_width - 2:
            check_width = min(space_width, line_width - x)
            space_region = gray[:, x:x + check_width]

            if np.mean(space_region) > self.SPACE_THRESHOLD:
                if not result or result[-1][0] != ' ':
                    result.append((' ', 1.0))
                x += space_width
                continue

            best_match = self._find_best_match(gray, x)

            if best_match:
                char, score, template = best_match
                result.append((char, score))
                x += template.width
            else:
                x += 1

        return result

    def recognize_textbox(self, text_region: np.ndarray) -> Tuple[str, str]:
        """
        Recognize text from a textbox region (two lines).

        Args:
            text_region: Image of the textbox text area (should be ~33 pixels tall)

        Returns:
            Tuple of (line1, line2)
        """
        # Line positions: line1 starts at y=0, line2 starts at y=16
        # Each line is CHAR_HEIGHT (14) pixels tall
        line1_img = text_region[0:self.CHAR_HEIGHT, :]
        line2_img = text_region[16:16 + self.CHAR_HEIGHT, :]

        return self.recognize_line(line1_img), self.recognize_line(line2_img)

    def recognize_textbox_with_confidence(self, text_region: np.ndarray) -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
        """
        Recognize text from a textbox region, returning confidence scores.

        Args:
            text_region: Image of the textbox text area

        Returns:
            Tuple of (line1_chars, line2_chars) where each is a list of (char, confidence)
        """
        line1_img = text_region[0:self.CHAR_HEIGHT, :]
        line2_img = text_region[16:16 + self.CHAR_HEIGHT, :]

        return (
            self.recognize_line_with_confidence(line1_img),
            self.recognize_line_with_confidence(line2_img)
        )

    def count_characters(self, text: str) -> int:
        """
        Count the number of displayable characters (for speedrun timing).

        Spaces are counted as they still take time to display.

        Args:
            text: The recognized text

        Returns:
            Character count
        """
        return len(text)

    def get_stats(self) -> dict:
        """Return statistics about loaded templates."""
        return {
            "templates_loaded": len(self.templates),
            "characters": sorted(self.templates.keys()),
        }


def create_ocr(language: str = "en") -> PokemonOCR:
    """
    Create and initialize a PokemonOCR instance.

    Args:
        language: Language code (en, it, fr, de, es)

    Returns:
        Initialized PokemonOCR instance
    """
    templates_dir = Path(__file__).parent.parent / "templates" / "western"
    return PokemonOCR(templates_dir=templates_dir, language=language)


if __name__ == "__main__":
    # Test the OCR
    import sys

    ocr = create_ocr()
    stats = ocr.get_stats()
    print(f"Loaded {stats['templates_loaded']} templates")
    print(f"Characters: {', '.join(stats['characters'][:20])}...")

    # Test with a screenshot if provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"\nTesting on: {image_path}")

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            # Assume this is a single line image
            text = ocr.recognize_line(img)
            print(f"Recognized: '{text}'")
        else:
            print(f"Error: Could not load {image_path}")
