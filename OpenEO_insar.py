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

if len(sys.argv) > 1:
    input_dict = json.loads(base64.b64decode(sys.argv[1].encode("utf8")).decode("utf8"))
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
        "polarization": "vv",
        "sub_swath": "IW3",
    }
if not input_dict.get("polarization"):
    input_dict["polarization"] = "vv"
if not input_dict.get("sub_swath"):
    input_dict["sub_swath"] = "IW3"
print(input_dict)
print("AWS_ACCESS_KEY_ID= " + str(os.environ.get("AWS_ACCESS_KEY_ID", None)))
if "AWS_ACCESS_KEY_ID" not in os.environ:
    raise Exception("AWS_ACCESS_KEY_ID should be set in environment")

center_point = (
    (input_dict["spatial_extent"]["west"] + input_dict["spatial_extent"]["east"]) / 2,
    (input_dict["spatial_extent"]["south"] + input_dict["spatial_extent"]["north"]) / 2,
)

# __file__ could have exotic values in Docker:
# __file__ == /src/./OpenEO_insar.py
# __file__ == //./src/OpenEO_insar.py
# So we do a lot of normalisation:
containing_folder = os.path.dirname(os.path.normpath(__file__).replace("//", "/"))
containing_folder = Path(containing_folder).absolute()
print("containing_folder: " + str(containing_folder))
# result_folder = Path.home()
result_folder = Path.cwd()
# result_folder = containing_folder / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = result_folder

# Allow for relative imports:
os.environ["PATH"] = os.environ["PATH"] + ":" + str(containing_folder / "utilities")
cmd = [
    "sentinel1_burst_extractor_spatiotemporal.sh",
    "-s", input_dict["temporal_extent"][0],
    "-e", input_dict["temporal_extent"][1],
    # TODO: Specify spatial extent instead of point
    "-x", str(center_point[0]),
    "-y", str(center_point[1]),
    "-p", input_dict["polarization"],
    "-S", input_dict["sub_swath"],
    "-o", str(tmp_insar),
]
print(cmd)
output = subprocess.check_output(cmd, cwd=containing_folder / "utilities", stderr=subprocess.STDOUT)
# get paths from stdout:
needle = "out_path: "
bursts = sorted([line[len(needle):] for line in output.decode("utf-8").split("\n") if line.startswith(needle)])
print(f"{bursts=}")
print("seconds since start: " + str((datetime.datetime.now() - start_time).seconds))

# GPT means "Graph Processing Toolkit" in this context
if len(bursts) == 0:
    raise Exception("No files found in command output: " + str(output))

if subprocess.run(["which", "gpt"]).returncode != 0 and os.path.exists(
        "/usr/local/esa-snap/bin/gpt"
):
    print("adding SNAP to PATH")  # needed when running outside of docker
    os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/esa-snap/bin"


def date_from_burst(burst_path):
    return Path(burst_path).parent.name.split("_")[2]


gpt_cmd = [
    "gpt",
    str(containing_folder / "notebooks/graphs/coh_2images_GeoTiff.xml"),
    f"-Pmst_filename={bursts[0]}",
    f"-Pslv_filename={bursts[1]}",
    f"-Poutput_filename={result_folder}/S1_coh_2images_{date_from_burst(bursts[0])}_{date_from_burst(bursts[1])}.tif",
]
print(gpt_cmd)
subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)

# slow when running outside Docker, because whole home directory is scanned.
simple_stac_builder.generate_catalog(result_folder)

print("seconds since start: " + str((datetime.datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = glob.glob(str(result_folder / "*2images*"))
for file in files:
    # Docker often runs as root, this makes it easier to work with the files as a standard user:
    subprocess.call(["chmod", "777", str(file)])

print("Files in target dir: " + str(files))
