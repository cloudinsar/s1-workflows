#!/usr/bin/env cwl-runner
cwlVersion: v1.2
class: CommandLineTool
baseCommand: /src/sar/sar_coherence.py
requirements:
  DockerRequirement:
    dockerPull: ghcr.io/cloudinsar/openeo_insar:20251126T2224
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
