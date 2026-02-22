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
    BIG_CHAR_HEIGHT = 30  # For 2x vertically stretched text like "Pum!!!"

    with VideoReader(video_path) as video:
        # Get first frame for layout detection
        first_frame = next(video.frames(max_frames=1))[1]
        layout = detect_screen_layout(first_frame)
        detector = TextboxDetector()

        max_frames = video.frame_count
        if max_seconds:
            max_frames = min(max_frames, int(max_seconds * video.fps))

        dialogues = []
        current_dialogue = {'line1': '', 'line2': '', 'frame': 0, 'is_slow': True}
        textbox_was_open = False
        scroll_base = ''  # The text that scrolled up, to be prepended to new line2
        prev_text_len = 0  # Track text length to detect instant vs slow text
        text_growth_count = 0  # Count frames where text grew incrementally

        # Use sequential frame reading (much faster than seeking)
        for frame_num, frame in video.frames(max_frames=max_frames):

            top_screen = extract_top_screen(frame, layout)
            normalized = normalize_to_ds_resolution(top_screen, layout)
            state = detector.detect_state(normalized)

            if state == TextboxState.OPEN:
                # Extract text lines
                line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]
                line2_img = normalized[TEXT_Y_LINE2:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]

                text1 = ocr.recognize_line(line1_img).strip()  # Strip leading/trailing spaces
                text2 = ocr.recognize_line(line2_img).strip()

                # Try big text detection if normal OCR finds nothing but there are dark pixels
                # Big text is 2x vertically stretched (like "Pum!!!", "Thud!!!")
                if not text1 and line1_img.min() < 120:
                    # Extract larger region for big text (30 pixels tall)
                    big_line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + BIG_CHAR_HEIGHT, TEXT_X:TEXT_X + 220]
                    text1 = ocr.recognize_big_text(big_line1_img).strip()

                # Detect instant vs slow text based on how text appears
                # Slow text: grows incrementally (1-3 chars per frame)
                # Instant text: appears all at once (large jump on first frame)
                current_text_len = len(text1) + len(text2)
                text_delta = current_text_len - prev_text_len

                if text_delta > 0:
                    # Text is growing
                    if text_delta <= 4:
                        # Small incremental growth = slow text
                        text_growth_count += 1
                    elif prev_text_len == 0 and text_delta >= 10:
                        # Large initial appearance = might be instant text
                        # But wait to see if it grows further
                        pass

                prev_text_len = current_text_len

                # After a few frames of no growth, check if it was instant text
                # Instant text: appears all at once, then doesn't change
                # We'll check this when dialogue ends

                # Detect scroll: current dialogue's line2 became current line1
                # This means the text scrolled up
                # A scroll occurs when: new line1 == old line2 AND line1 actually changed
                is_scroll = False
                old_line1 = current_dialogue.get('line1', '')
                old_line2 = current_dialogue.get('line2', '')
                if old_line2 and text1 and not scroll_base:
                    # Check if line1 matches the dialogue's line2 (scroll happened)
                    # Also verify line1 actually changed (to avoid false positives when line1==line2)
                    line1_changed = (text1 != old_line1)
                    line1_matches_old_line2 = (text1 == old_line2 or
                                               (len(old_line2) > 10 and text1.startswith(old_line2[:10])))
                    if line1_changed and line1_matches_old_line2:
                        is_scroll = True
                        scroll_base = old_line2  # Save the scrolled text for separate line output

                # Detect new dialogue: text reset to short/empty OR content completely changed
                current_len = len(text1) + len(text2)
                prev_len = len(current_dialogue['line1']) + len(current_dialogue['line2'])
                prev_line1 = current_dialogue['line1']

                # Dialogue reset conditions:
                # 1. Text length dropped significantly (>60%)
                # 2. Text is very short when it was long before
                # 3. Content completely changed (line1 doesn't share common prefix)
                is_reset = False
                is_content_change = False

                if prev_len > 5:  # Only check if we had meaningful text before
                    if current_len < prev_len * 0.4:  # Dropped by more than 60%
                        is_reset = True
                    elif current_len < 3 and prev_len > 5:  # Reset to very short
                        is_reset = True

                # Check for content change: line1 completely different from previous
                # This catches cases where text changes to new dialogue without length drop
                # BUT skip this check if it's a scroll (where old line2 became new line1)
                if prev_line1 and text1 and not is_scroll:
                    content_different = False
                    if len(prev_line1) >= 5 and len(text1) >= 5:
                        # For longer text, check prefix
                        if prev_line1[:5] != text1[:5]:
                            content_different = True
                    elif len(prev_line1) >= 3 and text_growth_count >= 3:
                        # For short text (3+ chars), check if content is completely different
                        # AND previous dialogue had significant growth (3+ frames of incremental growth)
                        # This saves short dialogues like "..." before they get overwritten
                        if not text1.startswith(prev_line1) and not prev_line1.startswith(text1):
                            content_different = True
                    if content_different:
                        is_content_change = True
                        is_reset = True

                if is_reset:
                    # Save previous dialogue if it's slow text
                    # Slow text should have had incremental growth (text_growth_count > 0)
                    is_slow = text_growth_count > 0
                    if current_dialogue['line1'] and is_slow:
                        dialogues.append(current_dialogue.copy())
                    # Start new dialogue
                    current_dialogue = {'line1': '', 'line2': '', 'frame': frame_num, 'is_slow': True}
                    scroll_base = ''  # Reset scroll state
                    prev_text_len = 0
                    text_growth_count = 0

                    # Store the new text (whether from content change or length drop)
                    if text1 or text2:
                        current_dialogue['line1'] = text1
                        current_dialogue['line2'] = text2
                        current_dialogue['frame'] = frame_num
                        # Track from current length - wait to see if it grows incrementally
                        prev_text_len = current_len

                # Update current dialogue with more complete text
                if is_scroll or scroll_base:
                    # In scroll mode - keep ORIGINAL line1, track scrolled lines separately
                    if is_scroll and not current_dialogue.get('scroll_line1'):
                        # First scroll - save original line1 and line2
                        current_dialogue['scroll_line1'] = current_dialogue['line1']
                        # Store the pre-scroll line2 as a separate line
                        if 'scroll_lines' not in current_dialogue:
                            current_dialogue['scroll_lines'] = []
                        current_dialogue['scroll_lines'].append(scroll_base)

                    if text2:
                        # Track new line2 after scroll (will be output as separate line)
                        current_dialogue['line2'] = text2
                        current_dialogue['frame'] = frame_num

                    # Keep original line1 (scroll_line1)
                    if current_dialogue.get('scroll_line1'):
                        current_dialogue['line1'] = current_dialogue['scroll_line1']
                elif not is_reset:
                    # Normal update - keep the longest/most complete text
                    if current_len >= prev_len:
                        current_dialogue['line1'] = text1
                        current_dialogue['line2'] = text2
                        current_dialogue['frame'] = frame_num

                textbox_was_open = True

            elif state == TextboxState.SCROLLING:
                # SCROLLING state - might be actual scrolling OR text like "Pum!!!"
                # that extends into the detection strip area
                # Still try to extract text
                line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]
                line2_img = normalized[TEXT_Y_LINE2:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + 220]

                text1 = ocr.recognize_line(line1_img).strip()
                text2 = ocr.recognize_line(line2_img).strip()

                # Try big text detection if normal OCR finds nothing but there are dark pixels
                # Big text like "Pum!!!" triggers SCROLLING state because it extends into detection strip
                if not text1 and line1_img.min() < 120:
                    big_line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + BIG_CHAR_HEIGHT, TEXT_X:TEXT_X + 220]
                    text1 = ocr.recognize_big_text(big_line1_img).strip()

                # Track text growth
                current_text_len = len(text1) + len(text2)
                text_delta = current_text_len - prev_text_len
                if 0 < text_delta <= 4:
                    text_growth_count += 1
                prev_text_len = current_text_len

                # Update if we have more text than before
                current_len = len(text1) + len(text2)
                prev_len = len(current_dialogue['line1']) + len(current_dialogue['line2'])
                if current_len >= prev_len:
                    current_dialogue['line1'] = text1
                    current_dialogue['line2'] = text2
                    current_dialogue['frame'] = frame_num

                textbox_was_open = True

            elif textbox_was_open:
                # Textbox just closed - save current dialogue if it's slow text
                # Slow text should have had incremental growth
                is_slow = text_growth_count > 0
                if current_dialogue['line1'] and is_slow:
                    dialogues.append(current_dialogue.copy())
                current_dialogue = {'line1': '', 'line2': '', 'frame': 0, 'is_slow': True}
                textbox_was_open = False
                scroll_base = ''  # Reset scroll state
                prev_text_len = 0
                text_growth_count = 0

            if frame_num % 1000 == 0:
                print(f"  Processing frame {frame_num}/{max_frames}...")

        # Don't forget remaining text (if it was slow text)
        if current_dialogue['line1'] and text_growth_count > 0:
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
        # No timestamps - just the dialogue text
        # Line2 is vertically aligned with line1 (no indent)
        output_lines.append(d['line1'])
        # Output scrolled lines as separate lines (not concatenated)
        if d.get('scroll_lines'):
            for scroll_line in d['scroll_lines']:
                output_lines.append(scroll_line)
        if d['line2']:
            output_lines.append(d['line2'])
        output_lines.append("")

    output_text = "\n".join(output_lines)
    print(output_text)

    # Save to file
    output_file = Path(video_path).stem + "_dialogue.txt"
    with open(output_file, 'w') as f:
        f.write(output_text)
    print(f"\nSaved to {output_file}")
