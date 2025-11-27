#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_coherence.py
requirements:
  DockerRequirement:
    dockerPull: registry.stag.warsaw.openeo.dataspace.copernicus.eu/rand/openeo_insar:1.50
  NetworkAccess:
    networkAccess: true
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
  polarization:
    type: string
  sub_swath:
    type: string?
outputs:
  output_file:
    type: File[]
    outputBinding:
      glob: [ "collection.json", "*.json", "*.tif", "*.tiff" ]
