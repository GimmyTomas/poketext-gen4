# Poketext Gen4

Extract dialogue text from Pokemon Generation 4 speedrun videos for character counting and route optimization.

## What this does

In Gen 4 Pokemon games, dialogue text is printed at **1 character per frame** (60fps). That means every extra character costs ~16ms of real time. This tool watches a video recording of a speedrun, detects when dialogue textboxes appear, and extracts all the "slow text" that the game prints character by character.

Example output:

```
Ciao, felice di conoscerti!

Ti do il benvenuto nel mondo dei
Pokemon!

Pum!!!

C: Che succede?!?
```

Each dialogue entry is separated by a blank line. Only slow text is extracted -- instant text (menus, name entry prompts) is excluded.

## Supported games

| Game | Status |
|------|--------|
| Diamond / Pearl | Tested (Italian, English) |
| HeartGold / SoulSilver | Tested (English) |
| Platinum | Planned |

Western languages (English, Italian, French, German, Spanish) share the same font and should all work. Japanese support is planned.

## Getting started

### Requirements

- Python 3.9+
- A video file of a Gen 4 speedrun

### Install

```bash
pip install opencv-python numpy
```

### Run

```bash
# Extract entire video
python extract_dialogue.py dp-any-scoa.mp4

# Extract first 3 minutes
python extract_dialogue.py dp-any-scoa.mp4 180

# Extract from 1:00 to 2:00
python extract_dialogue.py dp-any-scoa.mp4 60 120
```

Output is saved to `<video_name>_dialogue.txt`.

The game is auto-detected from the filename: include `hgss`, `heartgold`, or `soulsilver` in the filename for HG/SS videos.

### Output format

- Each dialogue box produces one or two lines (line 1 and line 2)
- Scrolling dialogues (4+ lines) output each line separately
- Blank line between dialogue entries
- A summary of character count and frame cost is printed to the console

## How it works

1. **Screen detection** -- Auto-detects the DS top screen position and scale factor from the video resolution
2. **Textbox detection** -- Checks pixel strips to determine if a textbox is open, closed, or scrolling
3. **Text animation tracking** -- Distinguishes slow text (1-3 chars/frame) from instant text by tracking growth patterns across frames
4. **OCR** -- Template matching against 122 extracted game font characters (A-Z, a-z, 0-9, punctuation, accented letters, symbols)
5. **Big text** -- Detects 2x vertically stretched text (e.g., "Pum!!!", "Thud!!") using stretched templates
6. **Pokegear phone calls** (HGSS) -- Detects white-on-dark text in Pokegear call screens
7. **Garbage filtering** -- Rejects OCR artifacts from screen transitions and cutscenes

## Project structure

```
extract_dialogue.py      # Main extraction script
src/
  video.py              # Video frame reading
  screen.py             # Screen layout detection
  textbox.py            # Textbox state detection
  ocr.py                # Template matching OCR
  games/                # Game-specific configuration
templates/
  western/              # 122 character template images
tests/
  test_benchmark.py     # Regression tests
  benchmark/            # Expected output files
game-data/              # Game font/textbox reference data
tools/                  # Template extraction utilities
legacy-code/            # Original C++ implementation
```

## Testing

Video files are not included in the repository (they're too large). You need your own video files to run tests.

```bash
# Full benchmark tests (compares entire video output against expected)
python tests/test_benchmark.py

# Fast prefix tests (first 60s of each video)
python tests/test_benchmark.py fast

# Fast test with custom duration
python tests/test_benchmark.py fast -d 300

# Quick segment tests (specific tricky segments)
python tests/test_benchmark.py quick

# Test only a specific game
python tests/test_benchmark.py fast -v hgss

# Pokegear phone call test
python tests/test_benchmark.py hgss-pokegear
```

## Contributing

See `NOTES.md` for development notes and technical details.

## License

[MIT](LICENSE)
