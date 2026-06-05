# PAP Render

A command-line pixel art renderer that composites a scene from a tile-based background and a list of sprites, exporting the result as a PNG image.

## Overview

- 16-color indexed palette (4 bit per pixel)
- Tile sheet: 64 tiles of 32×32 pixels in a 256×256 image
- Sprite sheet: 16 sprites of 64×64 pixels in a 256×256 image
- Frame buffer: 640×480 pixels (tile map 15×20)
- Sprite transformations: flip on x/y axis, rotation by 90/180/270 degrees
- Transparency via a designated palette index

## Usage

```bash
python main.py <palette.json> <scene.json> <tiles.bin> <sprites.bin> <output.png>
```

| Argument | Description |
|---|---|
| `palette.json` | 16 RGB colors |
| `scene.json` | transparent index, tile map, sprite list |
| `tiles.bin` | packed binary tile sheet (32768 bytes) |
| `sprites.bin` | packed binary sprite sheet (32768 bytes) |
| `output.png` | rendered output |

## Input Format

### palette.json

Array of 16 RGB colors:

```json
[
  [0, 0, 0],
  [255, 0, 0],
  ...
]
```

### scene.json

```json
{
  "transparent_index": 0,
  "tile_map": [[1, 0, 2, ...], ...],
  "sprites": [
    { "id": 0, "x": 100, "y": 80, "flip_x": false, "flip_y": false, "rotation": 0 }
  ]
}
```

- `transparent_index`: palette index (0–15) treated as transparent for all sprites
- `tile_map`: 15×20 matrix of tile IDs (0–63)
- `sprites`: ordered list — draw order determines z-order

### .bin files

Packed binary, 256×256 pixels stored as 32768 bytes. Each byte contains 2 pixels:
- high nibble (bits 7–4): first pixel → palette index 0–15
- low nibble (bits 3–0): second pixel → palette index 0–15

## Architecture

| Class | Responsibility | Status |
|---|---|---|
| `Palette` | Reads and validates `palette.json`, maps index → RGB | Done |
| `VirtualVRAM` | Loads `.bin` files, decodes nibble-packed pixels into index matrices | Done |
| `SceneParser` | Reads `scene.json`, returns tile map and sprite list | Planned |
| `Blitter` | Applies transformations and transparency, composites tiles and sprites | Planned |
| `RenderingPipeline` | Orchestrates the full render and exports PNG | Planned |

Custom exceptions (`PaletteError`, `VRAMError`) are raised for all invalid input cases.

## Requirements

- Python ≥ 3.14
- `Pillow` used only for PNG export
- `numpy` arrays with `np.uint8` dtype

## Project Structure

```
.
├── main.py               # Entry point (placeholder)
├── classes.py            # Palette, VirtualVRAM (and future classes)
├── tests.py              # Test suite (24 tests, all passing)
├── test_data/
│   ├── palette_ok.json          # Valid 16-color palette
│   ├── palette_wrong_count.json # Only 3 colors (invalid)
│   └── palette_wrong_value.json # Component > 255 (invalid)
└── pyproject.toml
```

## Tests

```bash
uv run pytest tests.py -v
```

24 tests covering `Palette` and `VirtualVRAM`:

**Palette (16 tests)**
- Happy path: load, `__getitem__` first/last, boundary values (0 and 255)
- File errors: file not found, invalid JSON
- Wrong color count: too few, too many, empty
- Wrong color format: fewer than 3 components, more than 3 components
- Out-of-range values: above 255, negative, exact 255
- `__getitem__` bounds: index 16 and index −1

**VirtualVRAM (8 tests)**
- Happy path: load, shape and dtype, all-zeros decode, all-`0xFF` decode, nibble split (`0xAB` → 10, 11)
- File errors: tiles not found, sprites not found
- Wrong size: tiles file too short, sprites file too short
