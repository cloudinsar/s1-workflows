#!/usr/bin/env python3
import base64
from datetime import timedelta

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
    input_dict = json.loads((repo_directory / "sar/example_inputs/input_dict_2024_vv_new.json").read_text())

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

bursts = retrieve_bursts_with_id_and_iw(
    start_date,
    end_date,
    input_dict['polarization'],
    input_dict['burst_id'],
    input_dict['sub_swath']
)

burst_paths = []
for burst in bursts:
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
    date = datetime.strptime(os.path.basename(os.path.dirname(f)).split("_")[2][:8], "%Y%m%d")
    date_to_path[date] = f

asset_paths = []

for prm_date, prm_filename in date_to_path.items():
    sec_date = prm_date + timedelta(days=input_dict["temporal_baseline"])
    sec_filename = date_to_path.get(sec_date)
    if sec_date in date_to_path:
        output_filename_tmp = (
            f"{result_folder}/tmp_S1_coh_2images_{date_from_burst(prm_filename)}_{date_from_burst(sec_filename)}.tif"
        )

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
            f"{result_folder}/S1_coh_2images_{date_from_burst(prm_filename)}_{date_from_burst(sec_filename)}.tif"
        )
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
