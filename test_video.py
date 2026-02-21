"""Quick test script to verify video reading and screen detection."""

import cv2
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.video import VideoReader
from src.screen import detect_screen_layout, extract_top_screen, normalize_to_ds_resolution

def test_video(video_path: str):
    """Test video reading and screen detection."""

    print(f"Testing video: {video_path}")
    print("-" * 50)

    with VideoReader(video_path) as video:
        print(f"Video info:")
        print(f"  Resolution: {video.width}x{video.height}")
        print(f"  FPS: {video.fps}")
        print(f"  Frame count: {video.frame_count}")
        print(f"  Duration: {video.frame_count / video.fps:.1f} seconds")
        print(f"  Is 60fps: {video.is_60fps}")
        print()

        # Get first frame
        frame = video.get_frame(0)
        if frame is None:
            print("ERROR: Could not read first frame")
            return

        print(f"First frame shape: {frame.shape}")

        # Detect screen layout
        layout = detect_screen_layout(frame)
        print(f"\nDetected screen layout:")
        print(f"  Top screen position: {layout.top_screen_pos.name}")
        print(f"  Top screen rect: {layout.top_screen_rect}")
        print(f"  Bottom screen rect: {layout.bottom_screen_rect}")
        print(f"  Scale factor: {layout.scale_factor:.2f}x")
        print(f"  Integer scale: {layout.is_integer_scale}")

        # Extract and save diagnostic images
        print("\nSaving diagnostic images...")

        # Save original frame
        cv2.imwrite("test_frame_original.png", frame)
        print("  Saved: test_frame_original.png")

        # Extract top screen
        top_screen = extract_top_screen(frame, layout)
        cv2.imwrite("test_frame_top_screen.png", top_screen)
        print(f"  Saved: test_frame_top_screen.png ({top_screen.shape[1]}x{top_screen.shape[0]})")

        # Normalize to DS resolution
        normalized = normalize_to_ds_resolution(top_screen, layout)
        cv2.imwrite("test_frame_normalized.png", normalized)
        print(f"  Saved: test_frame_normalized.png ({normalized.shape[1]}x{normalized.shape[0]})")

        # Also get a frame from later in the video (when textbox might be visible)
        # Try frame 1000 or halfway through
        test_frame_num = min(1000, video.frame_count // 2)
        later_frame = video.get_frame(test_frame_num)
        if later_frame is not None:
            later_top = extract_top_screen(later_frame, layout)
            later_norm = normalize_to_ds_resolution(later_top, layout)
            cv2.imwrite("test_frame_later.png", later_norm)
            print(f"  Saved: test_frame_later.png (frame {test_frame_num})")

        print("\nDone! Check the test_frame_*.png files to verify detection.")


if __name__ == "__main__":
    # Default to one of the sample videos
    video_path = sys.argv[1] if len(sys.argv) > 1 else "dp-any-gimmy.mp4"
    test_video(video_path)
