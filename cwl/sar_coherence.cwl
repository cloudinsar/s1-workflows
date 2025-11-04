#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_coherence.py

requirements:
  - class: InitialWorkDirRequirement
    listing:
      - entryname: "arguments.json"
        entry: $(inputs)
  - class: DockerRequirement
    dockerPull: registry.stag.warsaw.openeo.dataspace.copernicus.eu/rand/openeo_insar:1.46
  - class: NetworkAccess
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
  n_az_looks:
    type: int?
  n_rg_looks:
    type: int?
  polarization:
    type: string
  sub_swath:
    type: string?

arguments:
  - arguments.json

outputs:
  output_file:
    type: File[]
    outputBinding:
      glob: [ "S1_2images_collection.json", "*2images*" ]
