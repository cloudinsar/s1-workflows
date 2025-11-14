#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_slc_preprocessing.py
requirements:
  DockerRequirement:
    dockerPull: registry.stag.warsaw.openeo.dataspace.copernicus.eu/rand/openeo_insar:1.50
  NetworkAccess:
    networkAccess: true
inputs:
  temporal_extent:
    type: string[]
  burst_id:
    type: int
  master_date:
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
