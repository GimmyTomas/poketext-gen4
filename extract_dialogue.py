"""Extract dialogue text from Pokemon Gen 4 video."""

import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.video import VideoReader
from src.screen import detect_screen_layout, extract_top_screen, normalize_to_ds_resolution
from src.textbox import TextboxDetector, TextboxState
from src.ocr import create_ocr


def extract_dialogues(video_path: str, max_seconds: float = None):
    """Extract all dialogue text from a video.

    Args:
        video_path: Path to the video file
        max_seconds: Maximum seconds to process (None = entire video)

    Returns:
        List of dialogue dicts with 'frame', 'line1', 'line2' keys
    """
    ocr = create_ocr()

    TEXT_Y_LINE1 = 152
    TEXT_Y_LINE2 = 168
    TEXT_X = 14
    CHAR_HEIGHT = 15

    with VideoReader(video_path) as video:
        frame0 = video.get_frame(0)
        layout = detect_screen_layout(frame0)
        detector = TextboxDetector()

        max_frames = video.frame_count
        if max_seconds:
            max_frames = min(max_frames, int(max_seconds * video.fps))

        dialogues = []
        max_text = ('', '')
        max_len = 0
        max_frame = 0
        textbox_was_open = False

        for frame_num in range(max_frames):
            frame = video.get_frame(frame_num)
            if frame is None:
                continue

            top_screen = extract_top_screen(frame, layout)
            normalized = normalize_to_ds_resolution(top_screen, layout)
            state = detector.detect_state(normalized)

            if state == TextboxState.OPEN:
                line1 = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]
                line2 = normalized[TEXT_Y_LINE2:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]

                text1 = ocr.recognize_line(line1)
                text2 = ocr.recognize_line(line2)
                current_len = len(text1) + len(text2)

                # Detect new dialogue: text got much shorter (reset)
                if current_len < max_len - 10 and max_len > 15:
                    if max_text[0]:
                        dialogues.append({
                            'frame': max_frame,
                            'line1': max_text[0],
                            'line2': max_text[1]
                        })
                    max_text = ('', '')
                    max_len = 0

                # Track the longest/most complete text
                if current_len > max_len:
                    max_text = (text1, text2)
                    max_len = current_len
                    max_frame = frame_num

                textbox_was_open = True

            elif state == TextboxState.CLOSED and textbox_was_open:
                if max_text[0]:
                    dialogues.append({
                        'frame': max_frame,
                        'line1': max_text[0],
                        'line2': max_text[1]
                    })
                max_text = ('', '')
                max_len = 0
                textbox_was_open = False

            if frame_num % 1000 == 0:
                print(f"  Processing frame {frame_num}/{max_frames}...")

        # Don't forget remaining text
        if max_text[0]:
            dialogues.append({
                'frame': max_frame,
                'line1': max_text[0],
                'line2': max_text[1]
            })

    # Deduplicate: keep most complete version when line1 matches
    deduped = []
    for d in dialogues:
        # Check if this is a more complete version of the previous dialogue
        if deduped and d['line1'] == deduped[-1]['line1']:
            # Keep the one with more text in line2
            if len(d['line2']) > len(deduped[-1]['line2']):
                deduped[-1] = d
        elif deduped and deduped[-1]['line1'].startswith(d['line1'][:20]):
            # Previous was more complete, skip this one
            pass
        elif deduped and d['line1'].startswith(deduped[-1]['line1'][:20]):
            # This one is more complete, replace
            deduped[-1] = d
        else:
            deduped.append(d)

    return deduped, video.fps


def format_time(frame: int, fps: float) -> str:
    """Format frame number as MM:SS.ss timestamp."""
    time_sec = frame / fps
    return f"{int(time_sec // 60)}:{time_sec % 60:05.2f}"


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else "dp-any-gimmy.mp4"
    max_seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 180  # Default 3 minutes

    print(f"Extracting dialogue from: {video_path}")
    print(f"Processing first {max_seconds} seconds...")
    print()

    dialogues, fps = extract_dialogues(video_path, max_seconds)

    print(f"\nFound {len(dialogues)} dialogues:")
    print("=" * 60)

    output_lines = []
    for d in dialogues:
        timestamp = format_time(d['frame'], fps)
        output_lines.append(f"[{timestamp}] {d['line1']}")
        if d['line2']:
            output_lines.append(f"           {d['line2']}")
        output_lines.append("")

    output_text = "\n".join(output_lines)
    print(output_text)

    # Save to file
    output_file = Path(video_path).stem + "_dialogue.txt"
    with open(output_file, 'w') as f:
        f.write(output_text)
    print(f"\nSaved to {output_file}")
