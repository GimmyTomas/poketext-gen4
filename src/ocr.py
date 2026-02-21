"""Custom OCR for Pokemon Gen 4 text using template matching."""

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CharacterTemplate:
    """A template for a single character."""
    char: str
    template: np.ndarray
    width: int
    height: int


class PokemonOCR:
    """
    Custom OCR using template matching.

    Pokemon Gen 4 uses a fixed-width font, making template matching
    highly effective and more accurate than general-purpose OCR.
    """

    # Character dimensions in DS native resolution
    CHAR_WIDTH = 8   # Most characters
    CHAR_HEIGHT = 16

    # Special character widths (some are narrower)
    NARROW_CHARS = set("il1!.,':;")  # These might be narrower

    def __init__(self, templates_dir: Path | None = None, language: str = "en"):
        """
        Initialize the OCR with character templates.

        Args:
            templates_dir: Directory containing character template images
            language: Language code (en, it, fr, de, es, ja)
        """
        self.language = language
        self.templates: dict[str, CharacterTemplate] = {}

        if templates_dir and templates_dir.exists():
            self._load_templates(templates_dir)

    def _load_templates(self, templates_dir: Path):
        """Load character templates from a directory."""
        # Templates are named by character: a.png, b.png, etc.
        # Special characters use descriptive names: space.png, period.png, etc.

        for template_path in templates_dir.glob("*.png"):
            char = self._filename_to_char(template_path.stem)
            template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)

            if template is not None:
                self.templates[char] = CharacterTemplate(
                    char=char,
                    template=template,
                    width=template.shape[1],
                    height=template.shape[0]
                )

    def _filename_to_char(self, filename: str) -> str:
        """Convert a filename to its character."""
        special_chars = {
            "space": " ",
            "period": ".",
            "comma": ",",
            "exclaim": "!",
            "question": "?",
            "apostrophe": "'",
            "quote": '"',
            "colon": ":",
            "semicolon": ";",
            "hyphen": "-",
            "slash": "/",
            "lparen": "(",
            "rparen": ")",
            "ellipsis": "...",
        }

        return special_chars.get(filename, filename)

    def recognize_line(self, line_image: np.ndarray) -> str:
        """
        Recognize text from a line image.

        Args:
            line_image: Image of a single line of text (grayscale or BGR)

        Returns:
            Recognized text string
        """
        if len(line_image.shape) == 3:
            gray = cv2.cvtColor(line_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = line_image

        if not self.templates:
            # No templates loaded, return empty
            return ""

        result = []
        x = 0

        while x < gray.shape[1] - self.CHAR_WIDTH:
            # Extract a character-sized region
            char_region = gray[:, x:x + self.CHAR_WIDTH]

            # Check if this region is mostly white (space)
            if np.mean(char_region) > 240:
                result.append(" ")
                x += self.CHAR_WIDTH
                continue

            # Try to match against all templates
            best_match = None
            best_score = 0
            best_char = "?"

            for char, template in self.templates.items():
                if x + template.width > gray.shape[1]:
                    continue

                region = gray[:template.height, x:x + template.width]

                if region.shape != template.template.shape:
                    continue

                # Template matching
                result_match = cv2.matchTemplate(
                    region, template.template, cv2.TM_CCOEFF_NORMED
                )
                score = result_match[0, 0]

                if score > best_score:
                    best_score = score
                    best_char = char
                    best_match = template

            if best_match and best_score > 0.7:
                result.append(best_char)
                x += best_match.width
            else:
                x += self.CHAR_WIDTH

        return "".join(result)

    def recognize_textbox(self, text_region: np.ndarray) -> tuple[str, str]:
        """
        Recognize text from a textbox region (two lines).

        Args:
            text_region: Image of the textbox text area

        Returns:
            Tuple of (line1, line2)
        """
        # Split into two lines
        mid_y = text_region.shape[0] // 2

        line1_img = text_region[:mid_y, :]
        line2_img = text_region[mid_y:, :]

        return self.recognize_line(line1_img), self.recognize_line(line2_img)


def extract_character_templates(reference_image: np.ndarray,
                                 known_text: str,
                                 output_dir: Path):
    """
    Extract character templates from a reference image with known text.

    This is a helper function to build the template library from
    game screenshots with known text content.

    Args:
        reference_image: Screenshot of textbox with known text
        known_text: The actual text shown in the image
        output_dir: Directory to save extracted templates
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # This would need manual calibration for exact character positions
    # For now, this is a placeholder for the template extraction process
    pass
