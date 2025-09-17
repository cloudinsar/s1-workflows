import logging
import pytest
import rioxarray
from pathlib import Path

from testutils import *

_log = logging.getLogger(__name__)


@pytest.mark.skip(reason="TODO: Log into openEO backend")
def test_preprocessing_against_openeo_backend(auto_title):
    import openeo

    url = "https://openeo.dataspace.copernicus.eu"
    connection = openeo.connect(url).authenticate_oidc()

    datacube = connection.datacube_from_process(
        process_id="insar_preprocessing_v02",
        burst_id=329488,
        sub_swath="IW2",
        temporal_extent=["2018-01-26", "2018-02-07"],
        master_date="2018-01-28",
        polarization="vh",
    )

    datacube = datacube.save_result(format="GTiff")

    job = datacube.create_job(title=auto_title)
    job.start_and_wait()
    job.get_results().download_files("tmp" + auto_title)


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
