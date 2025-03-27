#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any


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


def generate_catalog(stac_root):
    # DRAFT CODE!
    collection_stac = {
        "type": "Collection",
        "stac_version": "1.0.0",
        "id": "unknown-job",
        "description": "",
        "license": "unknown",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [["9999-12-30T23:59:59Z", "0001-01-01T00:00:00Z"]]},
        },
        "links": [],
    }

    tiff_files = list(stac_root.rglob("*.tif"))
    for file in tiff_files:
        print(file)
        res = re.search(r"S1_coh_(?P<date1>\d{8})_(?P<date2>\d{8}).tif$", file.name)
        if res is None:
            print("Skipping: ", file)
            continue
        date1 = res.group("date1")
        date2 = res.group("date2")
        date1 = f"{date1[:4]}-{date1[4:6]}-{date1[6:8]}T00:00:00Z"
        date2 = f"{date2[:4]}-{date2[4:6]}-{date2[6:8]}T23:59:59Z"
        if date1 < collection_stac["extent"]["temporal"]["interval"][0][0]:
            collection_stac["extent"]["temporal"]["interval"][0][0] = date1
        if date1 > collection_stac["extent"]["temporal"]["interval"][0][1]:
            collection_stac["extent"]["temporal"]["interval"][0][1] = date1
        if date2 < collection_stac["extent"]["temporal"]["interval"][0][0]:
            collection_stac["extent"]["temporal"]["interval"][0][0] = date2
        if date2 > collection_stac["extent"]["temporal"]["interval"][0][1]:
            collection_stac["extent"]["temporal"]["interval"][0][1] = date2

        # get general metadata with gdalinfo:
        output = subprocess.check_output(
            ["gdalinfo", "-json", str(file)], text=True, stderr=subprocess.DEVNULL
        )
        cmd = ["gdalinfo", str(file), "-json", "--config", "GDAL_IGNORE_ERRORS", "ALL"]
        out = subprocess.check_output(cmd, timeout=1800, text=True)
        data_gdalinfo_from_subprocess = parse_json_from_output(out)
        del data_gdalinfo_from_subprocess["stac"][
            "proj:projjson"
        ]  # remove verbose information
        del data_gdalinfo_from_subprocess["stac"]["proj:wkt2"]  # remove verbose information
        # assemble with application specific data:
        stac = {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": file.name,
            "geometry": {
                "type": "Polygon",
                "coordinates": data_gdalinfo_from_subprocess["wgs84Extent"]["coordinates"],
            },
            "bbox": [-180, -90, 180, 90],
            "properties": {
                "datetime": "2024-08-26T17:15:50Z",
                # TODO: Get those values out of burst extraction:
                # "sar:instrument_mode": "IW",
                # "sar:frequency_band": "C",
                # "sar:polarizations": ["VV"],
                # "sat:orbit_state": "ASCENDING",
                # "sat:absolute_orbit": 55387,
                # "sat:relative_orbit": 15,
                # "insar:product_height": 1518,
                # "insar:prf": 1685.817302492702,
                # "insar:product_width": 25574,
                # "insar:product_name": "S1A_SLC_20240826T171550_030345_IW3_VV_442708",
                # "insar:product_type": "SLC",
                # "insar:doppler_difference_hz": 0.7882403,
                # "insar:temporal_baseline_days": 12.000008,
                # "insar:coherence": 0.8293007,
                # "insar:perpendicular_baseline_m": 193.23735,
                # "insar:height_of_ambiguity_m": -92.51294,
            },
            "links": [],
            "assets": {file.name: data_gdalinfo_from_subprocess["stac"]},
        }

        stac_item_filename = str(file) + ".json"
        with open(stac_item_filename, "w") as f:
            json.dump(stac, f, indent=2)

        collection_stac["links"].append(
            {
                "href": "./" + str(Path(stac_item_filename).relative_to(stac_root)),
                "rel": "item",
                "type": "application/geo+json",
            }
        )

    with open(stac_root / "collection.json", "w") as f:
        json.dump(collection_stac, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_catalog(Path(sys.argv[1]))
    else:
        generate_catalog(Path("./notebooks/output/S1_coh"))
        print("Using default stac_root!")
    print("done")
