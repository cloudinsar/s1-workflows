#!/usr/bin/env python3
import base64
import glob
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from utils import simple_stac_builder
from utils import tiff_to_gtiff
from utils.workflow_utils import *

start_time = datetime.now()

if len(sys.argv) > 1:
    input_dict = json.loads(base64.b64decode(sys.argv[1].encode("utf8")).decode("utf8"))
else:
    print("Using debug arguments!")
    # input_dict = input_dict_2018_vh_preprocessing
    input_dict = {
        "burst_id": 234893,
        "master_date": "2024-08-09",
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


mst_date: Optional[datetime] = None
for pol in input_dict["polarization"]:
    https_request = (
            f"https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts?$filter="
            + urllib.parse.quote(
        f"ContentDate/Start ge {input_dict['temporal_extent'][0]}T00:00:00.000Z and ContentDate/Start le {input_dict['temporal_extent'][1]}T23:59:59.000Z and "
        f"PolarisationChannels eq '{pol.upper()}' and "
        f"BurstId eq {input_dict['burst_id']} and "
        # f"(OData.CSC.Intersects(Footprint=geography'SRID=4326;POINT ({lon} {lat})')) and "
        f"SwathIdentifier eq '{input_dict['sub_swath'].upper()}'"
    )
            + "&$top=1000"
    )
    print(https_request)
    with urllib.request.urlopen(https_request) as response:
        bursts = json.loads(response.read().decode())

    burst_paths = []
    for burst in bursts["value"]:
        # Allow for relative imports:
        os.environ["PATH"] = os.environ["PATH"] + ":" + str(repo_directory / "utilities")

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

    # GPT means "Graph Processing Toolkit" in this context
    if subprocess.run(["which", "gpt"]).returncode != 0 and os.path.exists("/usr/local/esa-snap/bin/gpt"):
        print("adding SNAP to PATH")  # needed when running outside of docker
        os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/esa-snap/bin"

    input_mst_date = parse_date(input_dict["master_date"])
    mst_filename = next(filter(lambda x: input_mst_date.strftime("%Y%m%d") in str(x), burst_paths), None)
    if mst_filename is None:
        raise FileNotFoundError("No burst found for master date: " + str(input_mst_date))
    mst_date = parse_date(date_from_burst(mst_filename))
    mst_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_mst_{mst_date.strftime("%d%b%Y")}'

    burst_paths.remove(mst_filename)  # don't let master and slave be the same

    #####################################################################
    # First image is a special case #####################################
    #####################################################################
    slv_filename = burst_paths[0]
    slv_date = parse_date(date_from_burst(slv_filename))
    slv_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_slv1_{slv_date.strftime("%d%b%Y")}'
    # Avoid "2images" in the name here:
    output_mst_filename_tmp = (
        f"{result_folder}/tmp_mst_{mst_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}.tif"
    )
    output_slv_filename_tmp = (
        f"{result_folder}/tmp_slv_{slv_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}.tif"
    )
    if not os.path.exists(output_mst_filename_tmp) or not os.path.exists(
            output_slv_filename_tmp
    ):
        gpt_cmd = [
            "gpt",
            "-J-Xmx14G",
            str(
                repo_directory
                / "notebooks/graphs/pre-processing_2images_SaveMst_GeoTiff.xml"
            ),
            f"-Pmst_filename={mst_filename}",
            f"-Pslv_filename={slv_filename}",
            f"-Ppolarisation={pol.upper()}",
            f"-Pi_q_mst_bandnames=i_{mst_bandname},q_{mst_bandname}",
            f"-Pi_q_slv_bandnames=i_{slv_bandname},q_{slv_bandname}",
            f"-Poutput_mst_filename={output_mst_filename_tmp}",
            f"-Poutput_slv_filename={output_slv_filename_tmp}",
        ] + snap_extra_arguments
        print(gpt_cmd)
        subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)

    output_mst_filename = f"{result_folder}/S1_2images_mst_{mst_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}_<band_name>.tif"
    output_slv_filename = f"{result_folder}/S1_2images_slv_{slv_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}_<band_name>.tif"

    if not os.path.exists(output_mst_filename) or not os.path.exists(output_slv_filename):
        add_to_date_dict(mst_date,
                         tiff_to_gtiff.tiff_to_gtiff(output_mst_filename_tmp, output_mst_filename, tiff_per_band=True))
        add_to_date_dict(slv_date,
                         tiff_to_gtiff.tiff_to_gtiff(output_slv_filename_tmp, output_slv_filename, tiff_per_band=True))
    # TODO: Delete tmp files

    #####################################################################
    # Now the rest of the images ########################################
    #####################################################################
    for burst_path in burst_paths[1:]:
        slv_filename = burst_path
        slv_date = parse_date(date_from_burst(slv_filename))
        slv_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_slv1_{slv_date.strftime("%d%b%Y")}'
        # Avoid "2images" in the name here:
        output_slv_filename_tmp = (
            f"{result_folder}/tmp_slv_{slv_date.strftime('%Y%m%dT%H%M%S')}_{pol.lower()}.tif"
        )

        if not os.path.exists(output_slv_filename_tmp):
            gpt_cmd = [
                "gpt",
                "-J-Xmx14G",
                str(
                    repo_directory
                    / "notebooks/graphs/pre-processing_2images_SaveOnlySlv_GeoTiff.xml"
                ),
                f"-Pmst_filename={mst_filename}",
                f"-Pslv_filename={slv_filename}",
                f"-Ppolarisation={pol.upper()}",
                f"-Pi_q_slv_bandnames=i_{slv_bandname},q_{slv_bandname}",
                f"-Poutput_slv_filename={output_slv_filename_tmp}",
            ] + snap_extra_arguments
            print(gpt_cmd)
            subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)

        output_slv_filename = (
            f"{result_folder}/S1_2images_slv_{slv_date.strftime('%Y%m%dT%H%M%S')}_<band_name>.tif"
        )

        if not os.path.exists(output_slv_filename):
            add_to_date_dict(slv_date,
                             tiff_to_gtiff.tiff_to_gtiff(output_slv_filename_tmp, output_slv_filename,
                                                         tiff_per_band=True)
                             )
        # TODO: Delete tmp files

# date_to_output_paths = {datetime(2024, 8, 9, 5, 59, 7).date(): ['/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vv_i_VV.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vv_q_VV.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vv_grid_lat.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vv_grid_lon.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vh_i_VH.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vh_q_VH.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vh_grid_lat.tif',
#                                            '/home/emile/openeo/s1-workflows/S1_2images_mst_20240809T055907_vh_grid_lon.tif'],
#  datetime(2024, 8, 21, 5, 59, 7).date(): [
#      '/home/emile/openeo/s1-workflows/S1_2images_slv_20240821T055907_vv_i_VV.tif',
#      '/home/emile/openeo/s1-workflows/S1_2images_slv_20240821T055907_vv_q_VV.tif',
#      '/home/emile/openeo/s1-workflows/S1_2images_slv_20240821T055907_vh_i_VH.tif',
#      '/home/emile/openeo/s1-workflows/S1_2images_slv_20240821T055907_vh_q_VH.tif']}
# TODO: Assert latlon are the same for all polarizations
# remove latlon bands from master date:
mst_output_paths_element = date_to_output_paths.get(mst_date)
if len(input_dict["polarization"]) > 1:
    # remove elements matching  "_" + input_dict["polarization"][0] + "_grid_"
    mst_output_paths_element = [
        path for path in mst_output_paths_element if f"_{input_dict['polarization'][0]}_grid_" not in str(path)
    ]
    date_to_output_paths[mst_date] = mst_output_paths_element
latlon_band_files = [path for path in mst_output_paths_element if "_grid_" in str(path)]
assert len(latlon_band_files) == 2

for date in date_to_output_paths:
    if date == mst_date:
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
