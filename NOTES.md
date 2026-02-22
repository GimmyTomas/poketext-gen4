# Poketext Gen4 - Development Notes

## Text Detection Rules

### Slow Text vs Instant Text
- **Slow text**: Text that appears one character per frame (at 60fps, or every 2 frames at 30fps video)
- **Instant text**: Text that appears all at once (e.g., "Che nome scegli?", "Che nome scegli per il tuo amico?")
- We only want to count **slow text** for speedrun timing purposes
- **IMPORTANT**: Instant text does NOT have the continue marker. The marker detection must be working correctly.

### Detecting Slow Text
- At the end of slow text textboxes, there is a **small marker at the bottom right** that tells the player to press a button to continue
- This marker can help distinguish slow text from instant text
- **Caveat**: At 30fps recording, the marker might not appear if the player presses the button very fast
- Instant text like "Che nome scegli?" does NOT have this marker

### Scrolling Text
- Some textboxes don't reset the text, but **scroll upwards** to make space for a new line
- Example: "Alcuni di noi si coalizzano con i Pokémon per sfidare altre persone, stabilendo" scrolls up, then "con essi un profondo legame." appears on line 2
- The line "per sfidare altre persone, stabilendo" should only be counted **once**, not twice
- Detection: When line1 content moves to become line2, and new text appears on line1, it's a scroll
- **Output format**: Scrolling text should still be printed on TWO lines, not merged into one long line

### Spaces at Line Start
- The game does **NOT** spend a frame to print a space at the start of new lines
- OCR should NOT add spaces at the start of lines
- Spaces should not count toward character count when they're just line-start artifacts

## Special Text Types

### Big Text
- Some text appears as "big text" (vertically stretched)
- Italian example: "Pum!!!" around 2:46
- English example: "Thud!!!"
- The big text is NOT on a dark background - it's a normal textbox
- Need to look at actual video frames to understand the rendering

## Output Format
- Do NOT print timestamps (at least for now)
- Print each dialogue on separate lines
- Line1 first, then Line2 indented

## Known Issues Fixed
- [~2:25] "Mamma: G!" - now detected
- [~2:49] "Oh, ciao, G!" - now detected
- Pokedollar (₽) template added and working
- '1' vs 'l' confusion: FIXED - "₽1 milione!" now correctly recognized
- Instant text detection: FIXED - "Che nome scegli?" no longer appears (detected via text growth pattern)
- Scrolling text: FIXED - "Alcuni di noi..." now correctly shows both lines
- Timestamps removed from output
- Leading spaces on line2 fixed (using .strip())

## Completed Fixes

1. **Line2 spacing**: ✅ FIXED - Second lines no longer have leading spaces. Vertically aligned with line1.

2. **Scrolling text format**: ✅ FIXED - Now outputs as separate lines, not concatenated.

3. **1 vs l confusion**: ✅ FIXED - Adjusted DARK_THRESHOLD to 130 for proper character detection.

4. **Legacy code**: ✅ FIXED - Moved to "legacy-code" folder.

5. **Instant text detection**: ✅ FIXED - Tracks text growth patterns to exclude instant text.

## Pending/Investigating

1. **Big text (Pum!!!, Thud!!!)**: Code added to detect 2x vertically stretched text using `recognize_big_text()`. The big text doesn't appear in the first 3 minutes of dialogue - it may be a sound effect that appears outside the textbox area later in the game.

## Character Counting Rules
1. Count only slow text characters
2. Don't count spaces at the start of lines (they're artifacts)
3. Scrolled text should only be counted once
4. Instant text should be excluded from count

## Debug Tips
- Always look at actual video frames to verify issues
- The OCR should be able to read what you can see in the frames
- Check marker presence by examining the bottom-right corner of textboxes
