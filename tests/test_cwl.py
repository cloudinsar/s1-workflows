import yaml
from testutils import *


def test_cwl_syntax():
    cwl_files = list((repository_root / "cwl").glob("*.cwl"))
    assert cwl_files
    for cwl_file in cwl_files:
        print(f"Checking {cwl_file}")
        yaml_parsed = list(yaml.safe_load_all(cwl_file.read_text()))
        assert len(yaml_parsed) >= 1


def test_cwl_validate():
    exec_proc(["node", "--version"])
    cwl_files = list((repository_root / "cwl").glob("*.cwl"))
    assert cwl_files
    for cwl_file in cwl_files:
        print(f"Checking {cwl_file}")
        cmd = ["cwltool", "--disable-color", "--debug", "--validate", str(cwl_file)]
        name = cwl_file.name
        if str(name).startswith("sar_coherence_parallel_temporal_extent"):
            cmd += [repository_root / "sar/example_inputs/input_dict_test_parallel.json"]
        elif str(name).startswith("sar_coherence_parallel") or str(name).startswith("sar_interferogram"):
            cmd += [repository_root / "sar/example_inputs/input_dict_belgium_vv.json"]
        elif str(name).startswith("sar_coherence"):
            # cmd += [repository_root / "sar/example_inputs/input_dict_2024_vv_new.json"]
            pass
        elif str(name).startswith("sar_slc_preprocessing"):
            cmd += [repository_root / "sar/example_inputs/input_dict_2018_vh_preprocessing.json"]
        exec_proc(cmd)
