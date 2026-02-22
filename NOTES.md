# Poketext Gen4 - Development Notes

## Text Detection Rules

### Slow Text vs Instant Text
- **Slow text**: Text that appears one character per frame (at 60fps, or every 2 frames at 30fps video)
- **Instant text**: Text that appears all at once (e.g., "Che nome scegli?", "Che nome scegli per il tuo amico?")
- We only want to count **slow text** for speedrun timing purposes

### Detecting Slow Text
- At the end of slow text textboxes, there is a **small marker at the bottom right** that tells the player to press a button to continue
- This marker can help distinguish slow text from instant text
- **Caveat**: At 30fps recording, the marker might not appear if the player presses the button very fast

### Scrolling Text
- Some textboxes don't reset the text, but **scroll upwards** to make space for a new line
- Example: "Alcuni di noi si coalizzano con i Pokémon per sfidare altre persone, stabilendo" scrolls up, then "con essi un profondo legame." appears on line 2
- The line "per sfidare altre persone, stabilendo" should only be counted **once**, not twice
- Detection: When line1 content moves to become line2, and new text appears on line1, it's a scroll

### Spaces at Line Start
- The game does **NOT** spend a frame to print a space at the start of new lines
- Current OCR adds a space at the start of line2 - this should be removed
- Spaces should not count toward character count when they're just line-start artifacts

## Special Text Types

### Big Text
- Some text appears as "big text" (vertically stretched)
- Example: "Pum!!!" around 2:46
- These are likely the same character templates but stretched vertically
- Need special handling to detect and read these

## Known Missed Textboxes (first 3 minutes)
- [~2:25] "Mamma: G!" - missed
- [~2:49] "Oh, ciao, G!" - missed

## Missing Templates
- **Currency symbol** (Pokémon Dollar/Pokédollar ₽): Appears in textbox at [2:50.83] "OK, G? Se arrivi tardi ti do una bella multa di 1 milione!"
- Need to extract this template from the video

## Character Counting Rules
1. Count only slow text characters
2. Don't count spaces at the start of lines (they're artifacts)
3. Scrolled text should only be counted once
4. Instant text should be excluded from count
