import json
from pathlib import Path

from sar.utils.simple_stac_builder import generate_catalog


def test_generate_catalog_exports_stac_1_1(tmp_path, monkeypatch):
    tif = tmp_path / "S1_coh_2images_20240101T000000_20240113T000000.tif"
    tif.touch()

    gdalinfo_json = {
        "stac": {
            "eo:bands": [{"name": "b1", "description": "coherence"}],
            "proj:epsg": 32631,
            "proj:projjson": {},
            "proj:wkt2": "",
            "proj:shape": [10, 20],
            "proj:transform": [0, 1, 0, 0, 0, -1],
        },
        "wgs84Extent": {
            "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]
        },
        "cornerCoordinates": {
            "lowerLeft": [0.0, 0.0],
            "lowerRight": [1.0, 0.0],
            "upperRight": [1.0, 1.0],
            "upperLeft": [0.0, 1.0],
        },
    }

    def fake_check_output(cmd, timeout=None, text=None):
        if cmd == ["gdalinfo", "--version"]:
            return "GDAL 3.8.4, released 2024/03/04"
        if cmd[:2] == ["gdalinfo", str(tif)]:
            return json.dumps(gdalinfo_json)
        raise AssertionError(f"Unexpected command: {cmd}")

    class _FakeCollection:
        def validate_all(self):
            return 1

    monkeypatch.setattr("sar.utils.simple_stac_builder.subprocess.check_output", fake_check_output)
    monkeypatch.setattr("pystac.Collection.from_file", lambda *_args, **_kwargs: _FakeCollection())
    monkeypatch.chdir(tmp_path)

    generate_catalog(tmp_path)

    collection = json.loads((tmp_path / "S1_2images_collection.json").read_text())
    assert collection["stac_version"] == "1.1.0"

    item_href = next(link["href"] for link in collection["links"] if link["rel"] == "item")
    item = json.loads((tmp_path / Path(item_href)).read_text())
    assert item["stac_version"] == "1.1.0"
