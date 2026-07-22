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
    # input_dict = json.loads((repo_directory / "sar/example_inputs/input_dict_2024_vv_new.json").read_text())
    input_dict = json.loads((repo_directory / "sar/example_inputs/input_dict_2018_vh_new_spatial_extent_interferogram.json").read_text())
    # input_dict = json.loads((repo_directory / "sar/example_inputs/input_dict_2024_vv_interferogram.json").read_text())
input_dict = {k: v for k, v in input_dict.items() if v is not None}
_log.info(f"{input_dict=}")

# Inputs sanity check:
# Coherence requires either burst_id and sub_swath or spatial_extent.
# Interferogram requires either burst_id, sub_swath and InSAR_pairs or spatial_extent and temporal_baseline.

use_provided_pairs = False
if input_dict.get("interferogram"):
    if input_dict.get("burst_id") and input_dict["burst_id"] is not None and input_dict.get("InSAR_pairs") and input_dict["InSAR_pairs"] is not None:
        # We can skip all the rest and return the parameters as they are
        use_provided_pairs = True
    elif input_dict.get("spatial_extent") and input_dict["spatial_extent"] is not None and input_dict.get("temporal_baseline") and input_dict["temporal_baseline"] is not None:
        # We need to automatically select the burst_id and sub_swath, generating the InSAR_pairs
        pass
    else:
        raise Exception("For interferogram generation, please provide either \n(polarization, temporal_extent, burst_id, sub_swath, InSAR_pairs) or \n(polarization, temporal_extent, spatial_extent, temporal_baseline) \nto select the burst of interest")
else:
    if input_dict.get("burst_id") and input_dict["burst_id"] is not None and input_dict.get("sub_swath") and input_dict["sub_swath"] is not None:
        pass
    elif input_dict.get("spatial_extent") and input_dict["spatial_extent"] is not None:
        # We need to automatically select the burst_id and sub_swath, generating the InSAR_pairs
        pass
    else:
        raise Exception("For coherence generation, please provide either \n(polarization, temporal_extent, temporal_baseline, burst_id, sub_swath) or \n(polarization, temporal_extent, temporal_baseline, spatial_extent) \nto select the burst of interest")
if use_provided_pairs:
    start_date = min([min(pair) for pair in input_dict["InSAR_pairs"]])
    end_date = max([max(pair) for pair in input_dict["InSAR_pairs"]])
else:
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

s1_bursts = sorted(s1_bursts, key=lambda d: d['AbsoluteBurstId'])

subswath = input_dict.get("sub_swath") if input_dict.get("sub_swath") is not None else s1_bursts[0]["SwathIdentifier"]
burst_id = input_dict.get("burst_id") if input_dict.get("burst_id") is not None else s1_bursts[0]["BurstId"]

if not use_provided_pairs:
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

input_dict["sub_swath_id"] = subswath
input_dict["burst_id"] = burst_id
result_folder = Path.cwd().absolute()
# result_folder = repo_directory / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = Path(".")
tmp_insar.mkdir(parents=True, exist_ok=True)

with open(result_folder / "insar_pairs_inputs.json", "w") as f:
    json.dump(input_dict, f, indent=2)
    _log.info("Written: " + f.name)
