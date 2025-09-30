#!/usr/bin/env python3
import base64
import glob
import os
import subprocess
import sys
import urllib.parse
import urllib.request

import simple_stac_builder
import tiff_to_gtiff
from workflow_utils import *

start_time = datetime.now()

if len(sys.argv) > 1:
    input_dict = json.loads(base64.b64decode(sys.argv[1].encode("utf8")).decode("utf8"))
else:
    print("Using debug arguments!")
    input_dict = input_dict_2018_vh

if not input_dict.get("polarization"):
    input_dict["polarization"] = "vv"
if not input_dict.get("sub_swath"):
    input_dict["sub_swath"] = "IW3"
if not "coherence_window_rg" in input_dict or not "coherence_window_az" in input_dict:
    print("Setting default coherence window size")
    input_dict["coherence_window_rg"] = 10
    input_dict["coherence_window_az"] = 2
print(input_dict)
start_date = min([min(pair) for pair in input_dict["InSAR_pairs"]])
end_date = max([max(pair) for pair in input_dict["InSAR_pairs"]])

primary_dates = [pair[0] for pair in input_dict["InSAR_pairs"]]
primary_dates_duplicates = set([d for d in primary_dates if primary_dates.count(d) > 1])
if primary_dates_duplicates:
    raise ValueError(
        f"Duplicate primary date(s) found in InSAR_pairs: {primary_dates_duplicates}. "
        "You can load multiple primary dates over multiple processes if needed."
    )

# __file__ could have exotic values in Docker:
# __file__ == /src/./OpenEO_insar.py
# __file__ == //./src/OpenEO_insar.py
# So we do a lot of normalisation:
containing_folder = os.path.dirname(os.path.normpath(__file__).replace("//", "/"))
containing_folder = Path(containing_folder).absolute()
print("containing_folder: " + str(containing_folder))
result_folder = Path.cwd().absolute()
# result_folder = containing_folder / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = Path("/tmp/insar")
tmp_insar.mkdir(parents=True, exist_ok=True)

https_request = (
        f"https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts?$filter="
        + urllib.parse.quote(
    f"ContentDate/Start ge {start_date}T00:00:00.000Z and ContentDate/Start le {end_date}T23:59:59.000Z and "
    f"PolarisationChannels eq '{input_dict['polarization'].upper()}' and "
    f"BurstId eq {input_dict['burst_id']} and "
    f"SwathIdentifier eq '{input_dict['sub_swath'].upper()}'"
)
        + "&$top=1000"
)
print(https_request)
with urllib.request.urlopen(https_request) as response:
    bursts = json.loads(response.read().decode())

flattened_pairs = set()
for pair in input_dict["InSAR_pairs"]:
    for date in pair:
        flattened_pairs.add(parse_date(date).date())
burst_paths = []
for burst in bursts["value"]:
    begin = parse_date(burst["BeginningDateTime"]).date()
    end = parse_date(burst["EndingDateTime"]).date()
    if begin not in flattened_pairs and end not in flattened_pairs:
        print(f"Skipping burst {burst['BurstId']} ({begin} - {end})")
        continue
    # Allow for relative imports:
    os.environ["PATH"] = os.environ["PATH"] + ":" + str(containing_folder / "utilities")
    cmd = [
        "bash",
        "sentinel1_burst_extractor.sh",
        "-n", burst["ParentProductName"],
        "-p", input_dict["polarization"].lower(),
        "-s", str(input_dict["sub_swath"].lower()),
        "-r", str(input_dict["burst_id"]),
        "-o", str(tmp_insar),
    ]
    _, output = exec_proc(cmd, cwd=containing_folder / "utilities")
    # get paths from stdout:
    needle = "out_path: "
    bursts_from_output = sorted(
        [Path(line[len(needle):]).absolute() for line in output.split("\n") if line.startswith(needle)]
    )
    burst_paths.extend(bursts_from_output)
    print("seconds since start: " + str((datetime.now() - start_time).seconds))

    if len(bursts_from_output) == 0:
        raise Exception("No files found in command output: " + str(output))

print(f"{burst_paths=!r}")

# GPT means "Graph Processing Toolkit" in this context
if subprocess.run(["which", "gpt"]).returncode != 0 and os.path.exists("/usr/local/esa-snap/bin/gpt"):
    print("adding SNAP to PATH")  # needed when running outside of docker
    os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/esa-snap/bin"

asset_paths = []

for pair in input_dict["InSAR_pairs"]:
    mst_filename = next(filter(lambda x: pair[0].replace("-", "") in str(x), burst_paths))
    slv_filename = next(filter(lambda x: pair[1].replace("-", "") in str(x), burst_paths))

    output_filename_tmp = f"{result_folder}/tmp_S1_coh_2images_{date_from_burst(mst_filename)}_{date_from_burst(slv_filename)}.tif"

    if not os.path.exists(output_filename_tmp):
        gpt_cmd = [
            "gpt",
            "-J-Xmx14G",
            str(containing_folder / "notebooks/graphs/coh_2images_GeoTiff.xml"),
            f"-Pmst_filename={mst_filename}",
            f"-Pslv_filename={slv_filename}",
            f"-PcohWinRg={input_dict['coherence_window_rg']}",
            f"-PcohWinAz={input_dict['coherence_window_az']}",
            f"-Ppolarisation={input_dict['polarization'].upper()}",
            f"-Poutput_filename={output_filename_tmp}",
        ]
        exec_proc(gpt_cmd, write_output=False)

    output_filename = f"{result_folder}/S1_coh_2images_{date_from_burst(mst_filename)}_{date_from_burst(slv_filename)}.tif"
    asset_paths.append(output_filename)
    if not os.path.exists(output_filename):
        tiff_to_gtiff.tiff_to_gtiff(output_filename_tmp, output_filename)

# slow when running outside Docker, because the whole home directory is scanned.
simple_stac_builder.generate_catalog(
    result_folder,
    files=asset_paths,
)

print("seconds since start: " + str((datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = list(result_folder.glob("*2images*"))
for file in files:
    # Docker often runs as root, this makes it easier to work with the files as a standard user:
    subprocess.call(["chmod", "777", str(file)])

print("Files in target dir: " + str(files))
