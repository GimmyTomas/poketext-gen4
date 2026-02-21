# Poketext Gen4

## Project Overview

Extract "slow text" (1 char/frame at 60fps) from Pokémon Gen 4 speedrun videos for character counting and speedrun optimization.

## Current Status: Template Extraction Complete

**97 character templates** extracted and ready for OCR implementation.

### Completed:
- [x] Video reading with OpenCV
- [x] Screen layout auto-detection (top screen position, scale factor)
- [x] Textbox state detection (open/closed/scrolling)
- [x] Text region extraction (normalized to DS 256x192)
- [x] Character template extraction tools
- [x] 97 Western character templates (A-Z, a-z, 0-9, punctuation, accented)

### Next Steps:
1. **Implement template matching OCR** in `src/ocr.py`
2. **Test on video** - run OCR on extracted text regions
3. **Detect slow vs instant text** - verify character-by-character appearance
4. **Output results** - text file with character count

## Technical Details

### Text Region Coordinates (DS native 256x192)
```python
TEXT_X = 14       # X start of text
TEXT_Y_LINE1 = 152  # Y start of first line
TEXT_Y_LINE2 = 168  # Y start of second line
CHAR_HEIGHT = 14    # Character height in pixels
```

### Character Width Table
Located in `tools/extract_templates.py` - CharacterWidths class.
Most characters: 5 pixels. Narrow (i, l, !, .): 3 pixels. Wide (m, w, O): 6-7 pixels.

### Key Files
- `src/video.py` - Video frame extraction
- `src/screen.py` - Screen layout detection
- `src/textbox.py` - Textbox state detection
- `src/ocr.py` - OCR (needs template matching implementation)
- `tools/extract_templates.py` - Template extraction from screenshots
- `templates/western/` - 97 character template images

### Test Scripts
- `test_video.py` - Test video reading and screen detection
- `test_textbox.py` - Find frames with open textboxes
- `test_ocr_region.py` - Extract and visualize text regions

### Sample Video
`dp-any-gimmy.mp4` - Italian Diamond speedrun, 854x480 @ 30fps, 2.5x scale

## User Preferences
- Language: Python (with OpenCV)
- Primary goal: Character counting for speedrun optimization
- Support: Gen 4 games (D/P/Pt/HG/SS), Western + Japanese languages
- Output: Text file with extracted text and character count

## Ideas for Future
- Template reconstruction for unknown/blurry characters
- Japanese character support (separate template set)
- Other Western language accented characters
