#!/usr/bin/env python3
import base64
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

from sar.utils import simple_stac_builder
from sar.utils import tiff_to_gtiff
from sar.utils.workflow_utils import *

setup_insar_environment()

_log = logging.getLogger(__name__)

start_time = datetime.now()

if len(sys.argv) > 1:
    arg = sys.argv[1]
    if os.path.isfile(arg):
        input_dict = json.loads(Path(arg).read_text())
    else:
        input_dict = json.loads(base64.b64decode(arg.encode("utf8")).decode("utf8"))
else:
    _log.info("Using debug arguments!")
    input_dict = input_dict_2018_vh

if not input_dict.get("polarization"):
    input_dict["polarization"] = "vv"
if not input_dict.get("sub_swath"):
    input_dict["sub_swath"] = "IW3"
if not "coherence_window_rg" in input_dict or not "coherence_window_az" in input_dict:
    _log.info("Setting default coherence window size")
    input_dict["coherence_window_rg"] = 10
    input_dict["coherence_window_az"] = 2
if not "n_rg_looks" in input_dict or not "n_az_looks" in input_dict:
    _log.info("Setting default multi-look window size")
    input_dict["n_rg_looks"] = 4
    input_dict["n_az_looks"] = 1
_log.info(f"{input_dict=}")

# When using the CWL scatter for parallel execution, we will get only an element containing two dates
# To make sure everything works, we wrap it into a list
if not isinstance(input_dict["InSAR_pairs"][0],list):
    input_dict["InSAR_pairs"] = [input_dict["InSAR_pairs"]]

start_date = min([min(pair) for pair in input_dict["InSAR_pairs"]])
end_date = max([max(pair) for pair in input_dict["InSAR_pairs"]])

# We can allow to have multiple results with the same primary date, since we export the SNAP results directly in STAC,
# we are not supposed to load them again in openEO with load_stac, which would complain about more than one
# element having the same datetime (if we use the primary date as datetime).
# primary_dates = [pair[0] for pair in input_dict["InSAR_pairs"]]
# primary_dates_duplicates = set([d for d in primary_dates if primary_dates.count(d) > 1])
# if primary_dates_duplicates:
#     raise ValueError(
#         f"Duplicate primary date(s) found in InSAR_pairs: {primary_dates_duplicates}. "
#         "You can load multiple primary dates over multiple processes if needed."
#     )

result_folder = Path.cwd().absolute()
# result_folder = repo_directory / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = Path("/tmp/insar")
tmp_insar.mkdir(parents=True, exist_ok=True)

bursts = retrieve_bursts_with_id_and_iw(
    start_date,
    end_date,
    input_dict.get("polarization"),
    sbswath=input_dict.get("sub_swath"),
    burst_id=input_dict.get("burst_id"),
    spatial_extent=input_dict.get("spatial_extent"),
)

flattened_pairs = set()
for pair in input_dict["InSAR_pairs"]:
    for date in pair:
        flattened_pairs.add(parse_date(date).date())
burst_paths = []
for burst in bursts:
    begin = parse_date(burst["BeginningDateTime"]).date()
    end = parse_date(burst["EndingDateTime"]).date()
    if begin not in flattened_pairs and end not in flattened_pairs:
        _log.info(f"Skipping burst {burst['BurstId']} ({begin} - {end})")
        continue
    cmd = [
        "bash",
        "sentinel1_burst_extractor.sh",
        "-n", burst["ParentProductName"],
        "-p", input_dict["polarization"].lower(),
        "-s", str(input_dict["sub_swath"].lower()),
        "-r", str(burst["BurstId"]),
        "-o", str(tmp_insar),
    ]
    _, output = exec_proc(cmd, cwd=repo_directory / "utilities", write_output=False)
    # get paths from stdout:
    needle = "out_path: "
    bursts_from_output = sorted(
        [
            Path(line[len(needle) :]).absolute()
            for line in output.split("\n")
            if line.startswith(needle)
        ]
    )
    burst_paths.extend(bursts_from_output)
    _log.info("seconds since start: " + str((datetime.now() - start_time).seconds))

    if len(bursts_from_output) == 0:
        raise Exception("No files found in command output: " + str(output))

_log.info(f"{burst_paths=!r}")

asset_paths: List[Path] = []

for pair in input_dict["InSAR_pairs"]:
    prm_filename = next(filter(lambda x: pair[0].replace("-", "") in str(x), burst_paths))
    sec_filename = next(filter(lambda x: pair[1].replace("-", "") in str(x), burst_paths))

    output_filename_tmp = f"{tmp_insar}/tmp_phase_coh_{date_from_burst(prm_filename)}_{date_from_burst(sec_filename)}"
    prm_date = parse_date(pair[0])
    sec_date = parse_date(pair[1])
    result_path = os.path.join(
        result_folder,
        f"tmp_geocoded_interferogram_{prm_date.strftime('%d%b%Y')}_{sec_date.strftime('%d%b%Y')}.tif",
    )

    if not os.path.exists(result_path):
        phase_bandname = f'Phase_ifg_{input_dict["sub_swath"]}_{input_dict["polarization"].upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        coh_bandname = f'coh_{input_dict["sub_swath"]}_{input_dict["polarization"].upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'

        gpt_cmd = [
            "gpt",
            str(
                repo_directory
                / "notebooks/graphs/interferogram_sarGeometry.xml"
            ),
            f"-Pprm_filename={prm_filename}",
            f"-Psec_filename={sec_filename}",
            f"-PcohWinRg={input_dict['coherence_window_rg']}",
            f"-PcohWinAz={input_dict['coherence_window_az']}",
            f"-PnRgLooks={input_dict['n_rg_looks']}",
            f"-PnAzLooks={input_dict['n_az_looks']}",
            f"-Poutput_filename={output_filename_tmp}",
        ] + snap_extra_arguments
        exec_proc(gpt_cmd, write_output=False)

        # Prepare the snaphu export for unwrapping
        gpt_cmd = [
            "gpt",
            str(
                repo_directory
                / "notebooks/graphs/snaphu_export.xml"
            ),
            f"-Pphase_filename={output_filename_tmp}.dim",
            f"-Poutput_folder_snaphu={tmp_insar}",
        ] + snap_extra_arguments
        exec_proc(gpt_cmd, write_output=False)

        # Unwrapping with snaphu
        snaphu_conf_filename = glob.glob(f"{output_filename_tmp}/snaphu.conf")[0]
        with open(snaphu_conf_filename, "r") as snaphu_conf_file:
            for line in snaphu_conf_file:
                if line.startswith("#"):
                    line = line[1:].lstrip()  # Remove the '#' symbol and whitespaces at the beginning
                    if line.startswith("snaphu"):
                        cmd_unwrapping = line.rstrip()
                        break

        exec_proc(cmd_unwrapping, cwd=output_filename_tmp, write_output=False)

        # Geocode the result (interferogram, unwrapped interferogram, coherence)
        sub_swath = input_dict["sub_swath"].upper()
        phase_bandname = f'Phase_ifg_{sub_swath}_{input_dict["polarization"].upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        unw_phase_bandname = f'Unw_Phase_ifg_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        coh_bandname = f'coh_{sub_swath}_{input_dict["polarization"].upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        unw_phase_filename = glob.glob(
            os.path.join(output_filename_tmp, "UnwPhase*.hdr")
        )[0]
        saveDEM = False  # Just like in geocode_snaphuInterferogram.xml
        gpt_cmd = [
                "gpt",
                "-J-Xmx14G",
                str(
                    repo_directory
                    / "notebooks/graphs/geocode_snaphuInterferogram_WGS84.xml"
                ),
                f'-Pinterferogram_filename={output_filename_tmp}.dim',
                f'-PsaveDEM="{str(saveDEM).lower()}"',
                f'-Punw_interferogram_filename={unw_phase_filename}',
                f'-Pphase_coh_bandnames={phase_bandname},{unw_phase_bandname},{coh_bandname}',
                f'-Poutput_filename={result_path}'
            ] + snap_extra_arguments
        exec_proc(gpt_cmd, write_output=False)

    output_filename = Path(f"{result_folder}/phase_coh_{date_from_burst(prm_filename)}_{date_from_burst(sec_filename)}.tif")

    asset_paths.append(output_filename)
    if not os.path.exists(output_filename):
        tiff_to_gtiff.tiff_to_gtiff(result_path)
        Path(result_path).rename(output_filename) # Don't re-writie SNAP outputs, but rename them to match the expected naming convention

_log.info("seconds since start: " + str((datetime.now() - start_time).seconds))

# slow when running outside Docker, because the whole home directory is scanned.
simple_stac_builder.generate_catalog(
    result_folder,
    files=asset_paths,
    date_regex=re.compile(
        r".*phase_coh_(?P<date1>\d{8}T\d{6})_(?P<date2>\d{8}T\d{6}).tif$"
    ),
    collection_filename="collection.json",
)

_log.info("seconds since start: " + str((datetime.now() - start_time).seconds))

# # CWL Will find the result files in HOME or CD

files = list(result_folder.glob("*phase_coh_*"))
for file in files:
    # Docker often runs as root, this makes it easier to work with the files as a standard user:
    subprocess.call(["chmod", "777", str(file)])  # TODO: use 664

_log.info("Files in target dir: " + str(files))
