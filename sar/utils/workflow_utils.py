import json
import math
import os
import re
import shlex
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# __file__ could have exotic values in Docker:
# __file__ == /src/./OpenEO_insar.py
# __file__ == //./src/OpenEO_insar.py
# So we do a lot of normalization:
repo_directory = os.path.dirname(os.path.normpath(__file__).replace("//", "/"))
repo_directory = Path(repo_directory).parent.parent.absolute()
print("repo_directory: " + str(repo_directory))

if "AWS_ACCESS_KEY_ID" not in os.environ and os.path.exists(repo_directory / "notebooks/CDSE_SECRET"):
    # same credentials as in the notebooks
    with open(repo_directory / "notebooks/CDSE_SECRET", "r") as file:
        lines = file.readlines()
    os.environ["AWS_ACCESS_KEY_ID"] = lines[0].split(":")[1].strip()
    os.environ["AWS_SECRET_ACCESS_KEY"] = lines[1].split(":")[1].strip()
if not "AWS_ENDPOINT_URL_S3" in os.environ:
    os.environ["AWS_ENDPOINT_URL_S3"] = "https://eodata.dataspace.copernicus.eu"

print("S3_ENDPOINT_URL= " + str(os.environ.get("S3_ENDPOINT_URL", None)))
print("AWS_ACCESS_KEY_ID= " + str(os.environ.get("AWS_ACCESS_KEY_ID", None)))
if "AWS_ACCESS_KEY_ID" not in os.environ:
    raise Exception("AWS_ACCESS_KEY_ID should be set in environment")

input_dict_2024_vv = {
    "InSAR_pairs": [
        ["2024-08-09", "2024-08-21"],
        ["2024-08-21", "2024-09-02"],
        # ["2024-08-21", "2024-09-14"],
        # ["2024-09-02", "2024-09-14"],
    ],
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

input_dict_2018_vh = {
    "InSAR_pairs": [["2018-01-28", "2018-02-03"]],
    "burst_id": 329488,
    "coherence_window_az": 2,
    "coherence_window_rg": 10,
    "n_az_looks": 1,
    "n_rg_looks": 4,
    "polarization": "vh",
    "sub_swath": "IW2",
}

input_dict_belgium_vv = {
    "InSAR_pairs": [["2024-08-09", "2024-08-21"]],
    "burst_id": 234893,
    "polarization": "vv",
    "sub_swath": "IW1",
}
input_dict_2018_vh_preprocessing = {
    "temporal_extent": ["2018-01-28", "2018-02-03"],
    "primary_date": "2018-01-28",
    "burst_id": 329488,
    "polarization": "vh",
    "sub_swath": "IW2",
}

input_dict_belgium_vv_preprocessing = {
    "burst_id": 234893,
    "primary_date": "2024-08-09",
    "polarization": "vv",
    "sub_swath": "IW1",
    "temporal_extent": ["2024-08-09", "2024-08-21"],
}

input_dict_belgium_vv_vh_preprocessing = {
    "burst_id": 234893,
    "primary_date": "2024-08-09",
    "polarization": ["vv", "vh"],
    "sub_swath": "IW1",
    "temporal_extent": ["2024-08-09", "2024-09-02"],
}

# Parameters that gave empty bands on staging:
input_dict_2024_vv_preprocessing = {
        "burst_id": 249435,
        "primary_date": "2024-08-09",
        "polarization": "vv",
        "sub_swath": "IW2",
        "temporal_extent": [
          "2024-08-08",
          "2024-09-03"
        ]
}

snap_extra_arguments = [
    "-J-Dsnap.dataio.bigtiff.compression.type=LZW",
    "-J-Dsnap.dataio.bigtiff.tiling.width=512",
    "-J-Dsnap.dataio.bigtiff.tiling.height=512",
    "-J-Dsnap.dataio.bigtiff.compression.quality=1.0",
    "-J-Dsnap.gpf.useFileTileCache=true",
    "-J-Dsnap.parallelism=2",
    "-J-Dsnap.dataio.gdal.creationoptions=COMPRESS=DEFLATE;TILED=TRUE",
    "-J-Dsnap.jai.defaultTileSize=128",
    "-J-Dsnap.jai.tileCacheSize=512",
]

origGetAddrInfo = socket.getaddrinfo

def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
    return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)


# Force ipv4 usege to avoid urllib getting stuck on requests
# replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper


def date_from_burst(burst_path):
    return Path(burst_path).parent.name.split("_")[2]


def parse_date(date_str: str) -> datetime:
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return datetime.strptime(date_str, "%Y-%m-%d")
    if re.match(r"^\d{4}\d{2}\d{2}$", date_str):
        return datetime.strptime(date_str, "%Y%m%d")
    try:
        return datetime.strptime(date_str, "%Y%m%dT%H%M%S")
    except ValueError:
        pass
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")


def union_extents(a: list, b: list) -> list:
    """
    Union of two extents [minx, miny, maxx, maxy].
    """
    assert len(a) == 2
    assert len(b) == 2
    # check if not infinite first
    if not math.isinf(a[0]) and not math.isinf(a[1]):
        assert a[0] <= a[1], "Invalid extent: " + str(a)
    if not math.isinf(b[0]) and not math.isinf(b[1]):
        assert b[0] <= b[1], "Invalid extent: " + str(b)
    return [min(a[0], b[0]), max(a[1], b[1])]


def union_aabbox(a: list, b: list) -> list:
    """
    Union of two axis-aligned bounding boxes (AABBs).
    """
    return [
        min(a[0], b[0]),
        min(a[1], b[1]),
        max(a[2], b[2]),
        max(a[3], b[3]),
    ]


def parse_json_from_output(output_str: str) -> Dict[str, Any]:
    lines = output_str.split("\n")
    parsing_json = False
    json_str = ""
    # reverse order to get last possible json line
    for l in reversed(lines):
        if not parsing_json:
            if l.endswith("}"):
                parsing_json = True
        json_str = l + json_str
        if l.startswith("{"):
            break

    return json.loads(json_str)


def default_serializer(obj):
    """
    Function to handle JSON serialization of objects that cannot be natively serialized
    :param obj: object to seralize
    :return: JSON-compatible representation of object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def merge_two_dicts(x, y):
    z = x.copy()  # start with keys and values of x
    z.update(y)  # modifies z with keys and values of y
    return z


def exec_proc(command, cwd=None, write_output=True, env=None):
    if isinstance(command, str):
        command_to_display = command
        command_list = shlex.split(command)
    else:
        command = list(map(lambda x: str(x), command))
        command_to_display = subprocess.list2cmdline(command)
        command_list = command
    if cwd is None:
        cwd = os.getcwd()
    elif not os.path.exists(cwd):
        raise Exception("cwd does not exist: " + str(cwd))

    if env is None:
        env = {}

    keys_values = env.items()
    # convert all values to strings:
    env = {str(key): str(value) for key, value in keys_values}
    new_env = merge_two_dicts(os.environ, env)

    # print commands that can be pasted in the console
    print(f'> cd "{cwd}"')
    for key in env:
        print(key + "=" + str(subprocess.list2cmdline([env[key], ""])[:-3]))
    print("" + command_to_display)

    output = ""
    try:
        process = subprocess.Popen(
            command_list,
            cwd=cwd,
            universal_newlines=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            env=new_env,
        )

        with process:
            if process.stdout is None:
                # Just to satisfy the static type checker:
                raise Exception("Process returned with no stdout")
            for line in process.stdout:
                if write_output:
                    sys.stdout.write(line)
                output += line
            ret = process.wait()

    except subprocess.CalledProcessError as ex:
        ret = ex.returncode
        output = ex.output
    except KeyboardInterrupt:
        # Allows to still write output
        ret = 1

    if ret != 0:
        if not write_output:
            print(output)
        raise Exception("Process returned error status code: " + str(ret))
    return ret, output
