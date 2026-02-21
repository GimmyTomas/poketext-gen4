"""
Poketext Gen4 - Extract text from Pokemon Gen 4 speedrun videos.

Usage:
    python -m src.main <video_path> [options]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple, List

from .video import VideoReader
from .screen import detect_screen_layout, extract_top_screen, normalize_to_ds_resolution
from .textbox import TextboxDetector, TextboxState
from .ocr import PokemonOCR


def process_video(video_path: Path,
                  output_path: Optional[Path] = None,
                  game: str = "diamond_pearl",
                  language: str = "en",
                  verbose: bool = False) -> Tuple[str, int]:
    """
    Process a video and extract text.

    Args:
        video_path: Path to the video file
        output_path: Path to write output (None for stdout)
        game: Game identifier (diamond_pearl, platinum, hgss)
        language: Language code (en, it, fr, de, es, ja)
        verbose: Print progress information

    Returns:
        Tuple of (extracted_text, character_count)
    """
    with VideoReader(video_path) as video:
        if verbose:
            print(f"Processing: {video}", file=sys.stderr)

        # Detect screen layout from first frame
        _, first_frame = next(video.frames())
        video.cap.set(0, 0)  # Reset to beginning

        layout = detect_screen_layout(first_frame)
        if verbose:
            print(f"Detected layout: {layout.top_screen_pos.name}, "
                  f"scale={layout.scale_factor:.2f}",
                  file=sys.stderr)

        # Initialize detectors
        textbox_detector = TextboxDetector(game)
        ocr = PokemonOCR(language=language)

        # State tracking
        extracted_lines: List[str] = []
        prev_text_region = None
        prev_state = TextboxState.CLOSED
        current_text = ""

        # Process frames
        for frame_num, frame in video.frames():
            # Extract and normalize top screen
            top_screen = extract_top_screen(frame, layout)
            normalized = normalize_to_ds_resolution(top_screen, layout)

            # Detect textbox state
            state = textbox_detector.detect_state(normalized)

            # Handle state transitions
            if state == TextboxState.OPEN:
                text_region = textbox_detector.extract_text_region(normalized)

                if prev_state == TextboxState.CLOSED:
                    # Textbox just opened
                    prev_text_region = text_region.copy()

                elif prev_text_region is not None:
                    # Check if text is appearing character by character
                    if textbox_detector.is_text_appearing(prev_text_region, text_region):
                        # Text is being typed - this is "slow text"
                        # OCR would happen here once templates are ready
                        pass

                    prev_text_region = text_region.copy()

            elif state == TextboxState.CLOSED and prev_state == TextboxState.OPEN:
                # Textbox just closed - finalize current text
                if current_text:
                    extracted_lines.append(current_text)
                    current_text = ""
                prev_text_region = None

            prev_state = state

            if verbose and frame_num % 1000 == 0:
                print(f"Frame {frame_num}/{video.frame_count}", file=sys.stderr)

    # Combine results
    full_text = "\n".join(extracted_lines)
    char_count = sum(len(line.replace(" ", "")) for line in extracted_lines)

    # Output
    output_content = f"{full_text}\n\n---\nTotal characters: {char_count}\n"

    if output_path:
        output_path.write_text(output_content)
    else:
        print(output_content)

    return full_text, char_count


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from Pokemon Gen 4 speedrun videos."
    )
    parser.add_argument("video", type=Path, help="Path to video file")
    parser.add_argument("-o", "--output", type=Path, help="Output file path")
    parser.add_argument(
        "-g", "--game",
        choices=["diamond_pearl", "platinum", "hgss"],
        default="diamond_pearl",
        help="Game type (default: diamond_pearl)"
    )
    parser.add_argument(
        "-l", "--language",
        choices=["en", "it", "fr", "de", "es", "ja"],
        default="en",
        help="Game language (default: en)"
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print progress information")

    args = parser.parse_args()

    if not args.video.exists():
        print(f"Error: Video file not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    process_video(
        args.video,
        args.output,
        args.game,
        args.language,
        args.verbose
    )


if __name__ == "__main__":
    main()
