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

  An example on how to use it:
  
  ```python
  import openeo
  
  connection = openeo.connect("https://openeo.dataspace.copernicus.eu").authenticate_oidc()
  stac_resource = connection.datacube_from_process(
      "sentinel1_sar_slc_preprocessing",
      namespace="https://raw.githubusercontent.com/ESA-APEx/apex_algorithms/2ed1e3dc9884c1d7354687b709563d239393c392/algorithm_catalog/eurac/sentinel1_sar_slc_preprocessing/openeo_udp/sentinel1_sar_slc_preprocessing.json",
      **{
          "burst_id": 329488,
          "polarization": ["VH"],
          "primary_date": "2018-01-28",
          "sub_swath": "IW2",
          "temporal_extent": ["2018-01-28", "2018-02-04"],
      },
  )
  
  job = stac_resource.create_job(title="sentinel1_sar_slc_preprocessing test")
  job.start_and_wait()
  job.get_results().download_files()
  ```
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/cloudinsar/openeo_insar:20260424T0814
  NetworkAccess:
    networkAccess: true
  InitialWorkDirRequirement:
    listing:
      - entryname: "arguments.json"
        entry: $(inputs)
  ResourceRequirement:
    ramMin: 13000
    ramMax: 13000
    coresMin: 2
    coresMax: 7
arguments:
  - arguments.json
inputs:
  temporal_extent:
    type: string[]
    doc: "Temporal extent as [start_date, end_date], e.g., ['2024-08-01', '2024-09-30']."
  burst_id:
    type: int
    doc: |
      A temporal extent could have multiple bursts per day. Use [this notebook](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/LPS_DEMO/Input_selection.ipynb) to find a fitting `burst_id`.
      Alternatively, the burst id map can be downloaded here: [Burst ID Maps 2022-05-30](https://sar-mpc.eu/files/S1_burstid_20220530.zip).
  primary_date:
    type: string
    doc: "Acquisition date of the image to be used as reference of the coregistration operation."
  polarization:
    type:
      type: array
      items:
        type: enum
        symbols: [ "VV", "VH" ]
  sub_swath:
    - type: enum
      symbols: [ "IW1", "IW2", "IW3" ]
      doc: "Sub-swath identifier"
outputs:
  output_results:
    type: Directory
    outputBinding:
      glob: .
