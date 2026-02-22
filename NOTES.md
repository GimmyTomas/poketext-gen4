# Poketext Gen4 - Development Notes

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
