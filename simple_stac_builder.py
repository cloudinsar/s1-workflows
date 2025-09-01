#!/usr/bin/env python3
import logging
import os
from typing import Union

from workflow_utils import *


def generate_catalog(
    stac_root,
    files: Union[str, list] = "*2images*.tif",
    collection_filename="S1_2images_collection.json",
    date_regex: Union[str, re.Pattern] = re.compile(
        r"S1_coh_2images_(?P<date1>\d{8}T\d{6})_(?P<date2>\d{8}T\d{6}).tif$"
    ),
):
    local_args = locals().copy()
    function_call_str = "generate_catalog("
    for arg in local_args:
        function_call_str += f"{arg}={repr(local_args[arg])}, "
    function_call_str += ")"
    print(function_call_str)

    collection_stac: dict = {
        "type": "Collection",
        "stac_version": "1.0.0",
        "id": "unknown-job",
        "description": "Stac catalog made with " + os.path.basename(__file__),
        "license": "unknown",
        "stac_extensions": [
            "https://stac-extensions.github.io/datacube/v2.2.0/schema.json"
        ],
        "cube:dimensions": {
            "x": {"axis": "x", "type": "spatial"},
            "y": {"axis": "y", "type": "spatial"},
            "t": {"type": "temporal"},
            "bands": {"type": "bands"},
        },
        "extent": {
            "spatial": {"bbox": [[9999, 9999, -9999, -9999]]},
            "temporal": {
                "interval": [["9999-12-30T23:59:59Z", "0001-01-01T00:00:00Z"]]
            },
        },
        "links": [],
    }

    if isinstance(files, str):
        tiff_files = list(stac_root.glob(files))
    elif isinstance(files, list):
        tiff_files = files
    else:
        raise ValueError("Invalid files parameter: " + str(files))

    tiff_files = [Path(file) for file in tiff_files]
    for file in tiff_files:
        print(file)
        if not file.is_absolute():
            file = stac_root / file
        res = re.search(date_regex, file.name)
        if res is None:
            print("Skipping: ", file)
            continue
        date1 = parse_date(res.group("date1"))
        date1 = date1.isoformat() + "Z"
        if date1 < collection_stac["extent"]["temporal"]["interval"][0][0]:
            collection_stac["extent"]["temporal"]["interval"][0][0] = date1
        if date1 > collection_stac["extent"]["temporal"]["interval"][0][1]:
            collection_stac["extent"]["temporal"]["interval"][0][1] = date1
        if "date2" in res.groupdict():
            date2 = parse_date(res.group("date2"))
            date2 = date2.isoformat() + "Z"
            if date2 < collection_stac["extent"]["temporal"]["interval"][0][0]:
                collection_stac["extent"]["temporal"]["interval"][0][0] = date2
            if date2 > collection_stac["extent"]["temporal"]["interval"][0][1]:
                collection_stac["extent"]["temporal"]["interval"][0][1] = date2
        else:
            date2 = None

        # get general metadata with gdalinfo:
        cmd = ["gdalinfo", str(file), "-json", "--config", "GDAL_IGNORE_ERRORS", "ALL"]
        out = subprocess.check_output(cmd, timeout=1800, text=True)
        data_gdalinfo_from_subprocess = parse_json_from_output(out)
        gdalinfo_stac = data_gdalinfo_from_subprocess["stac"]

        def mapper(x):
            """
            replaces default band names like b1, b2, ... with their description instead
            """
            r = re.compile(r"b\d+")
            if r.match(x["name"]) and "description" in x:
                return {"name": x["description"]}
            return x

        gdalinfo_stac["eo:bands"] = list(map(mapper, gdalinfo_stac["eo:bands"]))
        band_names = [band["name"] for band in gdalinfo_stac["eo:bands"]]
        if "values" in collection_stac["cube:dimensions"]["bands"]:
            assert collection_stac["cube:dimensions"]["bands"]["values"] == band_names, (
                "Inconsistent band names: "
                + str(collection_stac["cube:dimensions"]["bands"]["values"])
                + " vs "
                + str(band_names)
            )
        else:
            collection_stac["cube:dimensions"]["bands"]["values"] = band_names

        del gdalinfo_stac["proj:projjson"]  # remove verbose information
        del gdalinfo_stac["proj:wkt2"]  # remove verbose information
        del gdalinfo_stac["proj:epsg"]  # might mess up x/y resolution, so remove
        if "proj:transform" in gdalinfo_stac:
            # might mess up x/y resolution, so remove
            del gdalinfo_stac["proj:transform"]
        del gdalinfo_stac["proj:shape"]  # might mess up x/y resolution, so remove
        gdalinfo_stac["href"] = "./" + str(Path(file).relative_to(stac_root))
        coordinates = data_gdalinfo_from_subprocess["wgs84Extent"]["coordinates"]
        # assemble with application-specific data:
        stac = {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": file.name,
            "geometry": {
                "type": "Polygon",
                "coordinates": coordinates,
            },
            "bbox": [
                min([c[0] for polygon in coordinates for c in polygon]),
                min([c[1] for polygon in coordinates for c in polygon]),
                max([c[0] for polygon in coordinates for c in polygon]),
                max([c[1] for polygon in coordinates for c in polygon]),
            ],
            "properties": {
                "datetime": date1,  # master date
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
            "assets": {file.name: gdalinfo_stac},
        }
        if date2 is not None:
            stac["properties"]["sar:datetime_slave"] = date2

        collection_stac["extent"]["spatial"]["bbox"][0] = union_aabbox(
            collection_stac["extent"]["spatial"]["bbox"][0], stac["bbox"]
        )

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

    collection_stac["cube:dimensions"]["x"]["extent"] = [
        collection_stac["extent"]["spatial"]["bbox"][0][0],
        collection_stac["extent"]["spatial"]["bbox"][0][2],
    ]
    collection_stac["cube:dimensions"]["y"]["extent"] = [
        collection_stac["extent"]["spatial"]["bbox"][0][1],
        collection_stac["extent"]["spatial"]["bbox"][0][3],
    ]
    collection_stac["cube:dimensions"]["t"]["extent"] = collection_stac["extent"][
        "temporal"
    ]["interval"][0]

    with open(stac_root / collection_filename, "w") as f:
        json.dump(collection_stac, f, indent=2)

    try:
        print("Trying pystac validation...")
        from pystac import Collection, Item

        logging.basicConfig(level=logging.DEBUG)

        collection = Collection.from_file(stac_root / collection_filename)
        collection.validate_all()
        print("pystac validation successful")
    except Exception as e:
        print("pystac validation failed: " + str(e))
        print("Reproduce error with:")
        print(function_call_str)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_catalog(Path(sys.argv[1]))
    else:
        print("Using debug arguments!")
        # generate_catalog(Path("./output"))
        generate_catalog(
            stac_root=Path("."),
            files=[
                "S1_coh_2images_20240809T170739_20240821T170739.tif",
                "S1_coh_2images_20240809T170739_20240902T170739.tif",
            ],
            collection_filename="S1_2images_collection.json",
            date_regex=re.compile(
                "S1_coh_2images_(?P<date1>\\d{8}T\\d{6})_(?P<date2>\\d{8}T\\d{6}).tif$"
            ),
        )

        # generate_catalog(
        #     Path("."),
        #     files=["S1_2images_20240809T170739.tif"],
        #     collection_filename="S1_2images_collection_master.json",
        #     date_regex=re.compile(r".*_(?P<date1>\d{8}(T\d{6})?)\.tif$"),
        # )
        # generate_catalog(Path("."), date_regex=re.compile(r".*_(?P<date1>\d{8}T\d{6}).nc$"))
    print("done")
