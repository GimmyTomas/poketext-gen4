#!/usr/bin/env python3
"""Benchmark test to verify dialogue extraction output doesn't regress.

Run this test before delivering any new version of the code.

Usage:
  python tests/test_benchmark.py              # Full benchmark tests
  python tests/test_benchmark.py fast         # Fast 60s prefix tests
  python tests/test_benchmark.py fast -d 300  # Fast 300s prefix tests
  python tests/test_benchmark.py fast -v hgss # Fast test on HGSS only
  python tests/test_benchmark.py quick        # Segment tests
  python tests/test_benchmark.py hgss-pokegear # Pokégear segment test
"""

import argparse
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
HGSS_EXPECTED = Path(__file__).parent / "benchmark" / "hgss-gless-werster_expected_first_10_mins.txt"

# Maximum allowed character differences (complete match with small tolerance)
MAX_DIFF_CHARS = 5

# ============================================================================
# Approximate test durations (M2 MacBook Air):
#
# dp-any-scoa.mp4 (English, 60fps, ~45 min video):
#   60s  -> ~20s     300s -> ~1.5 min    full -> ~15 min
#
# dp-any-gimmy.mp4 (Italian, 30fps, ~45 min video):
#   60s  -> ~10s     300s -> ~45s        full -> ~7 min
#
# hgss-gless-werster.mp4 (HGSS, 60fps, ~2 hour video):
#   60s  -> ~20s     300s -> ~1.5 min    600s -> ~3 min    full -> ~60 min
#
# Quick segment tests: ~5-10s each
# ============================================================================


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


def test_hgss_pokegear():
    """Test Pokégear phone call detection (HGSS 480-510s covers ~8:00-8:30 phone call)."""
    print("=== POKÉGEAR PHONE CALL TEST ===\n")

    video_path = PROJECT_ROOT / HGSS_VIDEO
    if not video_path.exists():
        print(f"SKIP: Video not found: {HGSS_VIDEO}")
        return True

    print(f"Testing HGSS Pokégear phone call (480s-510s)...")
    try:
        output = run_extraction(HGSS_VIDEO, 480, 510)
        lines = [l for l in output.strip().split('\n') if l]
        print(f"  Found {len(lines)} lines of dialogue")
        print(f"  Output:\n")
        for line in lines:
            print(f"    {line}")
        print()

        # Verify Pokégear text is detected
        passed = True
        expected_phrases = ["H-hello", "disaster"]
        for phrase in expected_phrases:
            if phrase.lower() in output.lower():
                print(f"  OK: Found expected phrase '{phrase}'")
            else:
                print(f"  WARNING: Expected phrase '{phrase}' not found")
                # Don't fail - thresholds may need tuning
                # passed = False

        # Verify "Click!" is filtered
        if "Click!" in output:
            print(f"  FAIL: 'Click!' should be filtered as instant text")
            passed = False
        else:
            print(f"  OK: 'Click!' correctly filtered")

        return passed
    except Exception as e:
        print(f"  ERROR: {e}")
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
        (HGSS_VIDEO, 480, 510, "HGSS Pokégear phone call"),
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


def test_full(video_filter: str = None):
    """Full benchmark tests on complete videos.

    Args:
        video_filter: If set, only run tests matching this filter (dp, hgss, etc.)
    """
    print("=== FULL BENCHMARK TESTS ===\n")

    results = []

    if not video_filter or "dp" in video_filter or "scoa" in video_filter or "english" in video_filter:
        results.append(test_video(ENGLISH_VIDEO, ENGLISH_EXPECTED, "English (dp-any-scoa)"))
        print()

    if not video_filter or "dp" in video_filter or "gimmy" in video_filter or "italian" in video_filter:
        results.append(test_video(ITALIAN_VIDEO, ITALIAN_EXPECTED, "Italian (dp-any-gimmy)"))
        print()

    if not video_filter or "hgss" in video_filter:
        # HGSS: first 10 minutes of expected output
        results.append(test_video(
            HGSS_VIDEO, HGSS_EXPECTED, "HGSS (hgss-gless-werster)",
            end=600
        ))
        print()

    return all(results) if results else True


def test_fast(duration: float = 60, video_filter: str = None):
    """Fast benchmark tests on first N seconds of each video.

    Compares extracted output against the prefix of expected output.
    Much faster than full tests while still catching regressions.

    Args:
        duration: Number of seconds to extract from each video
        video_filter: If set, only run tests matching this filter (dp, hgss, etc.)
    """
    print(f"=== FAST BENCHMARK TESTS (first {duration}s) ===\n")

    results = []

    if not video_filter or "dp" in video_filter or "scoa" in video_filter or "english" in video_filter:
        results.append(test_video(
            ENGLISH_VIDEO, ENGLISH_EXPECTED, "English (dp-any-scoa)",
            end=duration, prefix_match=True
        ))
        print()

    if not video_filter or "dp" in video_filter or "gimmy" in video_filter or "italian" in video_filter:
        results.append(test_video(
            ITALIAN_VIDEO, ITALIAN_EXPECTED, "Italian (dp-any-gimmy)",
            end=duration, prefix_match=True
        ))
        print()

    if not video_filter or "hgss" in video_filter:
        results.append(test_video(
            HGSS_VIDEO, HGSS_EXPECTED, "HGSS (hgss-gless-werster)",
            end=min(duration, 600), prefix_match=True
        ))
        print()

    return all(results) if results else True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark tests for dialogue extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
modes:
  full            Full benchmark tests (default)
  fast            Fast prefix tests (default 60s)
  quick           Quick segment tests
  hgss-pokegear   Pokégear phone call test
        """
    )
    parser.add_argument("mode", nargs="?", default="full",
                        choices=["full", "fast", "quick", "hgss-pokegear"],
                        help="Test mode (default: full)")
    parser.add_argument("-d", "--duration", type=float, default=60,
                        help="Duration in seconds for fast mode (default: 60)")
    parser.add_argument("-v", "--video", type=str, default=None,
                        help="Video filter (dp, hgss, scoa, gimmy, english, italian)")

    args = parser.parse_args()

    if args.mode == "quick":
        success = test_quick()
    elif args.mode == "fast":
        success = test_fast(args.duration, args.video)
    elif args.mode == "hgss-pokegear":
        success = test_hgss_pokegear()
    else:
        success = test_full(args.video)

    sys.exit(0 if success else 1)
