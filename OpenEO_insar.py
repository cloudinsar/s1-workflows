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
            "north": 46.749,
        },
        "temporal_extent": ["2024-08-14", "2024-08-26"],
    }
print(input_dict)
print("AWS_ACCESS_KEY_ID= " + str(os.environ.get("AWS_ACCESS_KEY_ID", None)))

center_point = (
    (input_dict["spatial_extent"]["west"] + input_dict["spatial_extent"]["east"]) / 2,
    (input_dict["spatial_extent"]["south"] + input_dict["spatial_extent"]["north"]) / 2,
)
argument_list = [
    "-s", input_dict["temporal_extent"][0],
    "-e", input_dict["temporal_extent"][1],
    # TODO: Specify spatial extent instead of point
    "-x", str(center_point[0]),
    "-y", str(center_point[1]),
    "-p", "vv",
    "-S", "IW3",  # TODO: Dynamically determine sub-swat
]
containing_folder = Path(os.path.dirname(__file__))

result_folder = Path.home()
# tmp_insar = Path("/tmp/insar") # TODO: No need to write tmp results to mount
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

# Allow for relative imports:
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

gpt_cmd = [
    "gpt",
    "/src/graphs/pre-processing_stackOverview_2images_GeoTiff.xml",
    f"-Pinput1={bursts[0]}",
    f"-Pinput2={bursts[1]}",
    f"-PstackOverview_filename={result_folder}/stackOverview_2images.json",
    f"-PcoregisteredStack_filename={result_folder}/Orb_Stack_2images",
]
print(gpt_cmd)
subprocess.run(gpt_cmd, check=True, stderr=subprocess.STDOUT)
print("seconds since start: " + str((datetime.datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = glob.glob(str(result_folder / "*.*"))
print("Files in target dir: " + str(files))
