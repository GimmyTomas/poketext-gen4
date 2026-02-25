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
ENGLISH_VIDEO = "dp-any-scoa.mp4"
ENGLISH_EXPECTED = Path(__file__).parent / "benchmark" / "dp-any-scoa_first_expected.txt"

ITALIAN_VIDEO = "dp-any-gimmy.mp4"
ITALIAN_EXPECTED = Path(__file__).parent / "benchmark" / "dp-any-gimmy_expected.txt"

HGSS_VIDEO = "hgss-gless-werster.mp4"
HGSS_EXPECTED_FIRST_MIN = Path(__file__).parent / "benchmark" / "hgss-gless-werster_expected_first_min.txt"

# Maximum allowed character differences (complete match with small tolerance)
MAX_DIFF_CHARS = 5


def run_extraction(video_path: str, start: float = None, end: float = None) -> str:
    """Run dialogue extraction and return output."""
    cmd = [sys.executable, "extract_dialogue.py", video_path]
    if start is not None and end is not None:
        cmd.extend([str(start), str(end)])
    elif end is not None:
        cmd.append(str(end))

    result = subprocess.run(
        cmd,
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


def count_differences(actual: str, expected: str) -> tuple[int, list]:
    """Count character differences between two strings.

    Returns:
        (diff_count, mismatches) where mismatches is a list of mismatch details
    """
    min_len = min(len(actual), len(expected))
    mismatches = []

    for i in range(min_len):
        if actual[i] != expected[i]:
            start = max(0, i - 20)
            end = min(min_len, i + 20)
            mismatches.append({
                'position': i,
                'expected_char': repr(expected[i]),
                'actual_char': repr(actual[i]),
                'expected_context': expected[start:end],
                'actual_context': actual[start:end],
            })

    # Count length difference as additional mismatches
    length_diff = abs(len(actual) - len(expected))
    diff_count = len(mismatches) + length_diff

    return diff_count, mismatches


def test_video(video_path: str, expected_path: Path, video_name: str,
               start: float = None, end: float = None,
               prefix_match: bool = False) -> bool:
    """Test a video extraction against expected output.

    Args:
        video_path: Path to video file
        expected_path: Path to expected output file
        video_name: Display name for the video
        start: Start time in seconds
        end: End time in seconds
        prefix_match: If True, only compare against the prefix of expected output
                      (for quick tests that extract partial videos)

    Returns True if test passes (diff <= MAX_DIFF_CHARS).
    """
    if not (PROJECT_ROOT / video_path).exists():
        print(f"SKIP: Video not found: {video_path}")
        return True

    if not expected_path.exists():
        print(f"SKIP: Expected output not found: {expected_path}")
        return True

    time_desc = ""
    if start is not None and end is not None:
        time_desc = f" ({start}s-{end}s)"
    elif end is not None:
        time_desc = f" (first {end}s)"
    else:
        time_desc = " (entire video)"

    print(f"Testing {video_name}{time_desc}...")
    actual = run_extraction(video_path, start, end)
    expected = expected_path.read_text()

    if prefix_match:
        # For partial video tests, only compare the actual output length
        # against the same-length prefix of the expected output
        expected = expected[:len(actual)]
        print(f"  (prefix match: comparing {len(actual)} chars)")

    diff_count, mismatches = count_differences(actual, expected)

    if diff_count == 0:
        print(f"PASS: Perfect match")
        return True
    elif diff_count <= MAX_DIFF_CHARS:
        print(f"PASS: {diff_count} character difference(s) (max allowed: {MAX_DIFF_CHARS})")
        return True
    else:
        print(f"FAIL: {diff_count} character differences (max allowed: {MAX_DIFF_CHARS})")
        print()

        # Report first few mismatches
        for i, m in enumerate(mismatches[:10]):
            print(f"  #{i+1} at pos {m['position']}: expected {m['expected_char']}, got {m['actual_char']}")
            print(f"      ...{m['expected_context']}...")
            print(f"      ...{m['actual_context']}...")
            print()

        if len(mismatches) > 10:
            print(f"  ... and {len(mismatches) - 10} more character mismatches")

        len_diff = abs(len(actual) - len(expected))
        if len_diff > 0:
            print(f"  Length difference: {len_diff} chars (expected {len(expected)}, got {len(actual)})")

        return False


def test_quick():
    """Quick tests on short video segments for fast iteration during development."""
    print("=== QUICK TESTS (short segments) ===\n")

    all_passed = True

    # Test a few specific segments known to have tricky cases
    segments = [
        # (video, start, end, description)
        (ITALIAN_VIDEO, 165, 175, "Pum!!! segment"),
        (ITALIAN_VIDEO, 365, 380, "... and Mmm... segment"),
        (ITALIAN_VIDEO, 405, 415, "Quote segment"),
        (ITALIAN_VIDEO, 535, 555, "Shop/pocket segment"),
        (ENGLISH_VIDEO, 280, 300, "Look! Poké Balls segment"),
    ]

    for video, start, end, desc in segments:
        video_path = PROJECT_ROOT / video
        if not video_path.exists():
            print(f"SKIP: {desc} - video not found")
            continue

        print(f"Testing {desc} ({video} {start}s-{end}s)...")
        try:
            output = run_extraction(video, start, end)
            lines = [l for l in output.strip().split('\n') if l]
            print(f"  OK: Found {len(lines)} lines of dialogue")

            # Check for common issues
            if "'''" in output or '"""' in output:
                print(f"  WARNING: Possible garbage quotes detected")
                all_passed = False
            if "☃" in output:
                print(f"  WARNING: Snowman symbols detected (false positive)")
                all_passed = False
        except Exception as e:
            print(f"  ERROR: {e}")
            all_passed = False
        print()

    return all_passed


def test_full():
    """Full benchmark tests on complete videos."""
    print("=== FULL BENCHMARK TESTS ===\n")

    success1 = test_video(ENGLISH_VIDEO, ENGLISH_EXPECTED, "English (dp-any-scoa)")
    print()

    success2 = test_video(ITALIAN_VIDEO, ITALIAN_EXPECTED, "Italian (dp-any-gimmy)")
    print()

    # HGSS: only first 60s of expected output exists
    success3 = test_video(
        HGSS_VIDEO, HGSS_EXPECTED_FIRST_MIN, "HGSS (hgss-gless-werster)",
        end=60
    )
    print()

    return success1 and success2 and success3


def test_fast(duration: float = 60):
    """Fast benchmark tests on first N seconds of each video.

    Compares extracted output against the prefix of expected output.
    Much faster than full tests while still catching regressions.
    """
    print(f"=== FAST BENCHMARK TESTS (first {duration}s) ===\n")

    success1 = test_video(
        ENGLISH_VIDEO, ENGLISH_EXPECTED, "English (dp-any-scoa)",
        end=duration, prefix_match=True
    )
    print()

    success2 = test_video(
        ITALIAN_VIDEO, ITALIAN_EXPECTED, "Italian (dp-any-gimmy)",
        end=duration, prefix_match=True
    )
    print()

    success3 = test_video(
        HGSS_VIDEO, HGSS_EXPECTED_FIRST_MIN, "HGSS (hgss-gless-werster)",
        end=min(duration, 60)
    )
    print()

    return success1 and success2 and success3


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick segment tests for specific edge cases
        success = test_quick()
    elif len(sys.argv) > 1 and sys.argv[1] == "--fast":
        # Fast benchmark on first 60s of videos
        duration = float(sys.argv[2]) if len(sys.argv) > 2 else 60
        success = test_fast(duration)
    else:
        # Full benchmark tests
        success = test_full()

    sys.exit(0 if success else 1)
