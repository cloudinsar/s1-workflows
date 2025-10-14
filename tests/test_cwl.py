import yaml
from testutils import *


def test_cwl_syntax():
    cwl_files = list((repository_root / "cwl").glob("*.cwl"))
    assert cwl_files
    for cwl_file in cwl_files:
        print(f"Checking {cwl_file}")
        yaml_parsed = list(yaml.safe_load_all(cwl_file.read_text()))
        assert len(yaml_parsed) >= 1
