"""Video frame extraction using OpenCV."""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import Iterator, Tuple, Optional, Union


class VideoReader:
    """Reads video files and extracts frames."""

    def __init__(self, video_path: Union[str, Path]):
        self.video_path = Path(video_path)
        self.cap = cv2.VideoCapture(str(self.video_path))

        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.cap.release()

    def frames(self, start_frame: int = 0, max_frames: Optional[int] = None) -> Iterator[Tuple[int, np.ndarray]]:
        """Yield (frame_number, frame) tuples.

        Args:
            start_frame: Frame number to start from (default: 0)
            max_frames: Stop after reaching this frame number (None = all frames)
        """
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_num = start_frame
        while max_frames is None or frame_num < max_frames:
            ret, frame = self.cap.read()
            if not ret:
                break
            yield frame_num, frame
            frame_num += 1

    def get_frame(self, frame_num: int) -> Optional[np.ndarray]:
        """Get a specific frame by number."""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        return frame if ret else None

    @property
    def is_60fps(self) -> bool:
        """Check if video is 60fps (or close to it)."""
        return self.fps > 55

    def __repr__(self):
        return (f"VideoReader({self.video_path.name}, "
                f"{self.width}x{self.height}, "
                f"{self.fps:.2f}fps, "
                f"{self.frame_count} frames)")
