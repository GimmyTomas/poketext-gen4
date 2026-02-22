# Poketext Gen4

## Project Overview

Extract "slow text" (1 char/frame at 60fps) from Pokémon Gen 4 speedrun videos for character counting and speedrun optimization.

## Current Status: Dialogue Extraction Working

The system can now extract dialogue text from speedrun videos with high accuracy.

### Completed:
- [x] Video reading with OpenCV
- [x] Screen layout auto-detection (top screen position, scale factor)
- [x] Textbox state detection (open/closed/scrolling)
- [x] Text region extraction (normalized to DS 256x192)
- [x] 97 Western character templates (A-Z, a-z, 0-9, punctuation, accented)
- [x] Template matching OCR with sliding window
- [x] Slow vs instant text detection (via text growth patterns)
- [x] Scrolling text handling (outputs as separate lines)
- [x] Big text support (2x vertically stretched, e.g., "Pum!!!")
- [x] Full dialogue extraction pipeline (`extract_dialogue.py`)

### Output Files Generated:
- `dp-any-gimmy_dialogue.txt` - Italian Diamond speedrun (first 3 min)
- `dp-any-scoa_dialogue.txt` - English Diamond speedrun (first 3 min)

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
MATCH_THRESHOLD = 0.90   # Template matching threshold
DARK_THRESHOLD = 130     # Dark pixel detection for character start
SPACE_THRESHOLD = 245    # White space detection
```

### Key Files
- `extract_dialogue.py` - Main dialogue extraction script
- `src/video.py` - Video frame extraction
- `src/screen.py` - Screen layout detection
- `src/textbox.py` - Textbox state detection
- `src/ocr.py` - Template matching OCR (normal + big text)
- `templates/western/` - 97 character template images
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

## User Preferences
- Language: Python (with OpenCV)
- Primary goal: Character counting for speedrun optimization
- Support: Gen 4 games (D/P/Pt/HG/SS), Western languages
- Output: Text file with extracted dialogue (no timestamps)

## Text Detection Rules

### Slow Text vs Instant Text
- **Slow text**: Appears 1-3 characters per frame (extracted)
- **Instant text**: Appears all at once (excluded from output)
- Detection: Track text growth patterns across frames

### Scrolling Text
- When text scrolls up, outputs each line separately
- Avoids double-counting scrolled text

### Output Format
- Line1 and Line2 vertically aligned (no indent)
- Blank line between dialogue entries
- No timestamps
