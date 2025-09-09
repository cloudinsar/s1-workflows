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
    input_dict = {
        "message": "These are example arguments",
        "burst_id": 249435,
        "sub_swath": "IW2",
        "temporal_extent": ["2024-08-09", "2024-09-02"],
        "primary_date": "2024-08-09",
        "polarization": ["vv","vh"],
    }
    # input_dict = {
    #     "message": "These are example arguments to match SAR2Cube_openEO_examples_coherence_boxcar",
    #     "burst_id": 329488,
    #     "sub_swath": "IW2",
    #     "temporal_extent": ["2018-01-26", "2018-02-09"],
    #     "primary_date": "2018-01-28",
    #     "polarization": "vh",
    # }
if not input_dict.get("polarization"):
    input_dict["polarization"] = ["vv","vh"]
elif type(input_dict.get("polarization"))==str:
    input_dict["polarization"] = [input_dict["polarization"]]

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
# Check if we need to download one or more polarizations

bursts_pol = {}
prm_filenames_pol = {}
tmp_files = []
secondary_paths = []
primary_paths = []

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
        os.environ["PATH"] = os.environ["PATH"] + ":" + str(containing_folder / "utilities")

        cmd = [
            "sentinel1_burst_extractor.sh",
            "-n", burst["ParentProductName"],
            "-p", pol.lower(),
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

    input_prm_date = parse_date(input_dict["primary_date"])
    prm_filename = next(
        filter(lambda x: input_prm_date.strftime("%Y%m%d") in str(x), burst_paths), None
    )
    if prm_filename is None:
        raise FileNotFoundError("No burst found for primary date: " + str(input_prm_date))
    prm_date = parse_date(date_from_burst(prm_filename))
    prm_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_mst_{prm_date.strftime("%d%b%Y")}'

    burst_paths.remove(prm_filename)  # don't let primary and secondary be the same
    
    prm_filenames_pol[pol] = prm_filename
    bursts_pol[pol] = burst_paths

    #####################################################################
    # First image is a special case #####################################
    #####################################################################
    sec_filename = burst_paths[0]
    sec_date = parse_date(date_from_burst(sec_filename))
    sec_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_slv1_{sec_date.strftime("%d%b%Y")}'
    # Avoid "2images" in the name here:
    output_prm_filename_tmp = (
        f"{result_folder}/tmp_prm_{prm_date.strftime('%Y%m%dT%H%M%S')}_{pol}.tif"
    )
    output_sec_filename_tmp = (
        f"{result_folder}/tmp_sec_{sec_date.strftime('%Y%m%dT%H%M%S')}_{pol}.tif"
    )
    if not os.path.exists(output_prm_filename_tmp) or not os.path.exists(
        output_sec_filename_tmp
    ):
        gpt_cmd = [
            "gpt",
            "-J-Xmx14G",
            str(
                containing_folder
                / "notebooks/graphs/pre-processing_2images_SavePrm_GeoTiff.xml"
            ),
            f"-Pprm_filename={prm_filename}",
            f"-Psec_filename={sec_filename}",
            f"-Ppolarisation={pol.upper()}",
            f"-Pi_q_prm_bandnames=i_{prm_bandname},q_{prm_bandname}",
            f"-Pi_q_sec_bandnames=i_{sec_bandname},q_{sec_bandname}",
            f"-Poutput_prm_filename={output_prm_filename_tmp}",
            f"-Poutput_sec_filename={output_sec_filename_tmp}",
        ]
        print(gpt_cmd)
        subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)
    if os.path.exists(output_sec_filename_tmp):
        secondary_paths.append(output_sec_filename_tmp)
    if os.path.exists(output_prm_filename_tmp):
        primary_paths.append(output_prm_filename_tmp)
    tmp_files.extend([output_sec_filename_tmp,output_prm_filename_tmp])

output_prm_filename = (
    f"{result_folder}/S1_2images_{prm_date.strftime('%Y%m%dT%H%M%S')}.tif"
)
output_sec_filename = (
    f"{result_folder}/S1_2images_{sec_date.strftime('%Y%m%dT%H%M%S')}.tif"
)

if not os.path.exists(output_prm_filename) or not os.path.exists(output_sec_filename):
    print("++++++++++ tiff_to_gtiff")
    print(primary_paths, output_prm_filename)
    print(secondary_paths, output_sec_filename)
    tiff_to_gtiff.tiff_to_gtiff(primary_paths, output_prm_filename)
    tiff_to_gtiff.tiff_to_gtiff(secondary_paths, output_sec_filename)

#####################################################################
# Now the rest of the images ########################################
#####################################################################
for i in range(len(burst_paths[1:])):
    secondary_paths = []
    for pol in input_dict["polarization"]:
        burst_paths = bursts_pol[pol]
        sec_filename = burst_paths[i+1]
        sec_date = parse_date(date_from_burst(sec_filename))
        sec_bandname = f'{input_dict["sub_swath"].upper()}_{pol.upper()}_slv1_{sec_date.strftime("%d%b%Y")}'
        # Avoid "2images" in the name here:
        output_sec_filename_tmp = (
            f"{result_folder}/tmp_sec_{sec_date.strftime('%Y%m%dT%H%M%S')}_{pol}.tif"
        )
        prm_filename = prm_filenames_pol[pol]
        if not os.path.exists(output_sec_filename_tmp):
            gpt_cmd = [
                "gpt",
                "-J-Xmx14G",
                str(
                    containing_folder
                    / "notebooks/graphs/pre-processing_2images_SaveOnlySec_GeoTiff.xml"
                ),
                f"-Pprm_filename={prm_filename}",
                f"-Psec_filename={sec_filename}",
                f"-Ppolarisation={pol.upper()}",
                f"-Pi_q_sec_bandnames=i_{sec_bandname},q_{sec_bandname}",
                f"-Poutput_sec_filename={output_sec_filename_tmp}",
            ]
            print(gpt_cmd)
            subprocess.check_call(gpt_cmd, stderr=subprocess.STDOUT)
        if os.path.exists(output_sec_filename_tmp):
            secondary_paths.append(output_sec_filename_tmp)
            tmp_files.append(output_sec_filename_tmp)

    output_sec_filename = (
        f"{result_folder}/S1_2images_{sec_date.strftime('%Y%m%dT%H%M%S')}.tif"
    )

    if not os.path.exists(output_sec_filename):
        print("++++++++++ tiff_to_gtiff")
        print(secondary_paths, output_sec_filename)
        tiff_to_gtiff.tiff_to_gtiff(secondary_paths, output_sec_filename)

# Delete tmp files
for f in tmp_files:
    try:
        os.remove(f)
    except Exception as e:
        print(e)

        # slow when running outside Docker, because the whole home directory is scanned.
        # simple_stac_builder.generate_catalog(
        #     result_folder,
        #     files=[output_prm_filename],
        #     collection_filename="S1_2images_collection_primary.json",
        #     date_regex=re.compile(r".*_(?P<date1>\d{8}(T\d{6})?)\.tif$"),
        # )

        # simple_stac_builder.generate_catalog(
        #     result_folder,
        #     files=secondary_paths,
        #     collection_filename="S1_2images_collection_secondary.json",
        #     date_regex=re.compile(r".*_(?P<date1>\d{8}(T\d{6})?)\.tif$"),
        # )

        # print("seconds since start: " + str((datetime.now() - start_time).seconds))

        # # CWL Will find the result files in HOME or CD

        # files = list(result_folder.glob("*2images*"))
        # for file in files:
        #     # Docker often runs as root, this makes it easier to work with the files as a standard user:
        #     subprocess.call(["chmod", "777", str(file)])

        # print("Files in target dir: " + str(files))
