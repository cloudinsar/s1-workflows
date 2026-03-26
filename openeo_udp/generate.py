import json
from pathlib import Path

import openeo
from openeo.api.process import Parameter
from openeo.rest.udp import build_process_dict
from openeo.rest.stac_resource import StacResource
from openeo.internal.graph_building import PGNode


CWL_PATH = "cwl/sar_coherence_parallel_temporal_extent.cwl"
CWL_URL = "https://raw.githubusercontent.com/cloudinsar/s1-workflows/refs/heads/main/" + CWL_PATH


def generate():
    connection = openeo.connect("openeofed.dataspace.copernicus.eu").authenticate_oidc()

    spatial_extent = Parameter.spatial_extent(
        name="spatial_extent",
        description=(
            "Limits the data to process to the specified bounding box or polygons. "
            "Used to find the Sentinel-1 burst to process when `burst_id` is not provided."
        ),
        optional=True,
        default=None,
    )

    temporal_extent = Parameter.temporal_interval(
        name="temporal_extent",
        description="Date range to search for Sentinel-1 acquisitions, e.g. ['2024-08-01', '2024-09-30'].",
    )

    temporal_baseline = Parameter.integer(
        name="temporal_baseline",
        description="Temporal baseline in days between InSAR pairs (e.g. 6 or 12).",
    )

    polarization = Parameter.string(
        name="polarization",
        description="SAR polarization channel to process.",
        default="vv",
        values=["vv", "vh"],
    )

    sub_swath = Parameter.string(
        name="sub_swath",
        description="Sentinel-1 IW sub-swath to process.",
        default="IW2",
        values=["IW1", "IW2", "IW3"],
    )

    burst_id = Parameter.integer(
        name="burst_id",
        description=(
            "Sentinel-1 burst ID to process. "
            "When omitted, the burst is selected automatically from `spatial_extent`."
        ),
        optional=True,
        default=None,
    )

    coherence_window_rg = Parameter.integer(
        name="coherence_window_rg",
        description="Coherence estimation window size in the range direction.",
        default=10,
        optional=True,
    )

    coherence_window_az = Parameter.integer(
        name="coherence_window_az",
        description="Coherence estimation window size in the azimuth direction.",
        default=2,
        optional=True,
    )

    stac_resource = StacResource(
        graph=PGNode(
            "run_cwl_to_stac",
            namespace=None,
            arguments={
                "cwl": CWL_URL,
                "context": {
                    "temporal_extent": {"from_parameter": "temporal_extent"},
                    "temporal_baseline": {"from_parameter": "temporal_baseline"},
                    "spatial_extent": {"from_parameter": "spatial_extent"},
                    "burst_id": {"from_parameter": "burst_id"},
                    "polarization": {"from_parameter": "polarization"},
                    "sub_swath": {"from_parameter": "sub_swath"},
                    "coherence_window_rg": {"from_parameter": "coherence_window_rg"},
                    "coherence_window_az": {"from_parameter": "coherence_window_az"},
                },
            },
        ),
        connection=connection,
    )

    return build_process_dict(
        process_graph=stac_resource,
        process_id="sar_coherence",
        description=(Path(__file__).parent.parent / "README.md").read_text(),
        parameters=[
            spatial_extent,
            temporal_extent,
            temporal_baseline,
            polarization,
            sub_swath,
            burst_id,
            coherence_window_rg,
            coherence_window_az,
        ],
    )


if __name__ == "__main__":
    with open("sar_coherence.json", "w") as f:
        json.dump(generate(), f, indent=2)
