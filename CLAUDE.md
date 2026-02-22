# Poketext Gen4

## Project Overview

Extract "slow text" (1 char/frame at 60fps) from Pokémon Gen 4 speedrun videos for character counting and speedrun optimization.

## Current Status: Phase 1 Complete

First working version for Diamond/Pearl with Western languages. All core features implemented and tested.

### Completed (Phase 1):
- [x] Video reading with OpenCV
- [x] Screen layout auto-detection (top screen position, scale factor)
- [x] Textbox state detection (open/closed/scrolling)
- [x] Text region extraction (normalized to DS 256x192)
- [x] 122 Western character templates (A-Z, a-z, 0-9, punctuation, accented, symbols)
- [x] Template matching OCR with sliding window
- [x] Slow vs instant text detection (via text growth patterns)
- [x] Scrolling text handling (outputs as separate lines)
- [x] Big text support (2x vertically stretched, e.g., "Pum!!!", "Thud!!")
- [x] Full dialogue extraction pipeline (`extract_dialogue.py`)

### Planned (Future Phases):
- [ ] Character counting with timing analysis
- [ ] Platinum / HG/SS game support
- [ ] Japanese character templates
- [ ] Battle text detection
- [ ] Menu text detection
- [ ] Full video processing (beyond first few minutes)

## Technical Details

### Text Region Coordinates (DS native 256x192)
```python
TEXT_X = 14           # X start of text
TEXT_Y_LINE1 = 152    # Y start of first line
TEXT_Y_LINE2 = 168    # Y start of second line
CHAR_HEIGHT = 15      # Character height in pixels
BIG_CHAR_HEIGHT = 30  # For 2x vertically stretched text
```

### OCR Parameters
```python
MATCH_THRESHOLD = 0.90      # Template matching threshold
DARK_THRESHOLD = 130        # Dark pixel detection for character start
SPACE_THRESHOLD = 245       # White space detection
BIG_TEXT_THRESHOLD = 0.50   # Lower threshold for big text (2x stretched)
BIG_TEXT_STRETCH = 2.0      # Vertical stretch factor for big text
```

### Key Files
- `extract_dialogue.py` - Main dialogue extraction script
- `src/video.py` - Video frame extraction
- `src/screen.py` - Screen layout detection
- `src/textbox.py` - Textbox state detection
- `src/ocr.py` - Template matching OCR (normal + big text)
- `templates/western/` - 122 character template images
- `legacy-code/` - Original C++ implementation

### Sample Videos
- `dp-any-gimmy.mp4` - Italian Diamond speedrun, 854x480 @ 30fps
- `dp-any-scoa.mp4` - English Diamond speedrun, 60fps

## Usage

```bash
# Extract dialogue from first 3 minutes
python extract_dialogue.py dp-any-gimmy.mp4 180

# Extract entire video
python extract_dialogue.py dp-any-gimmy.mp4
```

## Text Detection Rules

### Slow Text vs Instant Text
- **Slow text**: Appears 1-3 characters per frame (extracted)
- **Instant text**: Appears all at once (excluded from output)
- Detection: Track text growth patterns across frames

### Scrolling Text
- When text scrolls up, outputs each line separately
- Avoids double-counting scrolled text

### Big Text
- Some text is 2x vertically stretched (e.g., "Pum!!!", "Thud!!")
- Uses stretched templates with lower matching threshold
- Triggers SCROLLING state due to extending into detection strip

### Output Format
- Line1 and Line2 vertically aligned (no indent)
- Blank line between dialogue entries
- No timestamps

## Testing Requirements

**IMPORTANT: Before delivering any code changes, run the benchmark test:**

```bash
python tests/test_benchmark.py
```

This test verifies that dialogue extraction output matches the expected benchmark for the first 5:45 of `dp-any-scoa.mp4`. The test must pass before committing changes.

### Benchmark Files
- `tests/benchmark/dp-any-scoa_first_5min_expected.txt` - Expected output (111 dialogues)
- `tests/test_benchmark.py` - Benchmark test script
