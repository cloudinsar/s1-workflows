#!/usr/bin/env cwl-runner
# LOCAL USAGE:
#   cwltool --no-read-only --parallel --tmpdir-prefix=$HOME/tmp/ \
#           --preserve-environment=AWS_ACCESS_KEY_ID \
#           --preserve-environment=AWS_SECRET_ACCESS_KEY \
#           --preserve-environment=AWS_ENDPOINT_URL_S3 \
#           cwl/sar_slc_preprocessing.cwl sar/example_inputs/input_dict_belgium_vv_preprocessing.json
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_slc_preprocessing.py
doc: |
  This process generates a STAC collection of co‑registered Sentinel‑1 Single Look Complex (SLC) bursts in SAR geometry. A specific Sentinel‑1 burst is selected by explicitly defining the burst_id and sub_swath parameters, enabling fine‑grained, burst‑level access to Sentinel‑1 TOPS data.
  The co‑registration is performed using the [ESA SNAP Back‑Geocoding operator](https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-toolboxes/eu.esa.microwavetbx.sar.op.sentinel1.ui/operators/BackGeocodingOp.html), which aligns all SLC acquisitions to a common primary geometry, ensuring pixel‑level consistency across the temporal stack. The entire workflow is implemented as a Common Workflow Language (CWL) pipeline.
  The resulting co‑registered SLC stack provides the fundamental input for a wide range of advanced SAR analyses, including InSAR interferogram generation, coherence estimation, and polarimetric processing.
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/cloudinsar/openeo_insar:20260421T0923
  NetworkAccess:
    networkAccess: true
  InitialWorkDirRequirement:
    listing:
      - entryname: "arguments.json"
        entry: $(inputs)
  ResourceRequirement:
    ramMin: 11000
    ramMax: 11000
    coresMin: 2
    coresMax: 7
arguments:
  - arguments.json
inputs:
  temporal_extent:
    type: string[]
  burst_id:
    type: int
  primary_date:
    type: string
  polarization:
    type:
      type: array
      items:
        type: enum
        symbols: [ "VV", "VH" ]
  sub_swath:
    - type: enum
      symbols: [ "IW1", "IW2", "IW3" ]
outputs:
  output_results:
    type: Directory
    outputBinding:
      glob: .
