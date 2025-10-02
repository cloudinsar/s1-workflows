import logging
import rioxarray
import openeo

from testutils import *

#
# This test file is executed manually for the moment.
# It is serves as a scratchpad for testing purposes.
#

_log = logging.getLogger(__name__)
local_openEO = False


def get_connection():
    if local_openEO:
        # Start local openEO by running:
        #    minikube start
        #    local.py
        # https://github.com/Open-EO/openeo-geopyspark-driver/blob/master/docs/calrissian-cwl.md#kubernetes-setup
        return openeo.connect("http://127.0.0.1:8080").authenticate_basic("openeo", "openeo")
    else:
        # url = "https://openeo.dataspace.copernicus.eu"
        # url = "https://openeo.dev.warsaw.openeo.dataspace.copernicus.eu/"  # needs VPN
        url = "https://openeo-staging.dataspace.copernicus.eu/"
        return openeo.connect(url).authenticate_oidc()


@pytest.mark.skip(reason="TODO: Log into openEO backend")
def test_insar_coherence_against_openeo_backend(auto_title):
    now = datetime.now()
    tmp_dir = Path(repository_root / slugify(auto_title + "_" + str(now)).replace("tests/", "tests/tmp_")).absolute()
    tmp_dir.mkdir(exist_ok=True)
    datacube = get_connection().datacube_from_process(
        process_id="insar_coherence",
        # process_id="insar_interferogram_snaphu",
        **input_dict_2018_vh,
        # **input_dict_2024_vv,
    )

    if local_openEO:
        datacube = datacube.save_result(format="NetCDF")
        datacube.download(tmp_dir / "result.nc")
    else:
        datacube = datacube.save_result(format="GTiff")
        job = datacube.create_job(title=auto_title)
        job.start_and_wait()
        job.get_results().download_files(tmp_dir)


heavy_job_options = {
    "driver-memory": "7G",
    "driver-memoryOverhead": "5G",
    "executor-memory": "5G",
    "executor-memoryOverhead": "5G",
    "python-memory": "4200m",
}


@pytest.mark.skip(reason="TODO: Log into openEO backend")
def test_insar_preprocessing_v02_against_openeo_backend(auto_title):
    now = datetime.now()
    tmp_dir = Path(repository_root / slugify(auto_title + "_" + str(now)).replace("tests/", "tests/tmp_")).absolute()
    tmp_dir.mkdir(exist_ok=True)
    datacube = get_connection().datacube_from_process(
        process_id="insar_preprocessing",
        # process_id="insar_preprocessing_v02",
        # **input_dict_2018_vh_preprocessing,
        **input_dict_belgium_vv_vh_preprocessing,
    )

    if local_openEO:
        datacube = datacube.save_result(format="NetCDF")
        datacube.download(tmp_dir / "result.nc")
    else:
        datacube = datacube.save_result(format="GTiff")
        job = datacube.create_job(title=auto_title, job_options=heavy_job_options)
        job.start_and_wait()
        job.get_results().download_files(tmp_dir)


@pytest.mark.skip(reason="TODO: Run against openEO backend to get result?")
def test_compare_raw_with_result():
    expect_result = Path(
        repository_root
        / "tests/tmp_test_insar.py_test_insar_preprocessing_input_dict0/S1_2images_slv_20180203T062631.tif"
    )
    actual_result = Path(
        repository_root
        / "tests/tmp_test_insar.py_test_insar_preprocessing_input_dict0/openeo_result_S1_2images_collection_slaves/openEO_2018-02-03Z.tif"
    )
    assert actual_result.exists()
    result = rioxarray.open_rasterio(actual_result)
    # keep only first 2 bands:
    result = result.isel(band=slice(0, 2))
    result = result.values

    assert expect_result.exists()
    expected = rioxarray.open_rasterio(expect_result)
    expected = expected.values
    assert_xarray_equals(result, expected)
