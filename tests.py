# %%
import pytest
import json
import numpy as np
from classes import Palette, PaletteError, VirtualVRAM, VRAMError, SceneParser, SceneError

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
    assert vram._tiles_mx.shape == (256, 256)
    assert vram._sprites_mx.shape == (256, 256)
    assert vram._tiles_mx.dtype == np.uint8
    assert vram._sprites_mx.dtype == np.uint8

def test_vram_decode_all_zeros(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram._tiles_mx.max() == 0

def test_vram_decode_all_ff(tmp_path):
    t = make_tmp_bin(tmp_path, bytes([0xFF] * 32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram._tiles_mx.max() == 15
    assert vram._tiles_mx.min() == 15

def test_vram_decode_nibbles(tmp_path):
    # 0xAB → high nibble = 10 (primo pixel), low nibble = 11 (secondo pixel)
    data = bytes([0xAB]) + bytes(32767)
    t = make_tmp_bin(tmp_path, data, "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram._tiles_mx[0, 0] == 10
    assert vram._tiles_mx[0, 1] == 11


# -- VirtualVRAM file errors --------------------------------------------------

def test_vram_tiles_not_found(tmp_path):
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    with pytest.raises(FileNotFoundError):
        VirtualVRAM("non_esiste.bin", s)

def test_vram_sprites_not_found(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    with pytest.raises(FileNotFoundError):
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


# -- get_tile / get_sprite sheet builders -------------------------------------

def make_tile_sheet(tile_id, fill_byte=0xFF):
    data = bytearray(32768)
    row_start = (tile_id // 8) * 32
    col_start = (tile_id % 8) * 32
    for r in range(32):
        offset = (row_start + r) * 128 + col_start // 2
        for b in range(16):
            data[offset + b] = fill_byte
    return bytes(data)

def make_sprite_sheet(sprite_id, fill_byte=0xFF):
    data = bytearray(32768)
    row_start = (sprite_id // 4) * 64
    col_start = (sprite_id % 4) * 64
    for r in range(64):
        offset = (row_start + r) * 128 + col_start // 2
        for b in range(32):
            data[offset + b] = fill_byte
    return bytes(data)


# -- get_tile happy path ------------------------------------------------------

def test_get_tile_shape(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_tile(0).shape == (32, 32)
    assert vram.get_tile(0).dtype == np.uint8

def test_get_tile_first(tmp_path):
    t = make_tmp_bin(tmp_path, make_tile_sheet(0), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_tile(0).min() == 15
    assert vram.get_tile(0).max() == 15

def test_get_tile_last(tmp_path):
    t = make_tmp_bin(tmp_path, make_tile_sheet(63), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_tile(63).min() == 15
    assert vram.get_tile(63).max() == 15

def test_get_tile_isolation(tmp_path):
    t = make_tmp_bin(tmp_path, make_tile_sheet(5), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_tile(5).min() == 15
    assert vram.get_tile(0).max() == 0


# -- get_tile error path ------------------------------------------------------

def test_get_tile_not_int(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    with pytest.raises(VRAMError):
        vram.get_tile("0")

def test_get_tile_out_of_range_high(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    with pytest.raises(VRAMError):
        vram.get_tile(64)

def test_get_tile_out_of_range_low(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    with pytest.raises(VRAMError):
        vram.get_tile(-1)


# -- get_sprite happy path ----------------------------------------------------

def test_get_sprite_shape(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_sprite(0).shape == (64, 64)
    assert vram.get_sprite(0).dtype == np.uint8

def test_get_sprite_first(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, make_sprite_sheet(0), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_sprite(0).min() == 15
    assert vram.get_sprite(0).max() == 15

def test_get_sprite_last(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, make_sprite_sheet(15), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_sprite(15).min() == 15
    assert vram.get_sprite(15).max() == 15

def test_get_sprite_isolation(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, make_sprite_sheet(7), "sprites.bin")
    vram = VirtualVRAM(t, s)
    assert vram.get_sprite(7).min() == 15
    assert vram.get_sprite(0).max() == 0


# -- get_sprite error path ----------------------------------------------------

def test_get_sprite_not_int(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    with pytest.raises(VRAMError):
        vram.get_sprite("0")

def test_get_sprite_out_of_range_high(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    with pytest.raises(VRAMError):
        vram.get_sprite(16)

def test_get_sprite_out_of_range_low(tmp_path):
    t = make_tmp_bin(tmp_path, bytes(32768), "tiles.bin")
    s = make_tmp_bin(tmp_path, bytes(32768), "sprites.bin")
    vram = VirtualVRAM(t, s)
    with pytest.raises(VRAMError):
        vram.get_sprite(-1)


# -- SceneParser helpers ------------------------------------------------------

VALID_TILE_MAP = [[0] * 20 for _ in range(15)]
VALID_SPRITE = {"id": 0, "x": 0, "y": 0, "flip_x": False, "flip_y": False, "rotation": 0}

def make_scene(tmp_path, data, name="scene.json"):
    f = tmp_path / name
    f.write_text(json.dumps(data))
    return str(f)

def valid_scene():
    return {
        "transparent_index": 0,
        "tile_map": VALID_TILE_MAP,
        "sprites": [VALID_SPRITE],
    }


# -- SceneParser happy path ---------------------------------------------------

def test_scene_load_ok(tmp_path):
    p = SceneParser(make_scene(tmp_path, valid_scene()))
    assert p.transparent_index == 0
    assert p.tile_map.shape == (15, 20)
    assert p.tile_map.dtype == np.uint8
    assert isinstance(p.sprites, list)

def test_scene_transparent_index_boundary(tmp_path):
    data = valid_scene()
    data["transparent_index"] = 15
    p = SceneParser(make_scene(tmp_path, data))
    assert p.transparent_index == 15

def test_scene_empty_sprites(tmp_path):
    data = valid_scene()
    data["sprites"] = []
    p = SceneParser(make_scene(tmp_path, data))
    assert p.sprites == []

def test_scene_sprite_fields(tmp_path):
    p = SceneParser(make_scene(tmp_path, valid_scene()))
    s = p.sprites[0]
    assert s["id"] == 0
    assert s["x"] == 0
    assert s["y"] == 0
    assert s["flip_x"] is False
    assert s["flip_y"] is False
    assert s["rotation"] == 0


# -- SceneParser file errors --------------------------------------------------

def test_scene_file_not_found():
    with pytest.raises(FileNotFoundError):
        SceneParser("non_esiste.json")

def test_scene_invalid_json(tmp_path):
    f = tmp_path / "scene.json"
    f.write_text("questo non e json {{{")
    with pytest.raises(SceneError):
        SceneParser(str(f))


# -- SceneParser missing keys -------------------------------------------------

def test_scene_missing_transparent_index(tmp_path):
    data = valid_scene()
    del data["transparent_index"]
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_missing_tile_map(tmp_path):
    data = valid_scene()
    del data["tile_map"]
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_missing_sprites(tmp_path):
    data = valid_scene()
    del data["sprites"]
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))


# -- SceneParser transparent_index errors -------------------------------------

def test_scene_transparent_index_not_int(tmp_path):
    data = valid_scene()
    data["transparent_index"] = "0"
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_transparent_index_too_high(tmp_path):
    data = valid_scene()
    data["transparent_index"] = 16
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_transparent_index_negative(tmp_path):
    data = valid_scene()
    data["transparent_index"] = -1
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))


# -- SceneParser tile_map errors ----------------------------------------------

def test_scene_tile_map_wrong_rows(tmp_path):
    data = valid_scene()
    data["tile_map"] = [[0] * 20 for _ in range(10)]
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_tile_map_wrong_cols(tmp_path):
    data = valid_scene()
    data["tile_map"] = [[0] * 15 for _ in range(15)]
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_tile_map_value_too_high(tmp_path):
    data = valid_scene()
    data["tile_map"][0][0] = 64
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_tile_map_value_negative(tmp_path):
    data = valid_scene()
    data["tile_map"][0][0] = -1
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))


# -- SceneParser sprite errors ------------------------------------------------

def test_scene_sprites_not_list(tmp_path):
    data = valid_scene()
    data["sprites"] = "not a list"
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_missing_field(tmp_path):
    data = valid_scene()
    del data["sprites"][0]["rotation"]
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_id_not_int(tmp_path):
    data = valid_scene()
    data["sprites"][0]["id"] = "0"
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_id_too_high(tmp_path):
    data = valid_scene()
    data["sprites"][0]["id"] = 16
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_id_negative(tmp_path):
    data = valid_scene()
    data["sprites"][0]["id"] = -1
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_x_not_int(tmp_path):
    data = valid_scene()
    data["sprites"][0]["x"] = 1.5
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_y_not_int(tmp_path):
    data = valid_scene()
    data["sprites"][0]["y"] = "0"
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_flip_x_not_bool(tmp_path):
    data = valid_scene()
    data["sprites"][0]["flip_x"] = 0
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_flip_y_not_bool(tmp_path):
    data = valid_scene()
    data["sprites"][0]["flip_y"] = 1
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_rotation_not_int(tmp_path):
    data = valid_scene()
    data["sprites"][0]["rotation"] = "90"
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))

def test_scene_sprite_rotation_invalid(tmp_path):
    data = valid_scene()
    data["sprites"][0]["rotation"] = 45
    with pytest.raises(SceneError):
        SceneParser(make_scene(tmp_path, data))
