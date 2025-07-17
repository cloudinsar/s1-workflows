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
    # input_dict = {
    #     "message": "These are example arguments",
    #     "burst_id": 249435,
    #     "sub_swath": "IW2",
    #     "temporal_extent": ["2024-08-09", "2024-09-02"],
    #     "master_date": "2024-08-09",
    #     "polarization": "vv",
    # }
    input_dict = {
        "message": "These are example arguments to match SAR2Cube_openEO_examples_coherence_boxcar",
        "burst_id": 329488,
        "sub_swath": "IW2",
        "temporal_extent": ["2018-01-26", "2018-02-09"],
        "master_date": "2018-01-28",
        "polarization": "vh",
    }
if not input_dict.get("polarization"):
    input_dict["polarization"] = "vv"
if not input_dict.get("sub_swath"):
    input_dict["sub_swath"] = "IW3"
assert (len(input_dict["temporal_extent"]) == 2), "temporal_extent should be a list with two dates"
print(input_dict)

print("AWS_ACCESS_KEY_ID= " + str(os.environ.get("AWS_ACCESS_KEY_ID", None)))
if "AWS_ACCESS_KEY_ID" not in os.environ:
    raise Exception("AWS_ACCESS_KEY_ID should be set in environment")

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

# lat = 37.12  # Used to find the burst
# lon = -6.0
https_request = (
    f"https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts?$filter="
    + urllib.parse.quote(
        f"ContentDate/Start ge {input_dict['temporal_extent'][0]}T00:00:00.000Z and ContentDate/Start le {input_dict['temporal_extent'][1]}T23:59:59.000Z and "
        f"PolarisationChannels eq '{input_dict['polarization'].upper()}' and "
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
    os.environ["PATH"] = os.environ["PATH"] + ":" + str(containing_folder / "utilities")

    cmd = [
        "sentinel1_burst_extractor.sh",
        "-n", burst["ParentProductName"],
        "-p", input_dict["polarization"].lower(),
        "-s", str(input_dict["sub_swath"].lower()),
        "-r", str(input_dict["burst_id"]),
        "-o", str(result_folder),
    ]
    print(cmd)
    output = subprocess.check_output(cmd, cwd=containing_folder / "utilities", stderr=subprocess.STDOUT)
    # get paths from stdout:
    needle = "out_path: "
    bursts_from_output = sorted(
        [
            Path(line[len(needle) :]).absolute()
            for line in output.decode("utf-8").split("\n")
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
if subprocess.run(["which", "gpt"]).returncode != 0 and os.path.exists(
    "/usr/local/esa-snap/bin/gpt"
):
    print("adding SNAP to PATH")  # needed when running outside of docker
    os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/esa-snap/bin"

input_mst_date = parse_date(input_dict["master_date"])
mst_filename = next(
    filter(lambda x: input_mst_date.strftime("%Y%m%d") in str(x), burst_paths), None
)
if mst_filename is None:
    raise FileNotFoundError("No burst found for master date: " + str(input_mst_date))
mst_date = parse_date(date_from_burst(mst_filename))
mst_bandname = f'{input_dict["sub_swath"].upper()}_{input_dict["polarization"].upper()}_mst_{mst_date.strftime("%d%b%Y")}'

burst_paths.remove(mst_filename)  # don't let master and slave be the same

#####################################################################
# First image is a special case #####################################
#####################################################################
slv_filename = burst_paths[0]
slv_date = parse_date(date_from_burst(slv_filename))
slv_bandname = f'{input_dict["sub_swath"].upper()}_{input_dict["polarization"].upper()}_slv1_{slv_date.strftime("%d%b%Y")}'
# Avoid "2images" in the name here:
output_mst_filename_tmp = (
    f"{result_folder}/tmp_mst_{mst_date.strftime('%Y%m%dT%H%M%S')}.tif"
)
output_slv_filename_tmp = (
    f"{result_folder}/tmp_slv_{slv_date.strftime('%Y%m%dT%H%M%S')}.tif"
)
if not os.path.exists(output_mst_filename_tmp) or not os.path.exists(
    output_slv_filename_tmp
):
    gpt_cmd = [
        "gpt",
        "-J-Xmx14G",
        str(
            containing_folder
            / "notebooks/graphs/pre-processing_2images_SaveMst_GeoTiff.xml"
        ),
        f"-Pmst_filename={mst_filename}",
        f"-Pslv_filename={slv_filename}",
        f"-Ppolarisation={input_dict['polarization'].upper()}",
        f"-Pi_q_mst_bandnames=i_{mst_bandname},q_{mst_bandname}",
        f"-Pi_q_slv_bandnames=i_{slv_bandname},q_{slv_bandname}",
        f"-Poutput_mst_filename={output_mst_filename_tmp}",
        f"-Poutput_slv_filename={output_slv_filename_tmp}",
    ]
    print(gpt_cmd)
    subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)

output_mst_filename = (
    f"{result_folder}/S1_2images_{mst_date.strftime('%Y%m%dT%H%M%S')}.tif"
)
output_slv_filename = (
    f"{result_folder}/S1_2images_{slv_date.strftime('%Y%m%dT%H%M%S')}.tif"
)

slave_paths = [output_slv_filename]
if not os.path.exists(output_mst_filename) or not os.path.exists(output_slv_filename):
    tiff_to_gtiff.tiff_to_gtiff(output_mst_filename_tmp, output_mst_filename)
    tiff_to_gtiff.tiff_to_gtiff(output_slv_filename_tmp, output_slv_filename)
# TODO: Delete tmp files


#####################################################################
# Now the rest of the images ########################################
#####################################################################
for burst_path in burst_paths[1:]:
    slv_filename = burst_path
    slv_date = parse_date(date_from_burst(slv_filename))
    slv_bandname = f'{input_dict["sub_swath"].upper()}_{input_dict["polarization"].upper()}_slv1_{slv_date.strftime("%d%b%Y")}'
    # Avoid "2images" in the name here:
    output_slv_filename_tmp = (
        f"{result_folder}/tmp_slv_{slv_date.strftime('%Y%m%dT%H%M%S')}.tif"
    )

    if not os.path.exists(output_slv_filename_tmp):
        gpt_cmd = [
            "gpt",
            "-J-Xmx14G",
            str(
                containing_folder
                / "notebooks/graphs/pre-processing_2images_SaveOnlySlv_GeoTiff.xml"
            ),
            f"-Pmst_filename={mst_filename}",
            f"-Pslv_filename={slv_filename}",
            f"-Ppolarisation={input_dict['polarization'].upper()}",
            f"-Pi_q_slv_bandnames=i_{slv_bandname},q_{slv_bandname}",
            f"-Poutput_slv_filename={output_slv_filename_tmp}",
        ]
        print(gpt_cmd)
        subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)

    output_slv_filename = (
        f"{result_folder}/S1_2images_{slv_date.strftime('%Y%m%dT%H%M%S')}.tif"
    )

    slave_paths.append(output_slv_filename)
    if not os.path.exists(output_slv_filename):
        tiff_to_gtiff.tiff_to_gtiff(output_slv_filename_tmp, output_slv_filename)
    # TODO: Delete tmp files

# slow when running outside Docker, because the whole home directory is scanned.
simple_stac_builder.generate_catalog(
    result_folder,
    files=[output_mst_filename],
    collection_filename="S1_2images_collection_master.json",
    date_regex=re.compile(r".*_(?P<date1>\d{8}(T\d{6})?)\.tif$"),
)
simple_stac_builder.generate_catalog(
    result_folder,
    files=slave_paths,
    collection_filename="S1_2images_collection_slaves.json",
    date_regex=re.compile(r".*_(?P<date1>\d{8}(T\d{6})?)\.tif$"),
)

print("seconds since start: " + str((datetime.now() - start_time).seconds))

# CWL Will find the result files in HOME or CD

files = list(result_folder.glob("*2images*"))
for file in files:
    # Docker often runs as root, this makes it easier to work with the files as a standard user:
    subprocess.call(["chmod", "777", str(file)])

print("Files in target dir: " + str(files))
