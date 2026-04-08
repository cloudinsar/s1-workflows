#!/usr/bin/env python3
import base64
import os
import subprocess
import sys
import json

from sar.utils import simple_stac_builder
from sar.utils import tiff_to_gtiff
from sar.utils.workflow_utils import *

setup_insar_environment()

_log = logging.getLogger(__name__)

start_time = datetime.now()

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if os.path.isfile(arg):
        input_dict = json.loads(Path(arg).read_text())
    else:
        input_dict = json.loads(base64.b64decode(arg.encode("utf8")).decode("utf8"))
else:
    _log.info("Using debug arguments!")
    # input_dict = json.loads((repo_directory / "sar/example_inputs/input_dict_whole_2023_new.json").read_text())
    # input_dict = json.loads((repo_directory / "sar/example_inputs/input_dict_2018_vh_new.json").read_text())
    input_dict = json.loads((repo_directory / "sar/example_inputs/input_dict_2024_vv_new.json").read_text())

input_dict = {k: v for k, v in input_dict.items() if v is not None}
_log.info(f"{input_dict=}")

start_date = input_dict["temporal_extent"][0]  # TODO: date must be in the correct format, since later we append T00...
end_date = input_dict["temporal_extent"][1]

s1_bursts = retrieve_bursts_with_id_and_iw(
    start_date,
    end_date,
    input_dict.get("polarization"),
    sbswath=input_dict.get("sub_swath"),
    burst_id=input_dict.get("burst_id"),
    spatial_extent=input_dict.get("spatial_extent"),
)

dates = [datetime.strptime(b["BeginningDateTime"][:10], "%Y-%m-%d") for b in s1_bursts]
dates.sort()
InSARpairs = []
for date_ref in dates:
    for date_sec in dates:
        if (date_ref - date_sec).days == -input_dict["temporal_baseline"]:
            InSARpairs.append([
                datetime.strftime(date_ref, "%Y-%m-%d"),
                datetime.strftime(date_sec, "%Y-%m-%d")
            ])

if len(InSARpairs) == 0:
    if "T00:00:00" in end_date:
        raise ValueError(
            f"Not enough bursts found to make pairs. Is the end time intentionally put in the very beginning of that day? End date: '{end_date}'")
    else:
        raise ValueError(f"Not enough bursts found to make pairs for the given parameters: {input_dict}")

input_dict["InSAR_pairs"] = InSARpairs

result_folder = Path.cwd().absolute()
# result_folder = repo_directory / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = Path("/tmp/insar")
tmp_insar.mkdir(parents=True, exist_ok=True)

with open(result_folder / "insar_pairs_inputs.json", "w") as f:
    json.dump(input_dict, f, indent=2)
    _log.info("Written: " + f.name)
