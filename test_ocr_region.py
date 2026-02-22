"""Extract and visualize the text region for OCR development."""

import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.video import VideoReader
from src.screen import detect_screen_layout, extract_top_screen, normalize_to_ds_resolution
from src.textbox import TextboxDetector
from src.ocr import create_ocr


def extract_text_regions(video_path: str, frame_nums: list, run_ocr: bool = False):
    """Extract text regions from specific frames."""

    print(f"Extracting text regions from: {video_path}")
    print("-" * 50)

    ocr = None
    if run_ocr:
        ocr = create_ocr()
        print(f"OCR loaded with {len(ocr.templates)} templates")
        print()

    with VideoReader(video_path) as video:
        frame = video.get_frame(0)
        layout = detect_screen_layout(frame)
        detector = TextboxDetector()

        for frame_num in frame_nums:
            frame = video.get_frame(frame_num)
            if frame is None:
                print(f"Frame {frame_num}: Could not read")
                continue

            top_screen = extract_top_screen(frame, layout)
            normalized = normalize_to_ds_resolution(top_screen, layout)

            # Extract text region
            text_region = detector.extract_text_region(normalized)

            # Save full normalized frame with textbox highlighted
            highlighted = normalized.copy()
            # Draw rectangle around text region
            cv2.rectangle(highlighted,
                         (detector.region.text_x, detector.region.text_y),
                         (detector.region.text_x + detector.region.text_width,
                          detector.region.text_y + detector.region.text_height),
                         (0, 255, 0), 1)
            cv2.imwrite(f"test_ocr_highlighted_{frame_num}.png", highlighted)

            # Save just the text region
            cv2.imwrite(f"test_ocr_region_{frame_num}.png", text_region)

            # Save enlarged text region (4x) for better visibility
            enlarged = cv2.resize(text_region, None, fx=4, fy=4,
                                  interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(f"test_ocr_region_{frame_num}_4x.png", enlarged)

            print(f"Frame {frame_num}:")
            print(f"  Text region shape: {text_region.shape}")
            print(f"  Saved: test_ocr_region_{frame_num}.png")

            if ocr:
                line1, line2 = ocr.recognize_textbox(text_region)
                print(f"  OCR Line 1: '{line1}'")
                print(f"  OCR Line 2: '{line2}'")
                total_chars = len(line1) + len(line2)
                print(f"  Total chars: {total_chars}")

            print()

    print("Done!")


def test_ocr_on_frames(frames_dir: str):
    """Test OCR on pre-extracted textbox frames."""
    frames_path = Path(frames_dir)
    if not frames_path.exists():
        print(f"Error: Directory not found: {frames_dir}")
        return

    ocr = create_ocr()
    print(f"OCR loaded with {len(ocr.templates)} templates")
    print("-" * 50)

    detector = TextboxDetector()

    # Get all PNG files sorted numerically
    png_files = sorted(frames_path.glob("*.png"), key=lambda p: int(p.stem))

    for png_file in png_files[:10]:  # Test first 10 frames
        img = cv2.imread(str(png_file))
        if img is None:
            print(f"{png_file.name}: Could not load")
            continue

        # Check if image needs normalization
        h, w = img.shape[:2]
        if w != 256 or h != 192:
            # Normalize to DS resolution
            scale = w // 256
            if scale > 1:
                img = cv2.resize(img, (256, 192), interpolation=cv2.INTER_AREA)

        # Extract text region
        text_region = detector.extract_text_region(img)

        # Run OCR
        line1, line2 = ocr.recognize_textbox(text_region)

        print(f"{png_file.name}:")
        print(f"  Line 1: '{line1}'")
        print(f"  Line 2: '{line2}'")
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--frames":
            # Test on pre-extracted frames
            frames_dir = sys.argv[2] if len(sys.argv) > 2 else "game-data/textbox-frames-dp"
            test_ocr_on_frames(frames_dir)
        else:
            # Test on video
            video_path = arg
            frame_nums = [2010, 2210, 2288, 2345, 2495]
            extract_text_regions(video_path, frame_nums, run_ocr=True)
    else:
        print("Usage:")
        print("  python test_ocr_region.py <video.mp4>    # Test on video frames")
        print("  python test_ocr_region.py --frames [dir] # Test on pre-extracted frames")
        print()
        print("Running default test on game-data/textbox-frames-dp...")
        test_ocr_on_frames("game-data/textbox-frames-dp")
