#!/usr/bin/env python3
from pathlib import Path

import openeo

# This file is for testing the stac catalog that got created by the insar process.

#############################
# Step 1, build process graph
#############################
url = "https://openeo.dataspace.copernicus.eu"
# url = "http://127.0.0.1:8080"
connection = openeo.connect(url).authenticate_oidc()


stac_root_master = Path("S1_2images_collection_master.json").absolute()
stac_root_slaves = Path("S1_2images_collection_slaves.json").absolute()
assert stac_root_master.exists()
assert stac_root_slaves.exists()

datacube_master = openeo.DataCube.load_stac(
    url=str(stac_root_master), bands=["grid_lat", "grid_lon"]
)
datacube_master = datacube_master.reduce_dimension(reducer="max", dimension="t")
datacube_slaves = openeo.DataCube.load_stac(
    url=str(stac_root_slaves), bands=["i_VH", "q_VH"]
)
datacube = datacube_slaves.merge_cubes(datacube_master)
datacube = datacube.resample_spatial(
    resolution=1, projection="EPSG:3857"  # webmercator
)

# datacube = datacube.rename_labels(dimension="t", target=['2018-01-28_2018-02-03'])
datacube = datacube.reduce_dimension(dimension="t", reducer="mean")
# datacube = datacube.filter_bbox(
#     west=-50,
#     east=50,
#     south=-50,
#     north=50,
#     crs="EPSG:3857"
# )

output_dir = Path("tmp_local_output").absolute()
output_dir.mkdir(exist_ok=True)
datacube.print_json(file=output_dir / "process_graph.json", indent=2)

###################################
# Step 2, run process graph locally
###################################
containing_folder = Path(__file__).parent.absolute()

from openeogeotrellis.deploy.run_graph_locally import run_graph_locally

run_graph_locally(output_dir / "process_graph.json", output_dir)
