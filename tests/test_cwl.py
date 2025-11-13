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
    cwl_files = list((repository_root / "cwl").glob("*.cwl"))
    assert cwl_files
    for cwl_file in cwl_files:
        print(f"Checking {cwl_file}")
        if "sar_coherence.cwl" in str(cwl_file):
            print("Skipping to avoid known error on CI.")
            # cwl_utils.errors.JavascriptException: NodeJSEngine requires Node.js engine to evaluate and validate Javascript expressions, but couldn't find it.  Tried nodejs, node, docker run node:alpine"
            continue
        exec_proc(["cwltool", "--disable-color", "--debug", "--validate", str(cwl_file)])
