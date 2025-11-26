#!/usr/bin/env python3
import base64
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import timedelta

from utils import simple_stac_builder
from utils import tiff_to_gtiff
from utils.workflow_utils import *

setup_insar_environment()

start_time = datetime.now()

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if os.path.isfile(arg):
        input_dict = json.loads(Path(arg).read_text())
    else:
        input_dict = json.loads(base64.b64decode(arg.encode("utf8")).decode("utf8"))
else:
    print("Using debug arguments!")
    # input_dict = {
    #     "temporal_extent": ["2024-08-09", "2024-08-21"],
    #     "temporal_baseline": 12,
    #     "burst_id": 234893,
    #     "polarization": "vv",
    #     "sub_swath": "IW1",
    # }
    input_dict = {
        "temporal_extent": ["2024-08-09", "2024-09-14"],
        "temporal_baseline": 12,
        "burst_id": 249435,
        # Coherence window size:
        "coherence_window_az": 2,
        "coherence_window_rg": 10,
        # Multillok parameters:
        "n_az_looks": 1,
        "n_rg_looks": 4,
        "polarization": "vv",
        "sub_swath": "IW2",
    }
default_dict = {
    "coherence_window_rg": 10,
    "coherence_window_az": 2,
}
input_dict = {k: v for k, v in input_dict.items() if v is not None}
input_dict = {**default_dict, **input_dict}  # merge with defaults
print(input_dict)
start_date = input_dict["temporal_extent"][0]
end_date = input_dict["temporal_extent"][1]

result_folder = Path.cwd().absolute()
# result_folder = repo_directory / "output"
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

burst_paths = []
for burst in bursts["value"]:
    begin = parse_date(burst["BeginningDateTime"]).date()
    end = parse_date(burst["EndingDateTime"]).date()
    cmd = [
        "bash",
        "sentinel1_burst_extractor.sh",
        "-n", burst["ParentProductName"],
        "-p", input_dict["polarization"].lower(),
        "-s", str(input_dict["sub_swath"].lower()),
        "-r", str(input_dict["burst_id"]),
        "-o", str(tmp_insar),
    ]
    _, output = exec_proc(cmd, cwd=repo_directory / "utilities", write_output=False)
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

date_to_path = {}
for f in burst_paths:
    # date = parse_date(date_from_burst(f)).date() # same
    date = datetime.strptime(os.path.basename(os.path.dirname(f)).split('_')[2][:8], "%Y%m%d")
    date_to_path[date] = f

asset_paths = []

for prm_date, prm_filename in date_to_path.items():
    sec_date = prm_date + timedelta(days=input_dict["temporal_baseline"])
    sec_filename = date_to_path.get(sec_date)
    if sec_date in date_to_path:
        # coh_filename = os.path.join(output_folder, f'coh_{prm_date.strftime("%Y%m%d")}_{sec_date.strftime("%Y%m%d")}.tif')
        output_filename_tmp = f"{result_folder}/tmp_S1_coh_2images_{date_from_burst(prm_filename)}_{date_from_burst(sec_filename)}.tif"

        if not os.path.exists(output_filename_tmp):
            gpt_cmd = [
                          "gpt",
                          str(repo_directory / "notebooks/graphs/coh_2images_GeoTiff.xml"),
                          f"-Pprm_filename={prm_filename}",
                          f"-Psec_filename={sec_filename}",
                          f"-PcohWinRg={input_dict['coherence_window_rg']}",
                          f"-PcohWinAz={input_dict['coherence_window_az']}",
                          f"-Ppolarisation={input_dict['polarization'].upper()}",
                          f"-Poutput_filename={output_filename_tmp}",
                      ] + snap_extra_arguments
            exec_proc(gpt_cmd, write_output=False)

        output_filename = Path(
            f"{result_folder}/S1_coh_2images_{date_from_burst(prm_filename)}_{date_from_burst(sec_filename)}.tif")
        asset_paths.append(output_filename)
        if not os.path.exists(output_filename):
            tiff_to_gtiff.tiff_to_gtiff(output_filename_tmp, output_filename)

# slow when running outside Docker, because the whole home directory is scanned.
simple_stac_builder.generate_catalog(
    result_folder,
    files=asset_paths,
    collection_filename="collection.json",
)

print("seconds since start: " + str((datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = list(result_folder.glob("*2images*"))
for file in files:
    # Docker often runs as root, this makes it easier to work with the files as a standard user:
    subprocess.call(["chmod", "777", str(file)])

print("Files in target dir: " + str(files))
