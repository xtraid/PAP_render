# %%
import pytest
import json
import numpy as np
from classes import Palette, PaletteError, VirtualVRAM, VRAMError

VALID = "test_data/palette_ok.json"


def make_tmp(tmp_path, data):
    f = tmp_path / "palette.json"
    f.write_text(json.dumps(data))
    return str(f)


# -- happy path ---------------------------------------------------------------

def test_load_ok():
    p = Palette(VALID)
    assert p.data.shape == (16, 3)
    assert p.data.dtype == np.uint8

def test_getitem_first():
    p = Palette(VALID)
    assert list(p[0]) == [0, 0, 0]

def test_getitem_last():
    p = Palette(VALID)
    assert list(p[15]) == [255, 128, 0]

def test_boundary_values(tmp_path):
    data = [([0, 0, 0] if i % 2 == 0 else [255, 255, 255]) for i in range(16)]
    p = Palette(make_tmp(tmp_path, data))
    assert list(p[0]) == [0, 0, 0]
    assert list(p[1]) == [255, 255, 255]


# -- file errors --------------------------------------------------------------

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        Palette("non_esiste.json")

def test_invalid_json(tmp_path):
    f = tmp_path / "palette.json"
    f.write_text("questo non e json {{{")
    with pytest.raises(PaletteError):
        Palette(str(f))


# -- wrong color count --------------------------------------------------------

def test_too_few_colors(tmp_path):
    data = [[0, 0, 0]] * 3
    with pytest.raises(PaletteError):
        Palette(make_tmp(tmp_path, data))

def test_too_many_colors(tmp_path):
    data = [[0, 0, 0]] * 17
    with pytest.raises(PaletteError):
        Palette(make_tmp(tmp_path, data))

def test_empty_palette(tmp_path):
    with pytest.raises(PaletteError):
        Palette(make_tmp(tmp_path, []))


# -- wrong color format -------------------------------------------------------

def test_color_too_few_components(tmp_path):
    data = [[0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        Palette(make_tmp(tmp_path, data))

def test_color_too_many_components(tmp_path):
    data = [[0, 0, 0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        Palette(make_tmp(tmp_path, data))


# -- out of range values ------------------------------------------------------

def test_value_above_255(tmp_path):
    data = [[300, 0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        Palette(make_tmp(tmp_path, data))

def test_value_negative(tmp_path):
    data = [[-1, 0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        Palette(make_tmp(tmp_path, data))

def test_value_exact_255(tmp_path):
    data = [[255, 255, 255]] * 16
    p = Palette(make_tmp(tmp_path, data))
    assert list(p[0]) == [255, 255, 255]


# -- __getitem__ bounds -------------------------------------------------------

def test_getitem_out_of_range_high():
    p = Palette(VALID)
    with pytest.raises(PaletteError):
        p[16]

def test_getitem_out_of_range_low():
    p = Palette(VALID)
    with pytest.raises(PaletteError):
        p[-1]


# -- VirtualVRAM helpers ------------------------------------------------------

def make_tmp_bin(tmp_path, data, name="sheet.bin"):
    f = tmp_path / name
    f.write_bytes(data)
    return str(f)


# -- VirtualVRAM happy path ---------------------------------------------------

def test_vram_load_ok(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.tiles_mx.shape == (256, 256)
    assert vram.sprites_mx.shape == (256, 256)
    assert vram.tiles_mx.dtype == np.uint8
    assert vram.sprites_mx.dtype == np.uint8

def test_vram_decode_all_zeros(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.tiles_mx.max() == 0

def test_vram_decode_all_ff(tmp_path):
    t = make_tmp_bin(tmp_path, bytes([0xFF] * 32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.tiles_mx.max() == 15
    assert vram.tiles_mx.min() == 15

def test_vram_decode_nibbles(tmp_path):
    # 0xAB → high nibble = 10 (primo pixel), low nibble = 11 (secondo pixel)
    data = bytes([0xAB]) + bytes(32767)
    t = make_tmp_bin(tmp_path, data, "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.tiles_mx[0, 0] == 10
    assert vram.tiles_mx[0, 1] == 11


# -- VirtualVRAM file errors --------------------------------------------------

def test_vram_tiles_not_found(tmp_path):
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    with pytest.raises(VRAMError):
        VirtualVRAM("non_esiste.bin", s)

def test_vram_sprites_not_found(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    with pytest.raises(VRAMError):
        VirtualVRAM(t, "non_esiste.bin")


# -- VirtualVRAM wrong size ---------------------------------------------------

def test_vram_tiles_wrong_size(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(100), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    with pytest.raises(VRAMError):
        VirtualVRAM(t, s)

def test_vram_sprites_wrong_size(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(100), "sprites.bin")
    with pytest.raises(VRAMError):
        VirtualVRAM(t, s)
