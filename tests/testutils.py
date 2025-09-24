import numpy as np
import pytest
import xarray
from PIL import Image
from pathlib import Path
from typing import Union

import rioxarray

repository_root = Path(__file__).parent.parent

input_dict_2024_vv = {
    "InSAR_pairs": [
        ["2024-08-09", "2024-08-21"],
        # ["2024-08-09", "2024-09-02"],
        # ["2024-08-21", "2024-09-02"],
        # ["2024-08-21", "2024-09-14"],
        # ["2024-09-02", "2024-09-14"],
    ],
    "burst_id": 249435,
    # Coherence window size:
    "coherence_window_az": 2,
    "coherence_window_rg": 10,
    # Multillok parameters:
    "n_az_looks": 1,
    "n_rg_looks": 4,
    "polarization": "vv",
    "sub_swath": "IW2",
}

input_dict_2018_vh = {
    "InSAR_pairs": [["2018-01-28", "2018-02-03"]],
    "burst_id": 329488,
    "coherence_window_az": 2,
    "coherence_window_rg": 10,
    "n_az_looks": 1,
    "n_rg_looks": 4,
    "polarization": "vh",
    "sub_swath": "IW2",
}

input_dict_belgium_vv = {
    "InSAR_pairs": [["2024-08-09", "2024-08-21"]],
    "burst_id": 234893,
    "polarization": "vv",
    "sub_swath": "IW1",
}
input_dict_2018_vh_preprocessing = {
    "temporal_extent": ["2018-01-26", "2018-02-07"],
    "master_date": "2018-01-28",
    "burst_id": 329488,
    "polarization": "vh",
    "sub_swath": "IW2",
}

input_dict_belgium_vv_preprocessing = {
    "burst_id": 234893,
    "master_date": "2024-08-09",
    "polarization": "vv",
    "sub_swath": "IW1",
    "temporal_extent": ["2024-08-09", "2024-08-21"],
}


def assert_xarray_equals(
    xa1: Union[xarray.DataArray, np.ndarray],
    xa2: Union[xarray.DataArray, np.ndarray],
    max_nonmatch_ratio=0.01,
    tolerance=1.0e-6,
):
    """
    this function checks that only up to a portion of values do not match within tolerance
    """
    assert xa1.shape == xa2.shape

    difference_ndarray = xa1 - 1.0 * xa2
    if difference_ndarray.shape[0] <= 3:
        # Save compare image
        band_slice_shape: tuple = (
            3 - difference_ndarray.shape[0],
            difference_ndarray.shape[1],
            difference_ndarray.shape[2],
        )
        difference_ndarray = np.append(difference_ndarray, np.zeros(band_slice_shape), axis=0)
        difference_ndarray_rgb = difference_ndarray.transpose(1, 2, 0).astype("|u1")
        im = Image.fromarray(difference_ndarray_rgb)
        im.save("tmp_diff.tiff")

    significantly_different = abs(xa1 - 1.0 * xa2) > tolerance
    assert significantly_different.mean().item() <= max_nonmatch_ratio
    # np.testing.assert_allclose(
    #     xa2.where(~significantly_different),
    #     xa2.where(~significantly_different),
    #     rtol=0,
    #     atol=tolerance,
    #     equal_nan=True,
    # )


def slugify(title):
    title = title.lower().replace(" ", "_").replace(",", "_")
    windows_characters = ["<", ">", ":", '"', "\\", "|", "?", "*", "[", "]"]
    for char in windows_characters:
        title = title.replace(char, "_")
    title = title.strip("_").replace("__", "_")
    return title


def assert_tif_file_is_healthy(tif_path):
    tiff_arr = rioxarray.open_rasterio(tif_path)
    # tiff_arr.shape = (4, 1519, 26767)
    shape = tiff_arr.shape
    assert shape[1] > 100
    assert shape[2] > 100
    assert shape[2] >= shape[1]
    assert (tiff_arr.values != np.nan).any()


@pytest.fixture
def auto_title(request) -> str:
    """
    Fixture to automatically generate a (batch job) title for a test based
    on the test's file and function name.
    """
    return request.node.nodeid
