import numpy as np
import pytest
import xarray
from PIL import Image
from pathlib import Path
from typing import Union

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


@pytest.fixture
def auto_title(request) -> str:
    """
    Fixture to automatically generate a (batch job) title for a test based
    on the test's file and function name.
    """
    return request.node.nodeid
