# Poketext Gen4 - Development Notes

## Phase 2 Complete

HeartGold/SoulSilver support added alongside existing Diamond/Pearl support.

### HGSS-Specific Issues Resolved

1. **HGSS textbox detection**: HGSS has wider frame borders that get blended when scaling, requiring looser strip tolerance (20% vs 2% for DP)
2. **Pokegear phone calls**: White text on blue/black gradient background. Detected via saturated blue pixel analysis at y=150 and dark strip checks at y=168/183. Text is inverted before OCR.
3. **Pokegear "Click!" filtering**: "Click! ...... ......" is instant text from Pokegear, filtered in garbage detection
4. **Pokegear scroll animation**: Dark background causes garbled OCR during scroll frames. Added in_scroll_anim flag to skip mid-scroll garbage frames.
5. **HGSS text region**: Text starts at x=8 (wider than DP's x=14), with padding added for template matching at screen edges
6. **Cutscene false positives**: HGSS cutscenes can have bright content in the center strip that mimics a textbox. Added outer strip check (left x=20-80, right x=176-236) to verify the full textbox width is white.
7. **Garbage filter improvements**: Added check for Pokedollar symbol not followed by digit, emoji characters (outside BMP), and improved short text heuristics

## Phase 1 Complete

All initial features implemented and working for Diamond/Pearl with Western languages.

### Issues Resolved

1. **Line2 spacing**: Second lines vertically aligned with line1 (no indent)
2. **Scrolling text format**: Outputs as separate lines, not concatenated
3. **1 vs l confusion**: Adjusted DARK_THRESHOLD to 130
4. **Instant text detection**: Tracks text growth patterns to exclude instant text
5. **Big text (Pum!!!, Thud!!!)**: 2x vertically stretched template matching
6. **Legacy code**: Moved to `legacy-code/` folder

## Text Detection Rules

### Slow Text vs Instant Text
- **Slow text**: Text that appears 1-3 characters per frame
- **Instant text**: Text that appears all at once (e.g., "Che nome scegli?")
- We only extract **slow text** for speedrun timing purposes
- Detection method: Track text length changes across frames
  - Slow text: incremental growth (1-4 chars/frame)
  - Instant text: large initial jump (10+ chars), then no change

### Scrolling Text
- Some textboxes scroll upwards instead of clearing
- Example: "Alcuni di noi si coalizzano..." scrolls up, "con essi un profondo legame." appears below
- Detection: When line2 content appears as line1, it's a scroll
- Output: Each line printed separately (not concatenated)

### Big Text
- Some text is 2x vertically stretched (e.g., "Pum!!!", "Thud!!")
- Same font, just stretched vertically by factor of 2
- Triggers SCROLLING state because text extends into detection strip area
- Uses stretched templates (15px → 30px) with lower threshold (0.50)

### Spaces at Line Start
- The game does NOT print leading spaces on new lines
- OCR strips leading/trailing spaces from recognized text
- Lines are vertically aligned in the game

## Technical Parameters

### OCR Thresholds
```python
MATCH_THRESHOLD = 0.90   # Normal text
BIG_TEXT_THRESHOLD = 0.50  # Big text (fuzzier due to stretching)
DARK_THRESHOLD = 130     # Column must have pixels darker than this
SPACE_THRESHOLD = 245    # White space detection
```

### Coordinates (DS native 256x192)
```python
TEXT_X = 14
TEXT_Y_LINE1 = 152
TEXT_Y_LINE2 = 168
CHAR_HEIGHT = 15
BIG_CHAR_HEIGHT = 30
```

## Debug Tips

- Save frames with `cv2.imwrite()` to inspect visually
- Check textbox state at specific timestamps
- Verify template matching scores for problem characters
- Look at actual video frames to verify issues

## Character Counting Rules (for future)

1. Count only slow text characters
2. Don't count spaces at line start (they're artifacts)
3. Scrolled text should only be counted once
4. Instant text should be excluded from count
