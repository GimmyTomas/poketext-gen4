# Poketext Gen4

Extract dialogue text from Pokémon Generation 4 speedrun videos. Designed for speedrun optimization and cross-language text length analysis.

## Purpose

In Gen 4 Pokémon games, text is printed at 1 character per frame (at 60fps). This makes text length a significant factor in speedrun times. This tool extracts all "slow text" (character-by-character text) from video recordings, enabling:

- Character counting for speedrun route optimization
- Cross-language text length comparison
- Full dialogue extraction for documentation

## Status: Phase 1 Complete

The first working version is complete for Diamond/Pearl with Western languages (English, Italian, etc.).

### Working Features
- Automatic screen layout detection (handles various video resolutions)
- Textbox state detection (open, closed, scrolling)
- Template-based OCR with 122 character templates
- Slow text vs instant text detection
- Scrolling text handling
- Big text support (2x vertically stretched text like "Pum!!!", "Thud!!")
- Full dialogue extraction pipeline

### Tested On
- Italian Diamond speedrun (30fps)
- English Diamond speedrun (60fps)

## Supported Games

- Pokémon Diamond / Pearl (tested)
- Pokémon Platinum (planned)
- Pokémon HeartGold / SoulSilver (planned)

## Supported Languages

Currently: English, Italian (and other Western languages sharing the same font)

Planned: French, German, Spanish, Japanese

## Installation

```bash
pip install opencv-python numpy
```

Requires Python 3.9+.

## Usage

```bash
# Extract dialogue from first 3 minutes
python extract_dialogue.py video.mp4 180

# Extract entire video
python extract_dialogue.py video.mp4

# Output is saved to <video_name>_dialogue.txt
```

## How It Works

1. **Screen Detection**: Auto-detects the DS top screen position and scale factor
2. **Textbox Detection**: Identifies when dialogue textboxes are open using pixel analysis
3. **Text Animation Detection**: Tracks text growth to distinguish slow text (1-3 chars/frame) from instant text
4. **Character Recognition**: Custom template matching using extracted game font templates
5. **Big Text Detection**: 2x vertically stretched templates for special text effects

## Project Structure

```
extract_dialogue.py     # Main extraction script
src/
├── video.py           # Video frame extraction
├── screen.py          # Screen layout detection
├── textbox.py         # Textbox state detection
└── ocr.py             # Template matching OCR
templates/
└── western/           # 97 character template images
legacy-code/           # Original C++ implementation
```

## Output Format

```
Ciao, felice di conoscerti!

Ti do il benvenuto nel mondo dei
Pokémon!

Pum!!!

C: Che succede?!?
```

- Each dialogue entry separated by blank lines
- Line1 and Line2 vertically aligned (no indent)
- No timestamps (for now)

## Contributing

See `NOTES.md` for development notes and technical details.
See `CLAUDE.md` for AI assistant context.
