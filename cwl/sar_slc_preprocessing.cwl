#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_slc_preprocessing.py
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/cloudinsar/openeo_insar:20260107T1050
  NetworkAccess:
    networkAccess: true
  InitialWorkDirRequirement:
    listing:
      - entryname: "arguments.json"
        entry: $(inputs)
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
    type: string[]
  sub_swath:
    type: string?
outputs:
  output_file:
    type: File[]
    outputBinding:
      glob: ["collection.json", "*2images*"]
