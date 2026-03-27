#!/usr/bin/env cwl-runner
# Example on how to run locally: cwltool --tmpdir-prefix=$HOME/tmp/ --force-docker-pull --leave-container --leave-tmpdir --no-read-only --parallel --preserve-environment=AWS_ENDPOINT_URL_S3 --preserve-environment=AWS_ACCESS_KEY_ID --preserve-environment=AWS_SECRET_ACCESS_KEY cwl/sar_interferogram.cwl sar/example_inputs/input_dict_2018_vh.json
cwlVersion: v1.2
class: CommandLineTool

doc: |
  An example on how to use it:
  
  ```python
  import openeo

  connection = openeo.connect("openeo.dataspace.copernicus.eu/").authenticate_oidc()
  stac_resource = connection.datacube_from_process(
    "sar_interferogram",
    namespace="https://raw.githubusercontent.com/ESA-APEx/apex_algorithms/refs/heads/insar/algorithm_catalog/eurac/sar_interferogram/openeo_udp/sar_interferogram.json",
    **{
        "InSAR_pairs": [
            [
                "2018-01-28",
                "2018-02-03"
            ]
        ],
        "burst_id": 329488,
        "coherence_window_az": 2,
        "coherence_window_rg": 10,
        "n_az_looks": 1,
        "n_rg_looks": 4,
        "polarization": "VH",
        "sub_swath": "IW2"
    }
  )
  
  job = stac_resource.create_job(title="sar_interferogram test")
  job.start_and_wait()
  job.get_results().download_files()
  ```
baseCommand: /src/sar/sar_interferogram.py
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/cloudinsar/openeo_insar:20260317T1236
  NetworkAccess:
    networkAccess: true
  InitialWorkDirRequirement:
    listing:
      - entryname: "arguments.json"
        entry: $(inputs)
  ResourceRequirement:
    ramMin: 7000
    ramMax: 7000
    coresMin: 2
    coresMax: 7
arguments:
  - arguments.json
inputs:
  InSAR_pairs:
    type:
      type: array
      items:
        type: array
        items: string
  burst_id:
    type: int
  coherence_window_rg:
    type: int?
    default: 10
    doc: "Coherence window size in range direction"
  coherence_window_az:
    type: int?
    default: 2
    doc: "Coherence window size in azimuth direction"
  n_az_looks:
    type: int?
  n_rg_looks:
    type: int?
  polarization:
    - type: enum
      symbols: [ "VV", "VH" ]
  sub_swath:
    type:
      type: enum
      symbols: [ "IW1", "IW2", "IW3" ]
    default: "IW2"
    doc: "Sub-swath identifier"
outputs:
  output_file:
    type: File[]
    outputBinding:
      glob: ["collection.json", "*phase_coh_*"]
