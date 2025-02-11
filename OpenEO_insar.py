#!/usr/bin/env python3
import base64
import glob
import json
import subprocess
import sys
import os
import datetime
from pathlib import Path

start_time = datetime.datetime.now()

argument_list = sys.argv[1:]

if len(argument_list) > 0:
    input_dict = json.loads(base64.b64decode(argument_list[0].encode("utf8")).decode("utf8"))
else:
    input_dict = {
        "message": "These are example arguments",
        "spatial_extent": {
            "west": 10.751,
            "south": 46.741,
            "east": 10.759,
            "north": 46.749
        },
        "temporal_extent": [
            "2024-08-14",
            "2024-08-26"
        ]
    }
print(input_dict)
print("AWS_ACCESS_KEY_ID= " + str(os.environ.get("AWS_ACCESS_KEY_ID", None)))  # Don't print AWS_SECRET_ACCESS_KEY

argument_list = [
    "-s", input_dict["temporal_extent"][0],
    "-e", input_dict["temporal_extent"][1],
    # TODO: Specify spatial extent instead of point
    "-x", str((input_dict["spatial_extent"]["west"] + input_dict["spatial_extent"]["east"]) / 2),
    "-y", str((input_dict["spatial_extent"]["south"] + input_dict["spatial_extent"]["north"]) / 2),
    "-p", "vv",
    "-S", "IW3"  # TODO: Dynamically determine sub-swat
]
containing_folder = Path(os.path.dirname(__file__))

# result_folder = containing_folder / "result"
# result_folder.mkdir(parents=True, exist_ok=True)
# result_folder = Path("/home/ubuntu")
result_folder = Path.home()
# tmp_insar = Path("/tmp/insar")
# tmp_insar.mkdir(parents=True, exist_ok=True)
tmp_insar = result_folder

with open(result_folder / "output.txt", "w") as f:
    f.write(json.dumps(input_dict))

if "-o" in argument_list:
    index_of_o = argument_list.index("-o")
    # print("Ignoring -o parameter")
    # argument_list = argument_list[:index_of_o] + argument_list[index_of_o + 2:]
    if argument_list[index_of_o + 1] != "/home/ubuntu":
        raise Exception("Only /home/ubuntu is allowed as output folder")
else:
    argument_list = ["-o", str(tmp_insar)] + argument_list

# assert not any(tmp_insar.iterdir())
# cmd = [str(containing_folder /"utilities/sentinel1_burst_extractor_spatiotemporal.sh")] + argument_list
os.environ["PATH"] = os.environ["PATH"] + ":" + str(containing_folder / "utilities")
cmd = ["sentinel1_burst_extractor_spatiotemporal.sh"] + argument_list
print(cmd)
subprocess.run(cmd, check=True, cwd=containing_folder / "utilities", stderr=subprocess.STDOUT)

print("seconds since start: " + str((datetime.datetime.now() - start_time).seconds))

# GPT means "Graph Processing Toolkit" in this context
glob_str = str(tmp_insar / "*/manifest.safe")
bursts = glob.glob(glob_str)
if len(bursts) == 0:
    raise Exception("No files found with glob: " + glob_str)

input1 = bursts[0]
input2 = bursts[1]
# bursts_relative = [str(Path(burst).relative_to(tmp_insar)) for burst in bursts]
# iw_component = bursts_relative[0].split("_")[4]
# input1 = tmp_insar / "S1A_SLC_20240814T171550_030345_IW3_VV_441043.SAFE/manifest.safe"
# input2 = tmp_insar / "S1A_SLC_20240826T171550_030345_IW3_VV_442708.SAFE/manifest.safe"
# input1 = tmp_insar / "S1A_SLC_20240814T171550_030345_IW3_VV_042880.SAFE/manifest.safe"
# input2 = tmp_insar / "S1A_SLC_20240826T171550_030345_IW3_VV_043168.SAFE/manifest.safe"
# ('-Pinput1=/home/ubuntu/S1A_SLC_20240814T171550_030345_IW3_VV_441043.SAFE/manifest.safe',
#  '-Pinput2=/home/ubuntu/S1A_SLC_20240825T052728_359500_IW2_VV_442501.SAFE/manifest.safe',)

gpt_cmd = [
    "gpt",
    "/src/graphs/pre-processing_stackOverview_2images_GeoTiff.xml",
    f"-Pinput1={input1}", f"-Pinput2={input2}",
    f"-PstackOverview_filename={result_folder}/stackOverview_2images.json",
    f"-PcoregisteredStack_filename={result_folder}/Orb_Stack_2images"
]
print(gpt_cmd)
subprocess.run(gpt_cmd, check=True, stderr=subprocess.STDOUT)
print("seconds since start: " + str((datetime.datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = glob.glob(str(result_folder / "*.*"))
print("Files in target dir: " + str(files))
