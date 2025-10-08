import sys
import numpy as np
import pytest
import xarray
from PIL import Image
from pathlib import Path
from typing import Union

import rioxarray

sys.path.append(".")
sys.path.append("..")
from workflow_utils import *

repository_root = Path(__file__).parent.parent


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
    for b in range(shape[0]):
        band = tiff_arr[b, :, :]
        assert (band.values != np.nan).any()


@pytest.fixture
def auto_title(request) -> str:
    """
    Fixture to automatically generate a (batch job) title for a test based
    on the test's file and function name.
    """
    return request.node.nodeid
