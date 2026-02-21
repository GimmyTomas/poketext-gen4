"""Extract and visualize the text region for OCR development."""

import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.video import VideoReader
from src.screen import detect_screen_layout, extract_top_screen, normalize_to_ds_resolution
from src.textbox import TextboxDetector

def extract_text_regions(video_path: str, frame_nums: list):
    """Extract text regions from specific frames."""

    print(f"Extracting text regions from: {video_path}")
    print("-" * 50)

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
            print(f"  Saved: test_ocr_region_{frame_num}_4x.png (enlarged)")
            print()

    print("Done!")


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else "dp-any-gimmy.mp4"
    # Frames with textboxes from previous test
    frame_nums = [2010, 2210, 2288, 2345, 2495]
    extract_text_regions(video_path, frame_nums)
