#!/usr/bin/env python3
import base64
import glob
import os
import subprocess
import sys
import urllib.request
from typing import Any, Dict, Optional
from datetime import datetime

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
    print("Using debug arguments!")
    # input_dict = input_dict_2018_vh_preprocessing
    input_dict = {
        "burst_id": 234893,
        "primary_date": "2024-09-02",
        "polarization": ["vv", "vh"],
        "sub_swath": "IW1",
        "temporal_extent": ["2024-08-09", "2024-08-21"],
    }

if not input_dict.get("polarization"):
    input_dict["polarization"] = ["vv", "vh"]
elif isinstance(input_dict.get("polarization"), str):
    input_dict["polarization"] = [input_dict.get("polarization")]
if not input_dict.get("sub_swath"):
    input_dict["sub_swath"] = "IW3"
assert len(input_dict["temporal_extent"]) == 2, "temporal_extent should be a list with two dates"
print(input_dict)

result_folder = Path.cwd().absolute()
# result_folder = repo_directory / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = Path("/tmp/insar")
tmp_insar.mkdir(parents=True, exist_ok=True)

date_to_output_paths: Dict[datetime, list] = dict()


def add_to_date_dict(date: datetime, paths: list):
    if date not in date_to_output_paths:
        date_to_output_paths[date] = []
    date_to_output_paths[date].extend(paths)


prm_date: Optional[datetime] = None
for pol in input_dict["polarization"]:

    primary_date = parse_date(input_dict["primary_date"])
    start_date = parse_date(input_dict['temporal_extent'][0])
    end_date = parse_date(input_dict['temporal_extent'][1])

    # Moved the function in workflow_utils.py
    bursts = retrieve_bursts_with_id_and_iw(input_dict['temporal_extent'][0],
                                            input_dict['temporal_extent'][1],
                                            pol,
                                            input_dict['burst_id'],
                                            input_dict['sub_swath'])

    # Check if primary date is within the provided temporal extent.
    # If not, we need do a second query to retrieve it separately.
    if (primary_date < start_date) or (primary_date > end_date):
        burst_primary = retrieve_bursts_with_id_and_iw(input_dict["primary_date"],
                                                input_dict["primary_date"],
                                                pol,
                                                input_dict['burst_id'],
                                                input_dict['sub_swath'])
        if len(burst_primary) == 0:
            raise Exception(f"No bursts found for primary_date: {input_dict['primary_date']}, burst_id: {input_dict['burst_id']}, subswath: {input_dict['sub_swath']}")
        bursts.append(burst_primary[0])

    burst_paths = []
    for burst in bursts:
        cmd = [
            "bash",
            "sentinel1_burst_extractor.sh",
            "-n", burst["ParentProductName"],
            "-p", pol.lower(),
            "-s", str(input_dict["sub_swath"].lower()),
            "-r", str(input_dict["burst_id"]),
            "-o", str(tmp_insar),
        ]
        _, output = exec_proc(cmd, cwd=repo_directory / "utilities")
        # get paths from stdout:
        needle = "out_path: "
        bursts_from_output = sorted(
            [
                Path(line[len(needle):]).absolute()
                for line in output.split("\n")
                if line.startswith(needle)
            ]
        )
        burst_paths.extend(bursts_from_output)
        print("seconds since start: " + str((datetime.now() - start_time).seconds))

        if len(bursts_from_output) == 0:
            raise Exception("No files found in command output: " + str(output))

    burst_paths = sorted(burst_paths)
    print(f"{burst_paths=!r}")

    input_prm_date = parse_date(input_dict["primary_date"])
    prm_filename = next(filter(lambda x: input_prm_date.strftime("%Y%m%d") in str(x), burst_paths), None)
    if prm_filename is None:
        raise FileNotFoundError("No burst found for primary date: " + str(input_prm_date))
    prm_date = parse_date(date_from_burst(prm_filename))
    prm_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_mst_{prm_date.strftime("%d%b%Y")}'

    burst_paths.remove(prm_filename)  # don't let primary and secondary be the same

    #####################################################################
    # First image is a special case #####################################
    #####################################################################
    sec_filename = burst_paths[0]
    sec_date = parse_date(date_from_burst(sec_filename))
    sec_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_slv1_{sec_date.strftime("%d%b%Y")}'
    # Avoid "2images" in the name here:
    output_prm_filename_tmp = (
        f"{result_folder}/tmp_prm_{prm_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}.tif"
    )
    output_sec_filename_tmp = (
        f"{result_folder}/tmp_sec_{sec_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}.tif"
    )
    if not os.path.exists(output_prm_filename_tmp) or not os.path.exists(
            output_sec_filename_tmp
    ):
        gpt_cmd = [
            "gpt",
            str(
                repo_directory
                / "notebooks/graphs/pre-processing_2images_SavePrm_GeoTiff.xml"
            ),
            f"-Pprm_filename={prm_filename}",
            f"-Psec_filename={sec_filename}",
            f"-Ppolarisation={pol.upper()}",
            f"-Pi_q_prm_bandnames=i_{prm_bandname},q_{prm_bandname}",
            f"-Pi_q_sec_bandnames=i_{sec_bandname},q_{sec_bandname}",
            f"-Poutput_prm_filename={output_prm_filename_tmp}",
            f"-Poutput_sec_filename={output_sec_filename_tmp}",
        ] + snap_extra_arguments
        print(gpt_cmd)
        subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)

    output_prm_filename = f"{result_folder}/S1_2images_prm_{prm_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}_<band_name>.tif"
    output_sec_filename = f"{result_folder}/S1_2images_sec_{sec_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}_<band_name>.tif"

    if not os.path.exists(output_prm_filename) or not os.path.exists(output_sec_filename):
        add_to_date_dict(prm_date,
                         tiff_to_gtiff.tiff_to_gtiff(output_prm_filename_tmp, output_prm_filename, tiff_per_band=True))
        add_to_date_dict(sec_date,
                         tiff_to_gtiff.tiff_to_gtiff(output_sec_filename_tmp, output_sec_filename, tiff_per_band=True))
    # TODO: Delete tmp files

    #####################################################################
    # Now the rest of the images ########################################
    #####################################################################
    for burst_path in burst_paths[1:]:
        sec_filename = burst_path
        sec_date = parse_date(date_from_burst(sec_filename))
        sec_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_slv1_{sec_date.strftime("%d%b%Y")}'
        # Avoid "2images" in the name here:
        output_sec_filename_tmp = (
            f"{result_folder}/tmp_sec_{sec_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}.tif"
        )

        if not os.path.exists(output_sec_filename_tmp):
            gpt_cmd = [
                "gpt",
                str(
                    repo_directory
                    / "notebooks/graphs/pre-processing_2images_SaveOnlySec_GeoTiff.xml"
                ),
                f"-Pprm_filename={prm_filename}",
                f"-Psec_filename={sec_filename}",
                f"-Ppolarisation={pol.upper()}",
                f"-Pi_q_sec_bandnames=i_{sec_bandname},q_{sec_bandname}",
                f"-Poutput_sec_filename={output_sec_filename_tmp}",
            ] + snap_extra_arguments
            print(gpt_cmd)
            subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)

        output_sec_filename = (
            f"{result_folder}/S1_2images_sec_{sec_date.strftime('%Y%m%dT%H%M%S')}_<band_name>.tif"
        )

        if not os.path.exists(output_sec_filename):
            add_to_date_dict(sec_date,
                             tiff_to_gtiff.tiff_to_gtiff(output_sec_filename_tmp, output_sec_filename,
                                                         tiff_per_band=True)
                             )
        # TODO: Delete tmp files

# date_to_output_paths = {datetime(2024, 8, 9, 5, 59, 7).date(): ['/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vv_i_VV.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vv_q_VV.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vv_grid_lat.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vv_grid_lon.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vh_i_VH.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vh_q_VH.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vh_grid_lat.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_prm_20240809T055907_vh_grid_lon.tif'],
#  datetime(2024, 8, 21, 5, 59, 7).date(): [
#      '/home/emile/openeo/s1-workflows/S1_2images_sec_20240821T055907_vv_i_VV.tif',
#      '/home/emile/openeo/s1-workflows/S1_2images_sec_20240821T055907_vv_q_VV.tif',
#      '/home/emile/openeo/s1-workflows/S1_2images_sec_20240821T055907_vh_i_VH.tif',
#      '/home/emile/openeo/s1-workflows/S1_2images_sec_20240821T055907_vh_q_VH.tif']}
# TODO: Assert latlon are the same for all polarizations
# remove latlon bands from primary date:
prm_output_paths_element = date_to_output_paths.get(prm_date)
if len(input_dict["polarization"]) > 1:
    # remove elements matching  "_" + input_dict["polarization"][0] + "_grid_"
    prm_output_paths_element = [
        path for path in prm_output_paths_element if f"_{input_dict['polarization'][0]}_grid_" not in str(path)
    ]
    date_to_output_paths[prm_date] = prm_output_paths_element
latlon_band_files = [path for path in prm_output_paths_element if "_grid_" in str(path)]
assert len(latlon_band_files) == 2

for date in date_to_output_paths:
    if date == prm_date:
        continue
    output_paths_element = date_to_output_paths.get(date)
    output_paths_element.extend(latlon_band_files)

output_paths = list(date_to_output_paths.values())

simple_stac_builder.generate_catalog(
    result_folder,
    files=output_paths,
    collection_filename="collection.json",
    date_regex=re.compile(r"(?P<feature_id>.*_(?P<date1>\d{8}(T\d{6})?))(_\w+)?\.tif$"),
)

print("seconds since start: " + str((datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = list(result_folder.glob("*2images*"))
for file in files:
    # Docker often runs as root, this makes it easier to work with the files as a standard user:
    subprocess.call(["chmod", "777", str(file)])

print("Files in target dir: " + str(files))
