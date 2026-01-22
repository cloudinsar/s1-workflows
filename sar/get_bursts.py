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

start_time = datetime.now()

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if os.path.isfile(arg):
        input_dict = json.loads(Path(arg).read_text())
    else:
        input_dict = json.loads(base64.b64decode(arg.encode("utf8")).decode("utf8"))
else:
    # print("Using debug arguments!")
    input_dict = input_dict_2024_vv_parallel

# default_dict = {
#     "polarization": "vv",
#     "sub_swath": "IW3",
#     "coherence_window_rg": 10,
#     "coherence_window_az": 2,
# }
input_dict = {k: v for k, v in input_dict.items() if v is not None}
# input_dict = {**default_dict, **input_dict}  # merge with defaults
# print(input_dict)

start_date = input_dict["temporal_extent"][0] #TODO: date must be in the correct format, since later we append T00...
end_date = input_dict["temporal_extent"][1]

s1_bursts = retrieve_bursts_with_id_and_iw(
    start_date,
    end_date,
    input_dict["polarization"],
    input_dict["burst_id"],
    input_dict["sub_swath"]
)

dates = [datetime.strptime(b['BeginningDateTime'][:10], "%Y-%m-%d") for b in s1_bursts]
dates.sort()
InSARpairs = []
for date_ref in dates:
    for date_sec in dates:
        if (date_ref - date_sec).days == -input_dict["temporal_baseline"]:
            InSARpairs.append([
                datetime.strftime(date_ref, "%Y-%m-%d"),
                datetime.strftime(date_sec, "%Y-%m-%d")
            ])
input_dict["InSAR_pairs"] = InSARpairs

result_folder = Path.cwd().absolute()
# result_folder = repo_directory / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = Path("/tmp/insar")
tmp_insar.mkdir(parents=True, exist_ok=True)

with open(result_folder / "insar_pairs_inputs.json","w") as f:
    json.dump(input_dict,f)
