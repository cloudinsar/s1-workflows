#!/usr/bin/env python3
import argparse
import base64
import glob
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

from utils import simple_stac_builder
from utils import tiff_to_gtiff
from utils.workflow_utils import *

start_time = datetime.now()

parser = argparse.ArgumentParser()
parser.add_argument("--date_pairs", nargs="+", required=True)
parser.add_argument("--burst_id", type=int, required=True)
parser.add_argument("--coherence_window_az", type=int, default=2)
parser.add_argument("--coherence_window_rg", type=int, default=10)
parser.add_argument("--polarization", type=str, choices=["vv", "vh"], required=True)
parser.add_argument("--sub_swath", type=str, choices=["IW1", "IW2", "IW3"], required=True)
parser.add_argument("--n_az_looks", type=int, default=1)
parser.add_argument("--n_rg_looks", type=int, default=4)
args = parser.parse_args()
date_pairs_iso = [parse_date_tuple(t) for t in args.date_pairs]

start_date = min([min(pair) for pair in date_pairs_iso])
end_date = max([max(pair) for pair in date_pairs_iso])

primary_dates = [pair[0] for pair in date_pairs_iso]
primary_dates_duplicates = set([d for d in primary_dates if primary_dates.count(d) > 1])
if primary_dates_duplicates:
    raise ValueError(
        f"Duplicate primary date(s) found in InSAR_pairs: {primary_dates_duplicates}. "
        "You can load multiple primary dates over multiple processes if needed."
    )

result_folder = Path.cwd().absolute()
# result_folder = repo_directory / "output"
# result_folder.mkdir(exist_ok=True)
tmp_insar = Path("/tmp/insar")
tmp_insar.mkdir(parents=True, exist_ok=True)

https_request = (
        f"https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts?$filter="
        + urllib.parse.quote(
    f"ContentDate/Start ge {start_date}T00:00:00.000Z and ContentDate/Start le {end_date}T23:59:59.000Z and "
    f"PolarisationChannels eq '{args.polarization.upper()}' and "
    f"BurstId eq {args.burst_id} and "
    f"SwathIdentifier eq '{args.sub_swath.upper()}'"
)
        + "&$top=1000"
)
print(https_request)
with urllib.request.urlopen(https_request) as response:
    bursts = json.loads(response.read().decode())

flattened_pairs = set()
for pair in date_pairs_iso:
    for date in pair:
        flattened_pairs.add(parse_date(date).date())
burst_paths = []
for burst in bursts["value"]:
    begin = parse_date(burst["BeginningDateTime"]).date()
    end = parse_date(burst["EndingDateTime"]).date()
    if begin not in flattened_pairs and end not in flattened_pairs:
        print(f"Skipping burst {burst['BurstId']} ({begin} - {end})")
        continue
    cmd = [
        "sentinel1_burst_extractor.sh",
        "-n", burst["ParentProductName"],
        "-p", args.polarization.lower(),
        "-s", str(args.sub_swath.lower()),
        "-r", str(args.burst_id),
        "-o", str(tmp_insar),
    ]
    _, output = exec_proc(
        cmd,
        cwd=repo_directory / "utilities",
        env={
            # Allow for relative imports:
            "PATH": os.environ["PATH"] + ":" + str(repo_directory / "utilities")
        },
    )
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
    print("seconds since start: " + str((datetime.now() - start_time).seconds))

    if len(bursts_from_output) == 0:
        raise Exception("No files found in command output: " + str(output))

print(f"{burst_paths=!r}")

# GPT means "Graph Processing Toolkit" in this context
if subprocess.run(["which", "gpt"]).returncode != 0 and os.path.exists("/usr/local/esa-snap/bin/gpt"):
    print("adding SNAP to PATH")  # needed when running outside of docker
    os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/esa-snap/bin"


asset_paths = []

for pair in date_pairs_iso:
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
        phase_bandname = f'Phase_ifg_{args.sub_swath}_{args.polarization.upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        coh_bandname = f'coh_{args.sub_swath}_{args.polarization.upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'

        gpt_cmd = [
            "gpt",
            "-J-Xmx14G",
            str(
                repo_directory
                / "notebooks/graphs/interferogram_sarGeometry.xml"
            ),
            f"-Pprm_filename={prm_filename}",
            f"-Psec_filename={sec_filename}",
            f"-PcohWinRg={args.coherence_window_rg}",
            f"-PcohWinAz={args.coherence_window_az}",
            f"-PnRgLooks={args.n_rg_looks}",
            f"-PnAzLooks={args.n_az_looks}",
            f"-Poutput_filename={output_filename_tmp}",
        ] + snap_extra_arguments
        exec_proc(gpt_cmd)

        # Prepare the snaphu export for unwrapping
        gpt_cmd = [
            "gpt",
            "-J-Xmx14G",
            str(
                repo_directory
                / "notebooks/graphs/snaphu_export.xml"
            ),
            f"-Pphase_filename={output_filename_tmp}.dim",
            f"-Poutput_folder_snaphu={tmp_insar}",
        ] + snap_extra_arguments
        exec_proc(gpt_cmd)

        # Unwrapping with snaphu
        snaphu_conf_filename = glob.glob(f"{output_filename_tmp}/snaphu.conf")[0]
        with open(snaphu_conf_filename, "r") as file:
            for line in file:
                if line.startswith("#"):
                    line = line[1:].lstrip()  # Remove the '#' symbol and whitespaces at the beginning
                    if line.startswith("snaphu"):
                        cmd_unwrapping = line.rstrip()
                        break

        exec_proc(cmd_unwrapping, cwd=output_filename_tmp)

        # Geocode the result (interferogram, unwrapped interferogram, coherence)
        sub_swath = args.sub_swath.upper()
        phase_bandname = f'Phase_ifg_{sub_swath}_{args.polarization.upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        unw_phase_bandname = f'Unw_Phase_ifg_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        coh_bandname = f'coh_{sub_swath}_{args.polarization.upper()}_{prm_date.strftime("%d%b%Y")}_{sec_date.strftime("%d%b%Y")}'
        unw_phase_filename = glob.glob(
            os.path.join(output_filename_tmp, "UnwPhase*.hdr")
        )[0]
        gpt_cmd = [
                "gpt",
                "-J-Xmx14G",
                str(
                    repo_directory
                    / "notebooks/graphs/geocode_snaphuInterferogram.xml"
                ),
                f'-Pinterferogram_filename={output_filename_tmp}.dim',
                f'-Punw_interferogram_filename={unw_phase_filename}',
                f'-Pphase_coh_bandnames={phase_bandname},{unw_phase_bandname},{coh_bandname}',
                f'-Poutput_filename={result_path}'
            ] + snap_extra_arguments
        exec_proc(gpt_cmd)

    output_filename = f"{result_folder}/phase_coh_{date_from_burst(prm_filename)}_{date_from_burst(sec_filename)}.tif"

    asset_paths.append(output_filename)
    if not os.path.exists(output_filename):
        tiff_to_gtiff.tiff_to_gtiff(result_path, output_filename)

print("seconds since start: " + str((datetime.now() - start_time).seconds))

# slow when running outside Docker, because the whole home directory is scanned.
simple_stac_builder.generate_catalog(
    result_folder,
    files=asset_paths,
    date_regex=re.compile(
        r".*phase_coh_(?P<date1>\d{8}T\d{6})_(?P<date2>\d{8}T\d{6}).tif$"
    ),
    collection_filename="phase_coh_collection.json",
)

print("seconds since start: " + str((datetime.now() - start_time).seconds))

# # CWL Will find the result files in HOME or CD

files = list(result_folder.glob("*phase_coh_*"))
for file in files:
    # Docker often runs as root, this makes it easier to work with the files as a standard user:
    subprocess.call(["chmod", "777", str(file)])  # TODO: use 664

print("Files in target dir: " + str(files))
