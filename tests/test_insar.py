import sys

import json

import base64

import logging

from testutils import *

_log = logging.getLogger(__name__)

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


@pytest.mark.parametrize(
    "script",
    ["OpenEO_insar_coherence.py", "OpenEO_insar_interferogram_coherence.py", "OpenEO_insar_interferogram_snaphu.py"],
)
@pytest.mark.parametrize(
    "input_dict",
    [input_dict_2024_vv, input_dict_2018_vh],
)
def test_insar(script, input_dict, auto_title):
    input_base64_json = base64.b64encode(json.dumps(input_dict).encode("utf8")).decode("ascii")

    tmp_dir = Path(auto_title.replace("tests/", "tests/tmp_"))
    tmp_dir.mkdir(exist_ok=True)

    exec_proc(["python", repository_root / script, input_base64_json], cwd=tmp_dir)


@pytest.mark.parametrize(
    "input_dict",
    [input_dict_2024_vv, input_dict_2018_vh],
)
def test_insar_preprocessing(input_dict, auto_title):
    script = "OpenEO_insar_preprocessing.py"
    input_base64_json = base64.b64encode(json.dumps(input_dict).encode("utf8")).decode("ascii")

    tmp_dir = Path(auto_title.replace("tests/", "tests/tmp_"))
    tmp_dir.mkdir(exist_ok=True)

    exec_proc(["python", repository_root / script, input_base64_json], cwd=tmp_dir)
