import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


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
