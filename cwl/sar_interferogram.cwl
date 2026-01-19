#!/usr/bin/env cwl-runner
# Example on how to run locally: cwltool --tmpdir-prefix=$HOME/tmp/ --force-docker-pull --leave-container --leave-tmpdir --parallel --preserve-environment=AWS_ENDPOINT_URL_S3 --preserve-environment=AWS_ACCESS_KEY_ID --preserve-environment=AWS_SECRET_ACCESS_KEY cwl/sar_interferogram.cwl sar/example_inputs/input_dict_2018_vh.json
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_interferogram.py
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/cloudinsar/openeo_insar:20260107T1050
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
  coherence_window_az:
    type: int?
  coherence_window_rg:
    type: int?
  n_az_looks:
    type: int?
  n_rg_looks:
    type: int?
  polarization:
    type: string
  sub_swath:
    type: string?
outputs:
  output_file:
    type: File[]
    outputBinding:
      glob: ["collection.json", "*phase_coh_*"]
