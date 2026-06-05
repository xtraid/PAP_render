import numpy as np
import json


class PaletteError(Exception):
    pass


class Palette:
    def __init__(self, path):
        self.__path = path
        self.data = self._load_json()

    # Reads and validates a palette JSON file.
    # Input: self.__path — path to a JSON file containing a list of 16 [R, G, B] colors.
    # Output: np.ndarray of shape (16, 3) dtype uint8 with the palette colors.
    def _load_json(self):
        try:
            with open(self.__path) as f:
                raw = json.load(f)
        except json.JSONDecodeError as e:
            raise PaletteError(f"file JSON not valid: {e}") from e
        if len(raw) != 16:
            raise PaletteError(f"palette must contain 16 colors, trovati {len(raw)}")
        for i, color in enumerate(raw):
            if len(color) != 3:
                raise PaletteError(
                    f"color {i}: must contain 3 component for RGB, found {len(color)}"
                )
            for component in color:
                if not 0 <= component <= 255:
                    raise PaletteError(
                        f"color {i}: value {component} out of bounds [0, 255]"
                    )
        return np.array(raw, np.uint8)

    # Returns an unambiguous string representation of the palette.
    # Input: none.
    # Output: str.
    def __repr__(self):
        return f"Palette(path={self.__path!r})"

    # Prints the full palette to stdout.
    # Input: none.
    # Output: none.
    def print_palette(self):
        print(self.data)

    # Returns the RGB color at the given palette index.
    # Input: idx — integer in [0, 15].
    # Output: np.ndarray of shape (3,) dtype uint8 with [R, G, B] values.
    def __getitem__(self, idx):
        if not isinstance(idx, int):
            raise PaletteError(f"index must be int, got {type(idx).__name__}")
        if not 0 <= idx <= 15:
            raise PaletteError(f"index {idx} out of range [0, 15]")
        return self.data[idx]


class VRAMError(Exception):
    pass


class VirtualVRAM:
    def __init__(self, path_t, path_s):
        self.__path_tiles = path_t
        self.__path_sprites = path_s
        self.__tiles, self.__sprites = self._load_bin()
        self.tiles_mx = self._decode(self.__tiles)
        self.sprites_mx = self._decode(self.__sprites)

    # Reads the tile sheet and sprite sheet binary files.
    # Input: self.__path_tiles, self.__path_sprites — paths to nibble-packed binary files.
    # Output: tuple of two bytes objects (tiles_raw, sprites_raw).
    def _load_bin(self):
        try:
            with open(self.__path_tiles, "rb") as ftile:
                tiles = ftile.read()
        except OSError as e:
            raise VRAMError(f"cannot open {self.__path_tiles!r}: {e}") from e
        try:
            with open(self.__path_sprites, "rb") as fsprite:
                sprites = fsprite.read()
        except OSError as e:
            raise VRAMError(f"cannot open {self.__path_sprites!r}: {e}") from e
        return tiles, sprites

    # Decodes a nibble-packed binary buffer into a 256x256 matrix of palette indexes.
    # Input: raw — bytes of exactly 32768 bytes (2 pixels per byte, high nibble first).
    # Output: np.ndarray of shape (256, 256) dtype uint8 with palette indexes 0-15.
    def _decode(self, raw):
        if len(raw) != 32768:
            raise VRAMError(f"invalid file size: expected 32768 bytes, got {len(raw)}")
        data = np.frombuffer(raw, dtype=np.uint8)
        return np.stack([data >> 4, data & 0x0F], axis=1).ravel().reshape(256, 256)

    def __repr__(self):
        return f"VirtualVRAM(path_t={self.__path_tiles!r}, path_s={self.__path_sprites!r})"
