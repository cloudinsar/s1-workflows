#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: CommandLineTool
baseCommand: /src/sar/sar_interferogram.py
requirements:
  DockerRequirement:
    dockerPull: registry.stag.warsaw.openeo.dataspace.copernicus.eu/rand/openeo_insar:1.44
inputs:
  input_base64_json:
    type: string
    inputBinding:
      position: 1
outputs:
  output_file:
    type: File[]
    outputBinding:
      glob: ["S1_2images_collection.json", "*phase_coh_*"]
