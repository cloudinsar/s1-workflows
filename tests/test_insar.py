import pytest
import shutil

import base64
import logging
import sys

from testutils import *

_log = logging.getLogger(__name__)

sys.path.append(".")
sys.path.append("..")
from workflow_utils import *


def get_tiffs_from_stac_catalog(catalog_path: Path):
    """
    Simple function that recursively searches tiff files in catalog
    """
    import json

    catalog_path = Path(catalog_path)
    assert catalog_path.exists()
    catalog_json = json.loads(catalog_path.read_text())
    tiff_files = []
    links = []
    if "links" in catalog_json:
        links.extend(catalog_json["links"])
    if "assets" in catalog_json:
        links.extend(list(catalog_json["assets"].values()))
    for link in links:
        if "href" in link and link["href"].lower().endswith(".tif"):  # data link
            href = link["href"]
            if href.startswith("file://"):
                href = href[7:]
            # make absolute, compared to parent json file:
            href = os.path.normpath(os.path.join(catalog_path.parent, href))
            tiff_files.append(Path(href))
        elif "rel" in link and (link["rel"] == "child" or link["rel"] == "item") and "href" in link:
            child_path = catalog_path.parent / link["href"]
            tiff_files.extend(get_tiffs_from_stac_catalog(child_path))
    return tiff_files


def run_stac_catalog_and_verify(catalog_path: Path, tmp_dir: Path):
    catalog_path = Path(catalog_path)

    tiff_files_input = get_tiffs_from_stac_catalog(catalog_path)
    assert tiff_files_input, "There should be at least one .tif file generated"

    assert_tif_file_is_healthy(tiff_files_input[0])

    process_graph = {
        "process_graph": {
            "loadstac1": {"process_id": "load_stac", "arguments": {"url": str(catalog_path)}, "result": True}
        },
        "parameters": [],
    }
    openeo_result = tmp_dir / ("openeo_result_" + catalog_path.stem)
    openeo_result.mkdir(exist_ok=True)
    return  # local running is broken for the moment
    from openeogeotrellis.deploy.run_graph_locally import run_graph_locally

    run_graph_locally(process_graph, openeo_result)

    tiff_files_result = list(openeo_result.glob("*.tif"))
    assert tiff_files_result, "There should be at least one .tif file generated"

    assert_tif_file_is_healthy(tiff_files_result[0])

    # Compare openEO results to raw CWL results pixel based:
    # result = rioxarray.open_rasterio(tiff_files_input[0])
    # expected = rioxarray.open_rasterio(tiff_files_result[0])
    # assert_xarray_equals(result.values, expected.values)


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "script",
    [
        "OpenEO_insar_coherence.py",
        "OpenEO_insar_interferogram_snaphu.py",
    ],
)
@pytest.mark.parametrize(
    "input_dict",
    [
        # input_dict_2024_vv,
        input_dict_2018_vh,
        input_dict_belgium_vv,
    ],
)
def test_insar(script, input_dict, auto_title):
    input_base64_json = base64.b64encode(json.dumps(input_dict).encode("utf8")).decode("ascii")

    tmp_dir = Path(repository_root / slugify(auto_title).replace("tests/", "tests/tmp_")).absolute()
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(exist_ok=True)
    exec_proc(["python", repository_root / script, input_base64_json], cwd=tmp_dir)

    json_files = list(tmp_dir.glob("*collection*.json"))
    assert json_files, "A *collection*.json file generated"

    tiff_files = list(tmp_dir.glob("*.tif"))
    assert tiff_files, "There should be at least one .tif file generated"

    assert_tif_file_is_healthy(tiff_files[0])

    for jf in json_files:
        run_stac_catalog_and_verify(jf, tmp_dir)


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "input_dict",
    [input_dict_2018_vh_preprocessing],
)
def test_insar_preprocessing(input_dict, auto_title):
    script = "OpenEO_insar_preprocessing.py"

    input_base64_json = base64.b64encode(json.dumps(input_dict).encode("utf8")).decode("ascii")

    tmp_dir = Path(repository_root / slugify(auto_title).replace("tests/", "tests/tmp_")).absolute()
    print(f"{tmp_dir=}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(exist_ok=True)
    exec_proc(["python", repository_root / script, input_base64_json], cwd=tmp_dir)

    json_files = list(tmp_dir.glob("*collection*.json"))
    assert json_files, "A *collection*.json file generated"

    tiff_files = list(tmp_dir.glob("*.tif"))
    assert tiff_files, "There should be at least one .tif file generated"

    assert_tif_file_is_healthy(tiff_files[0])

    for jf in json_files:
        run_stac_catalog_and_verify(jf, tmp_dir)


@pytest.mark.skip("OOM on CI")
def test_insar_preprocessing_stac(auto_title):
    script = "OpenEO_insar_preprocessing.py"
    input_dict = input_dict_2018_vh_preprocessing
    input_base64_json = base64.b64encode(json.dumps(input_dict).encode("utf8")).decode("ascii")

    tmp_dir = Path(repository_root / slugify(auto_title).replace("tests/", "tests/tmp_")).absolute()
    print(f"{tmp_dir=}")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(exist_ok=True)
    exec_proc(["python", repository_root / script, input_base64_json], cwd=tmp_dir)

    import openeo

    stac_root_master = Path(tmp_dir / "S1_2images_collection_master.json").absolute()
    stac_root_slaves = Path(tmp_dir / "S1_2images_collection_slaves.json").absolute()
    assert stac_root_master.exists()
    assert stac_root_slaves.exists()

    datacube_master = openeo.DataCube.load_stac(url=str(stac_root_master), bands=["grid_lat", "grid_lon"])
    datacube_master = datacube_master.reduce_dimension(reducer="max", dimension="t")
    datacube_slaves = openeo.DataCube.load_stac(url=str(stac_root_slaves), bands=["i_VH", "q_VH"])
    datacube = datacube_slaves.merge_cubes(datacube_master)
    datacube = datacube.resample_spatial(resolution=1, projection="EPSG:3857")  # webmercator

    # datacube = datacube.rename_labels(dimension="t", target=['2018-01-28_2018-02-03'])
    datacube = datacube.reduce_dimension(dimension="t", reducer="mean")
    # datacube = datacube.filter_bbox(
    #     west=-50,
    #     east=50,
    #     south=-50,
    #     north=50,
    #     crs="EPSG:3857"
    # )

    output_dir = (tmp_dir / "tmp_local_output").absolute()
    output_dir.mkdir(exist_ok=True)
    datacube.print_json(file=output_dir / "process_graph.json", indent=2)

    ###################################
    # Step 2, run process graph locally
    ###################################
    containing_folder = Path(__file__).parent.absolute()

    from openeogeotrellis.deploy.run_graph_locally import run_graph_locally

    run_graph_locally(output_dir / "process_graph.json", output_dir)
