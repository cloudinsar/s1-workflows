import numpy as np
import xarray
from PIL import Image
from pathlib import Path
import pytest
from typing import Union
import rioxarray

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
    shape = difference_ndarray.shape
    shape = (1, shape[1], shape[2])
    difference_ndarray_rgb = np.append(difference_ndarray, np.zeros(shape), axis=0).transpose(1, 2, 0).astype("|u1")

    im = Image.fromarray(difference_ndarray_rgb)
    im.save("tmp_diff.tiff")

    significantly_different = abs(xa1 - 1.0 * xa2) > tolerance
    assert significantly_different.mean().item() <= max_nonmatch_ratio
    np.testing.assert_allclose(
        xa2.where(~significantly_different),
        xa2.where(~significantly_different),
        rtol=0,
        atol=tolerance,
        equal_nan=True,
    )


@pytest.mark.skip(reason="TODO: Run against openEO backend to get result?")
def test_compare_raw_with_result():
    expected_result = Path(repository_root / "tmp_slv_20180203T062631.tif")
    actual_result = Path(
        "/home/emile/openeo/VITO/VITO2025/cwl_testing/out-2025-09-16_11_02_49.397206_cwl_insar_preprocessing_test_py/openEO_2018-02-03Z.tif"
    )
    assert actual_result.exists()
    result = rioxarray.open_rasterio(actual_result)
    # keep only first 2 bands:
    result = result.isel(band=slice(0, 2))
    result = result.values

    assert expected_result.exists()
    expected = rioxarray.open_rasterio(expected_result)
    expected = expected.values
    assert_xarray_equals(result, expected)
