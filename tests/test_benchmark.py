#!/usr/bin/env python3
"""Benchmark test to verify dialogue extraction output doesn't regress.

Run this test before delivering any new version of the code.
"""

import sys
import subprocess
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Test configuration
TEST_VIDEO = "dp-any-scoa.mp4"
TEST_DURATION = 345  # 5:45 seconds
EXPECTED_OUTPUT = Path(__file__).parent / "benchmark" / "dp-any-scoa_first_5min_expected.txt"


def run_extraction(video_path: str, duration: float) -> str:
    """Run dialogue extraction and return output."""
    result = subprocess.run(
        [sys.executable, "extract_dialogue.py", video_path, str(duration)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    # Read the generated output file
    output_file = PROJECT_ROOT / f"{Path(video_path).stem}_dialogue.txt"
    if output_file.exists():
        return output_file.read_text()
    else:
        raise RuntimeError(f"Output file not created: {output_file}\nstderr: {result.stderr}")


def test_benchmark():
    """Test that extraction output matches expected benchmark."""
    video_path = PROJECT_ROOT / TEST_VIDEO

    if not video_path.exists():
        print(f"SKIP: Test video not found: {video_path}")
        print("       Place dp-any-scoa.mp4 in project root to run this test.")
        return True

    if not EXPECTED_OUTPUT.exists():
        print(f"SKIP: Expected output not found: {EXPECTED_OUTPUT}")
        return True

    print(f"Running extraction on {TEST_VIDEO} ({TEST_DURATION}s)...")
    actual = run_extraction(TEST_VIDEO, TEST_DURATION)
    expected = EXPECTED_OUTPUT.read_text()

    if actual == expected:
        print("PASS: Output matches expected benchmark")
        return True
    else:
        print("FAIL: Output differs from expected benchmark")
        print()

        # Show diff
        actual_lines = actual.splitlines()
        expected_lines = expected.splitlines()

        print(f"Expected {len(expected_lines)} lines, got {len(actual_lines)} lines")
        print()

        # Find first difference
        for i, (exp, act) in enumerate(zip(expected_lines, actual_lines)):
            if exp != act:
                print(f"First difference at line {i + 1}:")
                print(f"  Expected: {repr(exp)}")
                print(f"  Actual:   {repr(act)}")
                break
        else:
            if len(actual_lines) != len(expected_lines):
                print(f"Line count mismatch at line {min(len(actual_lines), len(expected_lines)) + 1}")

        return False


if __name__ == "__main__":
    success = test_benchmark()
    sys.exit(0 if success else 1)
