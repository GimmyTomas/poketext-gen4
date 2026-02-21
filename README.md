# Poketext Gen4

Extract text from Pokémon Generation 4 speedrun videos. Designed for speedrun optimization and cross-language text length analysis.

## Purpose

In Gen 4 Pokémon games, text is printed at 1 character per frame (at 60fps). This makes text length a significant factor in speedrun times. This tool extracts all "slow text" (character-by-character text) from video recordings, enabling:

- Character counting for speedrun route optimization
- Cross-language text length comparison
- Full text extraction for documentation

## Supported Games

- Pokémon Diamond
- Pokémon Pearl
- Pokémon Platinum
- Pokémon HeartGold
- Pokémon SoulSilver

## Supported Languages

- English, Italian, French, German, Spanish
- Japanese

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.10+ and OpenCV.

## Usage

```bash
python -m src.main <video_path> [options]

Options:
  -o, --output PATH     Output file (default: stdout)
  -g, --game GAME       Game type: diamond_pearl, platinum, hgss
  -l, --language LANG   Language: en, it, fr, de, es, ja
  -v, --verbose         Show progress
```

## How It Works

1. **Screen Detection**: Auto-detects the DS screen layout in the video (top screen position and scale)
2. **Textbox Detection**: Identifies when dialogue textboxes are open
3. **Text Animation Detection**: Distinguishes "slow text" (1 char/frame) from instant text
4. **Character Recognition**: Custom template matching using the game's fixed font

## Project Structure

```
src/
├── main.py          # Entry point
├── video.py         # Video frame extraction
├── screen.py        # Screen layout detection
├── textbox.py       # Textbox state detection
├── ocr.py           # Custom character recognition
└── games/           # Game-specific configurations
```

## Status

Work in progress. The basic structure is in place; character template extraction and recognition are being implemented.

## Legacy

The `poketext-gen4/` directory contains an earlier C++ implementation using FFmpeg and Tesseract OCR.
