"""Extract dialogue text from Pokemon Gen 4 video."""

import cv2
import numpy as np
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.video import VideoReader
from src.screen import detect_screen_layout, extract_top_screen, normalize_to_ds_resolution
from src.textbox import TextboxDetector, TextboxState
from src.ocr import create_ocr


def is_garbage_text(text: str) -> bool:
    """Check if text is garbage (OCR artifacts from transitions).

    Returns True for text that appears to be OCR artifacts, such as:
    - Mostly quotes/apostrophes (transition artifacts)
    - Special characters with no alphanumeric (except valid punctuation like ...)
    - Very short fragments with mostly symbols
    - Text containing snowman or card symbols (OCR false positives)

    Returns False for valid text including:
    - Text with sufficient alphanumeric characters
    - Ellipsis ... which is a valid dialogue
    """
    if not text:
        return True

    # Count alphanumeric characters
    alnum_count = sum(1 for c in text if c.isalnum())

    # Ellipsis (dots only) is valid dialogue, but very short patterns like ". ." are noise
    stripped = text.replace(' ', '')
    if stripped and all(c == '.' for c in stripped):
        # Must be at least 3 dots to be valid ellipsis "..."
        if len(stripped) >= 3:
            return False
        # Fewer than 3 dots is likely noise
        return True

    # Text containing snowman, card, or emoji symbols is likely OCR false positive
    garbage_symbols = set("☃☀☁☂♣♦♥♠□△◇↓")
    if any(c in garbage_symbols for c in text):
        return True
    # Emoji characters (outside BMP) are definitely OCR garbage
    if any(ord(c) > 0xFFFF for c in text):
        return True

    # Filter out menu/settings text that appears like slow text but isn't needed
    menu_patterns = ["WINDOW TYPE", "TEXT SPEED", "BATTLE SCENE", "BATTLE STYLE"]
    if any(pattern in text.upper() for pattern in menu_patterns):
        return True

    # Isolated pocket icon (■) without text is likely transition noise
    # But valid text like "It ■" or "nella Tasca ■S" should be kept
    # Only filter if the pocket icon is alone or with random/short characters
    if '■' in text:
        # Check if it's just the icon or icon with short noise
        text_without_icon = text.replace('■', '').strip()
        # Filter out if remaining text is very short (<=5 chars) and doesn't look like valid text
        # Valid text usually has words or meaningful content
        if len(text_without_icon) <= 5:
            # Check if it contains actual words (uppercase letters or multiple consecutive letters)
            has_uppercase = any(c.isupper() for c in text_without_icon)
            has_word = any(len(part) >= 3 for part in text_without_icon.split() if part.isalpha())
            if not has_uppercase and not has_word:
                return True

    # Very short fragments with isolated single letters are garbage
    # Valid short text: "OK", "No!", "Sì!", "I?", "G ..." — words or letter+punctuation
    # Garbage: "L j" (two random single letters separated by space)
    if alnum_count <= 2:
        # Check if all alpha characters are isolated single letters (no consecutive alpha)
        alpha_runs = re.findall(r'[a-zA-ZÀ-ÿ]+', text)
        has_multi_letter_word = any(len(run) >= 2 for run in alpha_runs)
        if not has_multi_letter_word and len(alpha_runs) >= 2:
            # Multiple isolated single letters (like "L j", "g ,L") = garbage
            return True

    # Short text starting with punctuation is likely garbage
    # Valid dialogue starts with a letter, digit, or "..." (already handled above)
    # Examples of garbage: ",L L", "…, gyg", "' ab"
    # Exception: text starting with accented chars (é, è, etc.) is valid
    if stripped and not stripped[0].isalnum():
        # Starts with punctuation
        if len(stripped) <= 8 and alnum_count <= 4:
            # Short text starting with punctuation and few letters = garbage
            return True

    # Short random lowercase text with punctuation is likely OCR noise
    # Valid dialogue typically starts with capital letter or is proper text
    # Examples of garbage: "pgp '", "ab ", "xyz"
    # Examples of valid: "e così...", "di nuovo"
    if len(stripped) <= 6 and stripped:
        # Check if it's all lowercase with punctuation (no capitals, no numbers)
        has_uppercase = any(c.isupper() for c in text)
        has_digit = any(c.isdigit() for c in text)
        has_common_punct = any(c in '.!?,' for c in text)
        if not has_uppercase and not has_digit and not has_common_punct:
            # Random lowercase letters with apostrophes/spaces - likely garbage
            # Check for both straight and curly apostrophes
            any_quote = any(c in "'\u2018\u2019" for c in text)
            if alnum_count <= 4 and any_quote:
                return True

    # Single letter fragments with special symbols are likely garbage
    # This catches fragments like "e ♣", "g■"
    # But allows valid short text like "G ...", "OK...", "No!", "Sì"
    if alnum_count == 1:
        # Single letter with special symbols (not standard punctuation) is garbage
        non_alnum = [c for c in text if not c.isalnum() and c not in ' .!?,…']
        if non_alnum:
            return True
        # Check for garbage patterns: punctuation-letter-punctuation (like "…, g,")
        # But allow valid patterns like "G ..." (letter followed by space and dots)
        stripped = text.strip()
        if stripped and stripped[0].isalnum():
            # Starts with letter - likely valid (e.g., "G ...", "I?")
            pass
        elif len(text) > 3:
            # Starts with punctuation and is long - likely garbage
            return True

    # Text must have at least some alphanumeric content to be valid
    if alnum_count == 0:
        # Mostly quotes/apostrophes is garbage (transition artifacts)
        quote_chars = set("'\"''""\u2018\u2019\u201c\u201d")
        quote_count = sum(1 for c in text if c in quote_chars)
        if quote_count > len(text) * 0.5:
            return True
        # Non-alphanumeric text without dots is likely garbage
        return True

    # Long text with very low alphanumeric ratio is likely OCR garbage
    # Real dialogue has 50%+ alphanumeric; scroll animation artifacts have <30%
    # e.g., "■ ìì'.,,". …,"?,,. . , ,↓,,.Ì,Ì"" " ì" (14% alnum)
    text_len = len(text.replace(' ', ''))
    if text_len >= 10 and alnum_count / text_len < 0.30:
        return True

    return False


def is_valid_textbox_region(line_img: np.ndarray, threshold: int = 200) -> bool:
    """Check if the line image has a valid textbox background.

    A real textbox has a white background (mean > threshold). Scenes without
    textboxes (like shop interiors) have dark backgrounds.

    Args:
        line_img: The line image to check
        threshold: Minimum mean brightness (200 for DP, 150 for HGSS)
    """
    if len(line_img.shape) == 3:
        gray = cv2.cvtColor(line_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = line_img
    return np.mean(gray) > threshold


def extract_dialogues(video_path: str, start_seconds: float = 0, end_seconds: float = None):
    """Extract all dialogue text from a video.

    Args:
        video_path: Path to the video file
        start_seconds: Start time in seconds (default: 0)
        end_seconds: End time in seconds (None = entire video)

    Returns:
        List of dialogue dicts with 'frame', 'line1', 'line2', 'is_slow' keys
    """
    ocr = create_ocr()

    TEXT_Y_LINE1 = 152
    TEXT_Y_LINE2 = 168
    CHAR_HEIGHT = 15
    BIG_CHAR_HEIGHT = 30  # For 2x vertically stretched text like "Pum!!!"

    # Detect game from filename
    video_lower = video_path.lower()
    if "hgss" in video_lower or "heartgold" in video_lower or "soulsilver" in video_lower:
        game = "hgss"
    elif "platinum" in video_lower:
        game = "platinum"
    else:
        game = "diamond_pearl"

    # Game-specific text region parameters
    # HGSS text starts at x=24 and extends close to edge (vs DP at x=14)
    # HGSS uses more horizontal space - need extra padding for template matching
    if game == "hgss":
        TEXT_X = 8        # Start from textbox edge
        TEXT_WIDTH = 248  # 8 + 248 = 256, full screen width
        validity_threshold = 150
    else:
        TEXT_X = 14
        TEXT_WIDTH = 232  # 14 + 232 = 246, leaving some margin
        validity_threshold = 200

    with VideoReader(video_path) as video:
        # Get first frame for layout detection
        first_frame = next(video.frames(max_frames=1))[1]
        layout = detect_screen_layout(first_frame)
        detector = TextboxDetector(game=game)

        start_frame = int(start_seconds * video.fps)
        end_frame = video.frame_count
        if end_seconds is not None:
            end_frame = min(end_frame, int(end_seconds * video.fps))

        dialogues = []
        current_dialogue = {'line1': '', 'line2': '', 'frame': 0, 'is_slow': True}
        textbox_was_open = False
        scroll_base = ''  # The text that scrolled up, to be prepended to new line2
        prev_text_len = 0  # Track text length to detect instant vs slow text
        text_growth_count = 0  # Count frames where text grew incrementally

        # Use sequential frame reading (much faster than seeking)
        for frame_num, frame in video.frames(start_frame=start_frame, max_frames=end_frame):

            top_screen = extract_top_screen(frame, layout)
            normalized = normalize_to_ds_resolution(top_screen, layout)
            state = detector.detect_state(normalized)

            if state == TextboxState.OPEN:
                # Extract text lines
                line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + CHAR_HEIGHT, TEXT_X:TEXT_X + TEXT_WIDTH]
                line2_img = normalized[TEXT_Y_LINE2:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + TEXT_WIDTH]

                # Add white padding on right for HGSS to allow template matching at edge
                # HGSS text extends close to screen edge, templates need space after chars
                if game == "hgss":
                    padding = np.full((CHAR_HEIGHT, 20, 3), 255, dtype=np.uint8)
                    line1_img = np.hstack([line1_img, padding])
                    line2_img = np.hstack([line2_img, padding])

                # Validate textbox region (must have white background)
                if not is_valid_textbox_region(line1_img, validity_threshold):
                    # Not a real textbox - skip this frame
                    continue

                text1 = ocr.recognize_line(line1_img).strip()  # Strip leading/trailing spaces
                text2 = ocr.recognize_line(line2_img).strip()

                # Try big text detection if normal OCR finds nothing but there are dark pixels
                # Big text is 2x vertically stretched (like "Pum!!!", "Thud!!!")
                if not text1 and line1_img.min() < 120:
                    # Extract larger region for big text (30 pixels tall)
                    big_line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + BIG_CHAR_HEIGHT, TEXT_X:TEXT_X + TEXT_WIDTH]
                    text1 = ocr.recognize_big_text(big_line1_img).strip()
                    # Filter out garbage from big text detection (like transition artifacts)
                    if is_garbage_text(text1):
                        text1 = ""

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

                # Handle consecutive scrolls (for 4+ line dialogues)
                # If we already have scroll_base set and detect another scroll, append to scroll_lines
                # Key: we need to check if text1 matches scroll_base (the previous scrolled line)
                # AND text1 is different from what we last saw as line1
                if scroll_base and text1 and old_line2 and text1 != scroll_base:
                    # Check if this is another scroll: old_line2 scrolled up to become text1
                    # AND text1 is different from scroll_base (it's a NEW scroll, not the same one)
                    line1_matches_old_line2 = (text1 == old_line2 or
                                               (len(old_line2) > 10 and text1.startswith(old_line2[:10])))
                    if line1_matches_old_line2:
                        # This is a consecutive scroll - append old scroll_base to scroll_lines
                        if 'scroll_lines' not in current_dialogue:
                            current_dialogue['scroll_lines'] = []
                        current_dialogue['scroll_lines'].append(scroll_base)
                        scroll_base = old_line2  # Update scroll_base to new scrolled line
                        is_scroll = True

                # Original scroll detection for first scroll
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

                # Handle empty/garbage frames during scroll animation
                # When text temporarily disappears or becomes garbled during scroll,
                # don't reset the dialogue. HGSS scroll animations produce frames where
                # OCR reads garbage (mid-scroll pixel shifts).
                # But only do this for slow text (text_growth_count > 0)
                # Instant text (like battle menu) should be allowed to reset naturally
                if current_dialogue['line1'] and current_dialogue['line2'] and text_growth_count > 0:
                    if current_len == 0 and prev_len > 0:
                        # Text disappeared - scroll animation
                        prev_text_len = 0
                        continue
                    if current_len < prev_len and prev_len > 10:
                        # Text got much shorter during active slow text with both lines.
                        # This could be a scroll animation frame (garbage OCR from mid-scroll
                        # pixel shifts) OR a real new dialogue starting.
                        # Distinguish: scroll garbage is garbled/nonsensical text, while
                        # a real new dialogue starts with clean text (like "B" for "But...").
                        old_l2_prefix = old_line2[:10] if len(old_line2) > 10 else old_line2
                        looks_like_scroll = text1.startswith(old_l2_prefix) if text1 and old_l2_prefix else False
                        if not looks_like_scroll and is_garbage_text(text1):
                            # Garbled text that doesn't match scroll pattern - skip
                            prev_text_len = 0
                            continue
                    # Otherwise this is a dialogue ending (possibly instant text) - let is_reset handle it

                if prev_len > 5:  # Only check if we had meaningful text before
                    if current_len < prev_len * 0.4:  # Dropped by more than 60%
                        is_reset = True
                    elif current_len < 3 and prev_len > 5:  # Reset to very short
                        is_reset = True

                # Check for content change: line1 completely different from previous
                # This catches cases where text changes to new dialogue without length drop
                # BUT skip this check if it's a scroll (where old line2 became new line1)
                # Also skip when in scroll mode (scroll_base set) - the visible line1 differs
                # from stored line1 because we preserve the original for proper output
                if prev_line1 and text1 and not is_scroll and not scroll_base:
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
                    elif len(prev_line1) >= 2 and text_growth_count >= 1:
                        # Special case for very short dialogues like "..."
                        # Only save punctuation-only short dialogues (like "...")
                        # Don't save mixed text like ",L" which are transition artifacts
                        prev_is_punct_only = not any(c.isalnum() for c in prev_line1)
                        new_starts_with_letter = text1[0].isalnum() if text1 else False
                        if prev_is_punct_only and new_starts_with_letter:
                            # Punctuation dialogue (like "...") followed by text
                            content_different = True
                    if content_different:
                        is_content_change = True
                        is_reset = True

                if is_reset:
                    # Save previous dialogue if it's slow text
                    # Slow text should have had incremental growth (text_growth_count > 0)
                    is_slow = text_growth_count > 0
                    # Also filter out garbage text (artifacts from transitions)
                    is_valid = not is_garbage_text(current_dialogue['line1'])
                    if current_dialogue['line1'] and is_slow and is_valid:
                        # Add any pending scroll_base to scroll_lines before saving
                        if scroll_base:
                            if 'scroll_lines' not in current_dialogue:
                                current_dialogue['scroll_lines'] = []
                            current_dialogue['scroll_lines'].append(scroll_base)
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
                        # First scroll - save original line1
                        current_dialogue['scroll_line1'] = current_dialogue['line1']
                        # Reset line2 so the new post-scroll line2 can grow from scratch
                        current_dialogue['line2'] = ''
                        # Note: scroll_base is added to scroll_lines by the consecutive scroll
                        # detection code when the NEXT scroll happens (or at dialogue end)

                    if text2 and len(text2) >= len(current_dialogue.get('line2', '')):
                        # Track new line2 after scroll (will be output as separate line)
                        # Only update if text grew (avoid replacing complete text with truncated)
                        current_dialogue['line2'] = text2
                        current_dialogue['frame'] = frame_num

                    # Keep original line1 (scroll_line1)
                    if current_dialogue.get('scroll_line1'):
                        current_dialogue['line1'] = current_dialogue['scroll_line1']
                elif not is_reset:
                    # Normal update - keep the longest/most complete text
                    # Use > (not >=) to avoid replacing good text with corrupted transition frames
                    if current_len > prev_len:
                        current_dialogue['line1'] = text1
                        current_dialogue['line2'] = text2
                        current_dialogue['frame'] = frame_num

                textbox_was_open = True

            elif state == TextboxState.SCROLLING:
                # SCROLLING state - might be actual scrolling OR text like "Pum!!!"
                # that extends into the detection strip area
                # Still try to extract text
                line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + CHAR_HEIGHT, TEXT_X:TEXT_X + TEXT_WIDTH]
                line2_img = normalized[TEXT_Y_LINE2:TEXT_Y_LINE2 + CHAR_HEIGHT, TEXT_X:TEXT_X + TEXT_WIDTH]

                # Validate textbox region (must have white background)
                # This filters out false positives from game scenes
                if not is_valid_textbox_region(line1_img, validity_threshold):
                    continue

                text1 = ocr.recognize_line(line1_img).strip()
                text2 = ocr.recognize_line(line2_img).strip()

                # Try big text detection if normal OCR finds nothing but there are dark pixels
                # Big text like "Pum!!!" triggers SCROLLING state because it extends into detection strip
                if not text1 and line1_img.min() < 120:
                    big_line1_img = normalized[TEXT_Y_LINE1:TEXT_Y_LINE1 + BIG_CHAR_HEIGHT, TEXT_X:TEXT_X + TEXT_WIDTH]
                    text1 = ocr.recognize_big_text(big_line1_img).strip()
                    # Filter out garbage from big text detection
                    if is_garbage_text(text1):
                        text1 = ""

                # Track text growth
                current_text_len = len(text1) + len(text2)
                text_delta = current_text_len - prev_text_len
                if 0 < text_delta <= 4:
                    text_growth_count += 1
                prev_text_len = current_text_len

                # Update if we have more text than before
                # Use > (not >=) to avoid replacing good text with corrupted transition frames
                current_len = len(text1) + len(text2)
                prev_len = len(current_dialogue['line1']) + len(current_dialogue['line2'])
                if current_len > prev_len:
                    current_dialogue['line1'] = text1
                    current_dialogue['line2'] = text2
                    current_dialogue['frame'] = frame_num

                textbox_was_open = True

            elif textbox_was_open:
                # Textbox just closed - save current dialogue if it's slow text
                # Slow text should have had incremental growth
                is_slow = text_growth_count > 0
                is_valid = not is_garbage_text(current_dialogue['line1'])
                if current_dialogue['line1'] and is_slow and is_valid:
                    # Add any pending scroll_base to scroll_lines before saving
                    if scroll_base:
                        if 'scroll_lines' not in current_dialogue:
                            current_dialogue['scroll_lines'] = []
                        current_dialogue['scroll_lines'].append(scroll_base)
                    dialogues.append(current_dialogue.copy())
                current_dialogue = {'line1': '', 'line2': '', 'frame': 0, 'is_slow': True}
                textbox_was_open = False
                scroll_base = ''  # Reset scroll state
                prev_text_len = 0
                text_growth_count = 0

            if frame_num % 1000 == 0:
                print(f"  Processing frame {frame_num}/{end_frame}...")

        # Don't forget remaining text (if it was slow text)
        if current_dialogue['line1'] and text_growth_count > 0 and not is_garbage_text(current_dialogue['line1']):
            # Add any pending scroll_base to scroll_lines before saving
            if scroll_base:
                if 'scroll_lines' not in current_dialogue:
                    current_dialogue['scroll_lines'] = []
                current_dialogue['scroll_lines'].append(scroll_base)
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
    if len(sys.argv) < 2:
        print("Usage: python extract_dialogue.py <video.mp4> [end_seconds | start_seconds end_seconds]")
        print()
        print("Examples:")
        print("  python extract_dialogue.py video.mp4           # Extract entire video")
        print("  python extract_dialogue.py video.mp4 180       # Extract first 180 seconds")
        print("  python extract_dialogue.py video.mp4 60 120    # Extract from 1:00 to 2:00")
        sys.exit(1)

    video_path = sys.argv[1]
    start_seconds = 0.0
    end_seconds = None

    if len(sys.argv) == 3:
        # Single time argument: extract from start to this time
        end_seconds = float(sys.argv[2])
    elif len(sys.argv) >= 4:
        # Two time arguments: extract from start_time to end_time
        start_seconds = float(sys.argv[2])
        end_seconds = float(sys.argv[3])

    print(f"Extracting dialogue from: {video_path}")
    if start_seconds == 0 and end_seconds is None:
        print("Processing entire video...")
    elif start_seconds == 0:
        print(f"Processing first {end_seconds} seconds...")
    else:
        print(f"Processing from {start_seconds}s to {end_seconds}s...")
    print()

    dialogues, fps = extract_dialogues(video_path, start_seconds, end_seconds)

    output_lines = []
    total_chars = 0
    for d in dialogues:
        # No timestamps - just the dialogue text
        # Line2 is vertically aligned with line1 (no indent)
        output_lines.append(d['line1'])
        total_chars += len(d['line1'])
        # Output scrolled lines as separate lines (not concatenated)
        if d.get('scroll_lines'):
            for scroll_line in d['scroll_lines']:
                output_lines.append(scroll_line)
                total_chars += len(scroll_line)
        if d['line2']:
            output_lines.append(d['line2'])
            total_chars += len(d['line2'])
        output_lines.append("")

    output_text = "\n".join(output_lines)

    # Save to file
    output_file = Path(video_path).stem + "_dialogue.txt"
    with open(output_file, 'w') as f:
        f.write(output_text)

    # Print summary
    text_seconds = total_chars / 60
    print(f"\nFound {len(dialogues)} dialogues")
    print(f"Total characters: {total_chars} ({text_seconds:.2f} seconds of text)")
    print(f"Saved to: {output_file}")
