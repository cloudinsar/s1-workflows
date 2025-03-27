#!/usr/bin/env python3
import base64
import glob
import json
import subprocess
import sys
import os
import datetime
from pathlib import Path

import simple_stac_builder

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
# result_folder = Path("/tmp/insar")
# result_folder.mkdir(parents=True, exist_ok=True)
tmp_insar = result_folder

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

if subprocess.run(["which", "gpt"]).returncode != 0 and os.path.exists(
        "/usr/local/esa-snap/bin/gpt"
):
    print("adding SNAP to PATH")  # needed when running outside of docker
    os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/esa-snap/bin"


def date_from_burst(burst_path):
    return Path(burst_path).parent.name.split("_")[2]


gpt_cmd = [
    "gpt",
    "./notebooks/graphs/coh_2images_GeoTiff.xml",
    f"-Pmst_filename={bursts[0]}",
    f"-Pslv_filename={bursts[1]}",
    f"-Poutput_filename={result_folder}/S1_coh_2images_{date_from_burst(bursts[0])}_{date_from_burst(bursts[1])}.tif",
]
print(gpt_cmd)
subprocess.run(gpt_cmd, check=True, stderr=subprocess.STDOUT)

# slow when running outside Docker, because whole home directory is scanned.
simple_stac_builder.generate_catalog(result_folder)

print("seconds since start: " + str((datetime.datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = glob.glob(str(result_folder / "*.*"))
print("Files in target dir: " + str(files))
