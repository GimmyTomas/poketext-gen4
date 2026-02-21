"""Test textbox detection on a video."""

import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.video import VideoReader
from src.screen import detect_screen_layout, extract_top_screen, normalize_to_ds_resolution
from src.textbox import TextboxDetector, TextboxState

def find_textbox_frame(video_path: str, start_frame: int = 0, max_frames: int = 10000):
    """Find frames with open textboxes."""

    print(f"Searching for textbox frames in: {video_path}")
    print(f"Starting from frame {start_frame}, checking up to {max_frames} frames")
    print("-" * 50)

    with VideoReader(video_path) as video:
        # Get layout from first frame
        frame = video.get_frame(0)
        layout = detect_screen_layout(frame)
        print(f"Layout: {layout.top_screen_pos.name}, scale={layout.scale_factor:.2f}x")

        detector = TextboxDetector()

        found_frames = []
        prev_state = TextboxState.CLOSED

        for frame_num in range(start_frame, min(start_frame + max_frames, video.frame_count)):
            frame = video.get_frame(frame_num)
            if frame is None:
                continue

            top_screen = extract_top_screen(frame, layout)
            normalized = normalize_to_ds_resolution(top_screen, layout)

            state = detector.detect_state(normalized)

            # Detect state transitions
            if state == TextboxState.OPEN and prev_state != TextboxState.OPEN:
                print(f"Frame {frame_num}: Textbox OPENED")
                found_frames.append((frame_num, "opened", normalized))

                # Save this frame
                cv2.imwrite(f"test_textbox_frame_{frame_num}.png", normalized)

                if len(found_frames) >= 5:
                    print(f"\nFound {len(found_frames)} textbox transitions. Stopping.")
                    break

            elif state == TextboxState.CLOSED and prev_state == TextboxState.OPEN:
                print(f"Frame {frame_num}: Textbox CLOSED")

            prev_state = state

            if frame_num % 1000 == 0:
                print(f"  Checked frame {frame_num}...")

    if not found_frames:
        print("\nNo textbox frames found. Let's save some sample frames to inspect manually.")
        # Save frames at different points for manual inspection
        with VideoReader(video_path) as video:
            frame = video.get_frame(0)
            layout = detect_screen_layout(frame)

            for sample_frame in [3000, 5000, 7000, 10000, 15000]:
                if sample_frame < video.frame_count:
                    frame = video.get_frame(sample_frame)
                    if frame is not None:
                        top_screen = extract_top_screen(frame, layout)
                        normalized = normalize_to_ds_resolution(top_screen, layout)
                        cv2.imwrite(f"test_sample_frame_{sample_frame}.png", normalized)
                        print(f"Saved test_sample_frame_{sample_frame}.png")

    print("\nDone!")


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else "dp-any-gimmy.mp4"
    start_frame = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    find_textbox_frame(video_path, start_frame)
