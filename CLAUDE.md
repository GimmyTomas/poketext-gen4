# Poketext Gen4

## Project Overview

Extract "slow text" (1 char/frame at 60fps) from Pokémon Gen 4 speedrun videos for character counting and speedrun optimization.

## Current Status: 74 Templates Extracted with Manual Boundaries

**74 character templates** extracted with manually verified pixel boundaries. All templates have good quality (variance > 500, dark pixels present).

### Completed:
- [x] Video reading with OpenCV
- [x] Screen layout auto-detection (top screen position, scale factor)
- [x] Textbox state detection (open/closed/scrolling)
- [x] Text region extraction (normalized to DS 256x192)
- [x] Manual character template extraction with precise boundaries
- [x] 74 Western character templates (verified quality)
- [x] Basic template matching OCR implementation (`src/ocr.py`)

### Available Characters:
```
Uppercase: A B C D E F G H I J K L M O P Q R T U V W X Y Z
Lowercase: a b c d e f g h i j k l m n o p r s t u v w x y
Digits:    0 1 2 3 4 5 6 7 8 9
Punct:     ! " ' ( ) , - . ; ?
Accented:  à è é ì ò ù
```

### Missing Characters (5):
- `:` (colon) - not in available screenshots
- `q`, `z` (lowercase) - not in available screenshots
- `N`, `S` (uppercase) - not in available screenshots

### Next Steps:
1. **Test OCR on screenshots** - verify template matching works
2. **Test on video** - verify OCR works on actual video frames
3. **Add missing characters** if needed from additional screenshots

## Technical Details

### Text Region Coordinates (DS native 256x192)
```python
TEXT_X = 14       # X start of text
TEXT_Y_LINE1 = 155  # Y start of first line (VERIFIED)
TEXT_Y_LINE2 = 171  # Y start of second line (155 + 16)
CHAR_HEIGHT = 14    # Character height in pixels
```

### Character Width Table
Located in `tools/extract_templates.py` - CharacterWidths class.
Most characters: 5 pixels. Narrow (i, l, !, .): 3 pixels. Wide (m, w, O): 6-7 pixels.

### Key Files
- `src/video.py` - Video frame extraction
- `src/screen.py` - Screen layout detection
- `src/textbox.py` - Textbox state detection
- `src/ocr.py` - Template matching OCR with sliding window
- `tools/extract_templates.py` - Template extraction from screenshots
- `templates/western/` - 74 character template images (14x3-9 px each)
- `tools/extract_complete.py` - Manual extraction with verified boundaries

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
