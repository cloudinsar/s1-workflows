#!/usr/bin/env python3
from pathlib import Path

import openeo

# This file is for testing the stac catalog that got created by the insar process.

#############################
# Step 1, build process graph
#############################

stac_root = Path("S1_2images_collection.json").absolute()
# stac_root = Path("output/S1_2images_collection.json").absolute()
assert stac_root.exists()

datacube = openeo.DataCube.load_stac(url=str(stac_root))
datacube = datacube.resample_spatial(
    resolution=1, projection="EPSG:3857"  # webmercator
)
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
