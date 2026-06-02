import numpy as np
import json


class PaletteError(Exception):
    pass


class palette:
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
                        f"color {i}: value {component} out od bounds [0, 255]"
                    )
        return np.array(raw, np.uint8)

    # Prints the full palette to stdout.
    # Input: none.
    # Output: none.
    def print_palette(self):
        print(self.data)

    # Returns the RGB color at the given palette index.
    # Input: idx — integer in [0, 15].
    # Output: np.ndarray of shape (3,) dtype uint8 with [R, G, B] values.
    def __getitem__(self, idx):
        if not 0 <= idx <= 15:
            raise PaletteError(f"index {idx} out of range [0, 15]")
        return self.data[idx]
