#!/usr/bin/env cwl-runner
# Example on how to run locally: cwltool --tmpdir-prefix=$HOME/tmp/ --force-docker-pull --leave-container --leave-tmpdir --parallel cwl/sar_coherence.cwl sar/example_inputs/input_dict_2024_vv_new.json
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_coherence.py
requirements:
  DockerRequirement:
    dockerPull: registry.stag.warsaw.openeo.dataspace.copernicus.eu/rand/openeo_insar:1.53
  NetworkAccess:
    networkAccess: true
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
