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
        List of dialogue dicts with 'frame', 'line1', 'line2', 'is_slow' keys
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
        current_dialogue = {'line1': '', 'line2': '', 'frame': 0, 'has_marker': False}
        textbox_was_open = False
        scroll_base = ''  # The text that scrolled up, to be prepended to new line2
        frames_since_marker = 0  # Count frames since we saw marker

        for frame_num in range(max_frames):
            frame = video.get_frame(frame_num)
            if frame is None:
                continue

            top_screen = extract_top_screen(frame, layout)
            normalized = normalize_to_ds_resolution(top_screen, layout)
            state = detector.detect_state(normalized)

            if state == TextboxState.OPEN:
                # Extract text lines
                line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]
                line2_img = normalized[TEXT_Y_LINE2:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]

                text1 = ocr.recognize_line(line1_img).strip()  # Strip leading/trailing spaces
                text2 = ocr.recognize_line(line2_img).strip()

                # Check for continue marker (indicates slow text completion)
                has_marker = detector.has_continue_marker(normalized)
                if has_marker:
                    current_dialogue['has_marker'] = True
                    frames_since_marker = 0

                # Detect scroll: current dialogue's line2 became current line1
                # This means the text scrolled up
                is_scroll = False
                old_line2 = current_dialogue.get('line2', '')
                if old_line2 and text1 and not scroll_base:
                    # Check if line1 matches the dialogue's line2 (scroll happened)
                    if text1 == old_line2 or (len(old_line2) > 10 and text1.startswith(old_line2[:10])):
                        is_scroll = True
                        scroll_base = old_line2  # Save the scrolled text to prepend later

                # Detect new dialogue: text reset to short/empty
                current_len = len(text1) + len(text2)
                prev_len = len(current_dialogue['line1']) + len(current_dialogue['line2'])

                # Dialogue reset if: text got much shorter OR content completely changed
                # Use relative threshold: text dropped by more than 60%
                is_reset = False
                if prev_len > 5:  # Only check if we had meaningful text before
                    if current_len < prev_len * 0.4:  # Dropped by more than 60%
                        is_reset = True
                    elif current_len < 3 and prev_len > 5:  # Reset to very short
                        is_reset = True

                if is_reset:
                    # Text got much shorter - save previous dialogue if it had marker
                    if current_dialogue['line1'] and current_dialogue['has_marker']:
                        dialogues.append(current_dialogue.copy())
                    # Start new dialogue
                    current_dialogue = {'line1': '', 'line2': '', 'frame': frame_num, 'has_marker': False}
                    scroll_base = ''  # Reset scroll state

                # Update current dialogue with more complete text
                if is_scroll or scroll_base:
                    # In scroll mode - keep line1 fixed, update line2 with scroll_base + text2
                    if text2:
                        new_line2 = scroll_base + " " + text2
                        # Only update if this is longer than what we have
                        if len(new_line2) > len(current_dialogue.get('line2', '')):
                            current_dialogue['line2'] = new_line2
                            current_dialogue['frame'] = frame_num
                elif not is_reset:
                    # Normal update - keep the longest/most complete text
                    if current_len >= prev_len:
                        current_dialogue['line1'] = text1
                        current_dialogue['line2'] = text2
                        current_dialogue['frame'] = frame_num

                textbox_was_open = True
                frames_since_marker += 1

            elif state == TextboxState.SCROLLING:
                # Still track scrolling state
                textbox_was_open = True
                frames_since_marker += 1

            elif textbox_was_open:
                # Textbox just closed - save current dialogue if it had marker
                if current_dialogue['line1'] and current_dialogue['has_marker']:
                    dialogues.append(current_dialogue.copy())
                current_dialogue = {'line1': '', 'line2': '', 'frame': 0, 'has_marker': False}
                textbox_was_open = False
                scroll_base = ''  # Reset scroll state
                frames_since_marker = 0

            if frame_num % 1000 == 0:
                print(f"  Processing frame {frame_num}/{max_frames}...")

        # Don't forget remaining text
        if current_dialogue['line1'] and current_dialogue['has_marker']:
            dialogues.append(current_dialogue.copy())

    # Deduplicate and merge scrolling dialogues
    deduped = []
    for d in dialogues:
        if not deduped:
            deduped.append(d)
            continue

        prev = deduped[-1]

        # Check if this is a scroll continuation (line1 matches prev line2)
        if d['line1'] == prev.get('line2', ''):
            # This is a scroll - merge: keep prev line1, use new line2
            prev['line2'] = d['line2']
            prev['frame'] = d['frame']
        elif d['line1'] == prev['line1']:
            # Same line1 - keep the one with more text in line2
            if len(d['line2']) > len(prev['line2']):
                deduped[-1] = d
        elif prev['line1'].startswith(d['line1'][:20]) if len(d['line1']) >= 20 else False:
            # Previous was more complete, skip this one
            pass
        elif d['line1'].startswith(prev['line1'][:20]) if len(prev['line1']) >= 20 else False:
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
