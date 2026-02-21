# Poketext Gen4

## Project Overview

A tool to extract text from Pokémon Generation 4 speedrun videos (Diamond, Pearl, Platinum, HeartGold, SoulSilver). The primary goal is to count characters for speedrun optimization and language comparison analysis.

## Key Concepts

### Text Types
- **Slow text**: Printed at 1 character per frame (60fps). This is what we extract.
- **Instant text**: Printed all at once. We ignore this.

### Technical Details
- DS native resolution: 256x192 per screen
- Videos may be recorded at various resolutions (integer or non-integer multiples)
- Recordings may be 30fps or 60fps (game runs at 60fps, overworld updates at 30fps)
- Screen layout varies: top screen can be on left or right, usually larger

### Text Detection Strategy
1. **Textbox detection**: Identify when a dialogue textbox is open
2. **Animation verification**: Confirm text is appearing character-by-character
3. **Character recognition**: Custom template matching using the game's fixed font

### Supported Games
- Pokémon Diamond (DS)
- Pokémon Pearl (DS)
- Pokémon Platinum (DS)
- Pokémon HeartGold (DS)
- Pokémon SoulSilver (DS)

### Supported Languages
- Western: English, Italian, French, German, Spanish
- Japanese (different font/character set)

## Project Structure

```
src/
├── main.py              # Entry point
├── video.py             # Video frame extraction
├── screen.py            # Screen layout detection
├── textbox.py           # Textbox state detection
├── ocr.py               # Custom character recognition
└── games/               # Game-specific configurations
    ├── base.py
    ├── diamond_pearl.py
    ├── platinum.py
    └── hgss.py
```

## Output Format
- Full extracted text
- Total character count at the end

## Legacy Code
The `poketext-gen4/` directory contains the original C++ implementation using FFmpeg and Tesseract. It works but has accuracy issues with OCR. The new Python implementation uses custom template matching instead.

## Development Notes
- Use OpenCV for video reading and image processing
- Template matching for OCR (game uses fixed fonts)
- Auto-detect screen layout (top screen is larger)
- Handle both 30fps and 60fps recordings
- Handle various recording resolutions (sharp and blurry pixels)
