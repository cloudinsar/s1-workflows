import logging

import rioxarray
from openeo.rest.stac_resource import StacResource
from openeo.internal.graph_building import PGNode

from testutils import *

#
# This test file is executed manually for the moment.
# It is serves as a scratchpad for testing purposes.
#

_log = logging.getLogger(__name__)
local_openEO = False


def get_connection():
    import openeo
    if local_openEO:
        # Start local openEO by running:
        #    minikube start
        #    local.py
        # https://github.com/Open-EO/openeo-geopyspark-driver/blob/master/docs/calrissian-cwl.md#kubernetes-setup
        return openeo.connect("http://127.0.0.1:8080").authenticate_basic("openeo", "openeo")
    else:
        # url = "https://openeo.dev.warsaw.openeo.dataspace.copernicus.eu/"  # needs VPN
        # url = "https://openeo-staging.dataspace.copernicus.eu/"
        url = "https://openeo.dataspace.copernicus.eu"
        return openeo.connect(url).authenticate_oidc()


@pytest.mark.skip(reason="TODO: Log into openEO backend")
@pytest.mark.parametrize(
    "process_id",
    [
        "sar_coherence",
    ],
)
@pytest.mark.parametrize(
    "input_dict",
    [
        # json.loads((repo_directory / "sar/example_inputs/input_dict_2018_vh_new.json").read_text()),
        json.loads((repo_directory / "sar/example_inputs/input_dict_2024_vv_new.json").read_text()),
    ],
)
def test_georeferenced_new_sar_against_openeo_backend(process_id, input_dict, auto_title):
    now = datetime.now()
    tmp_dir = Path(repository_root / slugify(auto_title + "_" + str(now)).replace("tests_", "tests/tmp_")).absolute()
    tmp_dir.mkdir(exist_ok=True)

    datacube = get_connection().datacube_from_process(process_id=process_id, **input_dict)
    # datacube = get_connection().datacube_from_process(
    #     process_id="run_cwl_to_stac",
    #     # cwl_url needs to be whitelisted
    #     cwl_url="https://raw.githubusercontent.com/cloudinsar/s1-workflows/refs/heads/main/cwl/sar_coherence.cwl",
    #     context=input_dict,
    # )

    if local_openEO:
        datacube = datacube.save_result(format="NetCDF")
        # datacube.download(tmp_dir / "result.nc")
        from openeogeotrellis.deploy.run_graph_locally import run_graph_locally
        datacube.print_json(file=tmp_dir / "process_graph.json", indent=2)

        run_graph_locally(tmp_dir / "process_graph.json", tmp_dir)
    else:
        datacube = datacube.save_result(format="GTiff", options={"overviews": "OFF"})
        # datacube = datacube.export_workspace(
        #     workspace="insar-results-workspace",
        #     merge=f"{auto_title}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}",
        # )
        job = datacube.create_job(title=auto_title)
        job.start_and_wait()
        job.get_results().download_files(tmp_dir)

        tif_paths = list(tmp_dir.glob("*.tif"))
        for tif_path in tif_paths:
            assert_tif_file_is_healthy(tif_path)


@pytest.mark.skip(reason="TODO: Log into openEO backend")
@pytest.mark.parametrize(
    "process_id",
    [
        "sar_coherence_parallel",
        "sar_interferogram",
    ],
)
@pytest.mark.parametrize(
    "input_dict",
    [
        # input_dict_2018_vh,
        # input_dict_belgium_vv,
        # json.loads((repo_directory / "sar/example_inputs/input_dict_whole_2023.json").read_text()),
        json.loads((repo_directory / "sar/example_inputs/input_dict_2024_vv.json").read_text()),
        # json.loads((repo_directory / "sar/example_inputs/input_dict_2023.json").read_text()),
    ],
)
def test_georeferenced_sar_against_openeo_backend(process_id, input_dict, auto_title):
    now = datetime.now()
    tmp_dir = Path(repository_root / slugify(auto_title + "_" + str(now)).replace("tests_", "tests/tmp_")).absolute()
    tmp_dir.mkdir(exist_ok=True)
    datacube = get_connection().datacube_from_process(process_id=process_id, **input_dict)

    if local_openEO:
        datacube = datacube.save_result(format="NetCDF")
        datacube.download(tmp_dir / "result.nc")
    else:
        datacube = datacube.save_result(format="GTiff", options={"overviews": "OFF"})
        # datacube = datacube.export_workspace(
        #     workspace="insar-results-workspace",
        #     merge=f"{auto_title}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}",
        # )
        job = datacube.create_job(title=auto_title)
        job.start_and_wait()
        job.get_results().download_files(tmp_dir)

        tif_paths = list(tmp_dir.glob("*.tif"))
        for tif_path in tif_paths:
            assert_tif_file_is_healthy(tif_path)


@pytest.mark.skip(reason="TODO: Log into openEO backend")
@pytest.mark.parametrize(
    "input_dict",
    [
        # input_dict_2018_vh_preprocessing,
        # input_dict_belgium_vv_vh_preprocessing,
        input_dict_belgium_vv_preprocessing,
        # input_dict_2024_vv_preprocessing,
    ],
)
def test_sar_preprocessing_against_openeo_backend(input_dict, auto_title):
    now = datetime.now()
    tmp_dir = Path(repository_root / slugify(auto_title + "_" + str(now)).replace("tests/", "tests/tmp_")).absolute()
    tmp_dir.mkdir(exist_ok=True)
    # datacube = get_connection().datacube_from_process(process_id="sar_slc_preprocessing", **input_dict)
    stac_resource = StacResource(
        graph=PGNode(
            process_id="run_cwl_to_stac",
            arguments={
                "cwl_url": "https://raw.githubusercontent.com/cloudinsar/s1-workflows/refs/heads/main/cwl/sar_slc_preprocessing.cwl",
                "context": input_dict,
            },
        ),
        connection=get_connection(),
    )

    stac_resource = stac_resource.export_workspace(
        "insar-results-workspace",
        # "tmp_workspace",
        merge="/" + os.path.basename(__file__) + "_" + now.strftime("%Y-%m-%d_%H_%M_%S"),
    )

    if local_openEO:
        # datacube = stac_resource.save_result(format="NetCDF")
        # datacube.download(tmp_dir / "result.nc")
        # Run in the same process, so that we can check the output directly:
        from openeogeotrellis.deploy.run_graph_locally import run_graph_locally
        stac_resource.print_json(file=tmp_dir / "process_graph.json", indent=2)

        run_graph_locally(tmp_dir / "process_graph.json", tmp_dir)
    else:
        # stac_resource = datacube.save_result(format="GTiff", options={"overviews": "OFF"})
        job = stac_resource.create_job(
            title=auto_title,
            job_options={
                # "image-name": "python38-dev",
                "python-memory": "4000m",  # did also work with 3G
            },
        )
        job.start_and_wait()
        job.get_results().download_files(tmp_dir)

        tif_paths = list(tmp_dir.glob("*.tif"))
        for tif_path in tif_paths:
            assert_tif_file_is_healthy(tif_path)


@pytest.mark.skip(reason="TODO: Run against openEO backend to get result?")
def test_compare_raw_with_result():
    expect_result = Path(
        repository_root
        / "tests/tmp_test_insar.py_test_sar_preprocessing_input_dict0/S1_2images_slv_20180203T062631.tif"
    )
    actual_result = Path(
        repository_root
        / "tests/tmp_test_insar.py_test_sar_preprocessing_input_dict0/openeo_result_S1_2images_collection_slaves/openEO_2018-02-03Z.tif"
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
