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
    json_files = list((repository_root / "sar/example_inputs").glob("*.json"))
    json_files = list(filter(lambda x: "_error" not in str(x), json_files))
    assert json_files
    json_files_new = list(filter(lambda x: "_new" in str(x), json_files))
    json_files_preprocessing = list(filter(lambda x: str(x).endswith("_preprocessing.json"), json_files))
    json_files_rest = set(json_files) - set(json_files_new) - set(json_files_preprocessing) - set(json_files_new) - set(json_files_preprocessing)
    assert json_files_rest
    for cwl_file in cwl_files:
        print(f"Checking {cwl_file}")
        name = cwl_file.name
        json_files_filtered = None
        if str(name).startswith("sar_coherence_parallel_temporal_extent"):
            json_files_filtered = json_files_new
        elif str(name).startswith("sar_coherence_parallel") or str(name).startswith("sar_interferogram"):
            json_files_filtered = json_files_rest
        elif str(name).startswith("sar_coherence"):
            json_files_filtered = json_files_new
        elif str(name).startswith("sar_slc_preprocessing"):
            json_files_filtered = json_files_preprocessing
        assert json_files_filtered
        for j in json_files_filtered:
            cmd = ["cwltool", "--disable-color", "--debug", "--validate", str(cwl_file), j]
            exec_proc(cmd)
