# Pokétext Gen4

## Project Overview

Extract "slow text" (1 char/frame at 60fps) from Pokémon Gen 4 speedrun videos for character counting and speedrun optimization.

## Current Status: Phase 2 Complete

Diamond/Pearl and HeartGold/SoulSilver dialogue extraction works for full-length speedrun videos.

### Completed:
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
- [x] Blue text handling (item names, Coupon text)
- [x] Pocket icon detection (symbols)
- [x] Full video processing (entire speedrun videos)
- [x] Garbage text filtering (transition artifacts)
- [x] HGSS support (game-specific textbox detection, wider text regions)
- [x] HGSS Pokégear phone call detection (white-on-dark text)
- [x] HGSS cutscene false positive rejection (outer strip check)

### Planned (Future Phases):
- [ ] Character counting with timing analysis
- [ ] Platinum game support
- [ ] Japanese character templates
- [ ] Battle text detection
- [ ] Menu text detection

## Technical Details

### Text Region Coordinates (DS native 256x192)
```python
# Diamond/Pearl
TEXT_X = 14           # X start of text
TEXT_WIDTH = 232      # Text region width
TEXT_Y_LINE1 = 152    # Y start of first line
TEXT_Y_LINE2 = 168    # Y start of second line
CHAR_HEIGHT = 15      # Character height in pixels
BIG_CHAR_HEIGHT = 30  # For 2x vertically stretched text

# HGSS
TEXT_X = 8            # Wider text region for HGSS
TEXT_WIDTH = 248      # Full screen width
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
- `src/textbox.py` - Textbox state detection (DP + HGSS)
- `src/ocr.py` - Template matching OCR (normal + big text)
- `src/games/` - Game-specific configuration
- `templates/western/` - 122 character template images
- `legacy-code/` - Original C++ implementation

### Sample Videos
- `dp-any-gimmy.mp4` - Italian Diamond speedrun, 854x480 @ 30fps
- `dp-any-scoa.mp4` - English Diamond speedrun, 60fps
- `hgss-gless-werster.mp4` - English HeartGold speedrun, 60fps

## Usage

```bash
# Extract entire video
python extract_dialogue.py dp-any-gimmy.mp4

# Extract first 3 minutes
python extract_dialogue.py dp-any-gimmy.mp4 180

# Extract segment from 1:00 to 2:00
python extract_dialogue.py dp-any-gimmy.mp4 60 120
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

### Pokégear Phone Calls (HGSS)
- White text on blue/black gradient background
- Detected via blue pixel analysis at y=150, dark check at y=168/183
- Text is inverted before OCR (white-on-dark -> dark-on-white)

### Output Format
- Line1 and Line2 vertically aligned (no indent)
- Blank line between dialogue entries
- No timestamps

## Testing

Benchmark tests are available for regression testing:

```bash
# Full benchmark (compares entire video output)
python tests/test_benchmark.py

# Fast prefix tests (first 60s)
python tests/test_benchmark.py fast

# Fast with custom duration
python tests/test_benchmark.py fast -d 300

# Quick segment tests (specific tricky segments)
python tests/test_benchmark.py quick

# Filter by game
python tests/test_benchmark.py fast -v hgss

# Pokégear phone call test
python tests/test_benchmark.py hgss-pokegear
```

### Benchmark Files
- `tests/benchmark/dp-any-scoa_expected.txt` - English DP expected output
- `tests/benchmark/dp-any-gimmy_expected.txt` - Italian DP expected output
- `tests/benchmark/hgss-gless-werster_expected_first_17_mins.txt` - HGSS expected output (first 17 minutes)
- `tests/test_benchmark.py` - Benchmark test script
