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

input_dict_2024_vv = {
    "InSAR_pairs": [["2024-08-09", "2024-08-21"]],
    "burst_id": 249435,
    "coherence_window_az": 2,
    "coherence_window_rg": 10,
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


def run_stac_catalog_and_verify(catalog_path: Path, tmp_dir: Path):
    catalog_path = Path(catalog_path)
    json_files = list(tmp_dir.glob("*collection*.json"))
    assert json_files, "A *collection/.json file generated"

    tiff_files = list(tmp_dir.glob("*.tif"))
    assert tiff_files, "There should be at least one .tif file generated"

    assert_tif_file_is_healthy(tiff_files[0])

    process_graph = {
        "process_graph": {
            "loadstac1": {"process_id": "load_stac", "arguments": {"url": str(catalog_path)}, "result": True}
        },
        "parameters": [],
    }
    openeo_result = tmp_dir / ("openeo_result_" + catalog_path.stem)
    openeo_result.mkdir(exist_ok=True)
    from openeogeotrellis.deploy.run_graph_locally import run_graph_locally
    run_graph_locally(process_graph, openeo_result)

    tiff_files_result = list(openeo_result.glob("*.tif"))
    assert tiff_files_result, "There should be at least one .tif file generated"

    assert_tif_file_is_healthy(tiff_files_result[0])


# @pytest.mark.skip(reason="geotrellis.raster.GeoAttrsError: invalid cols: 0")
@pytest.mark.parametrize(
    "script",
    ["OpenEO_insar_coherence.py"],
)
@pytest.mark.parametrize(
    "input_dict",
    [input_dict_2024_vv, input_dict_2018_vh],
)
def test_insar(script, input_dict, auto_title):
    input_base64_json = base64.b64encode(json.dumps(input_dict).encode("utf8")).decode("ascii")

    tmp_dir = Path(slugify(auto_title).replace("tests/", "tests/tmp_"))
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


input_dict_2018_vh_preprocessing = {
    "burst_id": 329488,
    "master_date": "2018-01-28",
    "polarization": "vh",
    "sub_swath": "IW2",
    "temporal_extent": ["2018-01-26", "2018-02-07"],
}


# @pytest.mark.skip(reason="geotrellis.raster.GeoAttrsError: invalid cols: 0")
@pytest.mark.parametrize(
    "input_dict",
    [input_dict_2018_vh_preprocessing],
)
def test_insar_preprocessing(input_dict, auto_title):
    script = "OpenEO_insar_preprocessing.py"

    input_base64_json = base64.b64encode(json.dumps(input_dict).encode("utf8")).decode("ascii")

    tmp_dir = Path(slugify(auto_title).replace("tests/", "tests/tmp_"))
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
