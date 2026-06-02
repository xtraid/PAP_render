# %%
import pytest
import json
import numpy as np
from palette import palette, PaletteError

VALID = "test_data/palette_ok.json"


def make_tmp(tmp_path, data):
    f = tmp_path / "palette.json"
    f.write_text(json.dumps(data))
    return str(f)


# -- happy path ---------------------------------------------------------------

def test_load_ok():
    p = palette(VALID)
    assert p.data.shape == (16, 3)
    assert p.data.dtype == np.uint8

def test_getitem_first():
    p = palette(VALID)
    assert list(p[0]) == [0, 0, 0]

def test_getitem_last():
    p = palette(VALID)
    assert list(p[15]) == [255, 128, 0]

def test_boundary_values(tmp_path):
    data = [([0, 0, 0] if i % 2 == 0 else [255, 255, 255]) for i in range(16)]
    p = palette(make_tmp(tmp_path, data))
    assert list(p[0]) == [0, 0, 0]
    assert list(p[1]) == [255, 255, 255]


# -- file errors --------------------------------------------------------------

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        palette("non_esiste.json")

def test_invalid_json(tmp_path):
    f = tmp_path / "palette.json"
    f.write_text("questo non e json {{{")
    with pytest.raises(PaletteError):
        palette(str(f))


# -- wrong color count --------------------------------------------------------

def test_too_few_colors(tmp_path):
    data = [[0, 0, 0]] * 3
    with pytest.raises(PaletteError):
        palette(make_tmp(tmp_path, data))

def test_too_many_colors(tmp_path):
    data = [[0, 0, 0]] * 17
    with pytest.raises(PaletteError):
        palette(make_tmp(tmp_path, data))

def test_empty_palette(tmp_path):
    with pytest.raises(PaletteError):
        palette(make_tmp(tmp_path, []))


# -- wrong color format -------------------------------------------------------

def test_color_too_few_components(tmp_path):
    data = [[0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        palette(make_tmp(tmp_path, data))

def test_color_too_many_components(tmp_path):
    data = [[0, 0, 0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        palette(make_tmp(tmp_path, data))


# -- out of range values ------------------------------------------------------

def test_value_above_255(tmp_path):
    data = [[300, 0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        palette(make_tmp(tmp_path, data))

def test_value_negative(tmp_path):
    data = [[-1, 0, 0]] + [[0, 0, 0]] * 15
    with pytest.raises(PaletteError):
        palette(make_tmp(tmp_path, data))

def test_value_exact_255(tmp_path):
    data = [[255, 255, 255]] * 16
    p = palette(make_tmp(tmp_path, data))
    assert list(p[0]) == [255, 255, 255]


# -- __getitem__ bounds -------------------------------------------------------

def test_getitem_out_of_range_high():
    p = palette(VALID)
    with pytest.raises(PaletteError):
        p[16]

def test_getitem_out_of_range_low():
    p = palette(VALID)
    with pytest.raises(PaletteError):
        p[-1]
