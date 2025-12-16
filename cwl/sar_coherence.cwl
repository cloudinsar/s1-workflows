#!/usr/bin/env cwl-runner
# Example on how to run locally: cwltool --tmpdir-prefix=$HOME/tmp/ --force-docker-pull --leave-container --leave-tmpdir --parallel cwl/sar_coherence.cwl sar/example_inputs/input_dict_2018_vh_new.json
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_coherence.py
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/cloudinsar/openeo_insar:20251216T0834-json_logging
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
  temporal_baseline:
    type: int
  burst_id:
    type: int
  coherence_window_az:
    type: int?
  coherence_window_rg:
    type: int?
  polarization:
    type: string
  sub_swath:
    type: string
outputs:
  output_file:
    type: File[]
    outputBinding:
      glob: [ "collection.json", "*.json", "*.tif", "*.tiff" ]
