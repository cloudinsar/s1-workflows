#!/usr/bin/env cwl-runner

# WORKFLOW STRUCTURE ($graph with 3 components):
#
#   1. main (Workflow) - Orchestrates the 3 steps below
#      ├─   generate_pairs (CommandLineTool)
#      │    Queries Copernicus catalog for available bursts in date range
#      │    Creates InSAR pairs based on temporal baseline (e.g., 12 days)
#      │    Outputs: insar_pairs_inputs.json
#      │
#      ├─   extract_pairs (ExpressionTool)
#      │    Reads JSON file and extracts InSAR_pairs array
#      │    Converts File → Array for scatter processing
#      │    Outputs: array like [["2024-08-09","2024-08-21"], ["2024-08-21","2024-09-02"]]
#      │
#      └─   process_pairs (SCATTER)
#           Processes each pair in parallel (one job per pair)
#           Downloads bursts from S3, runs SNAP coherence processing
#           Outputs: Directory per pair with GeoTIFF results
#
#   2. get_insar_pairs (CommandLineTool) - Runs get_bursts.py script
#
#   3. extract_pairs_array (ExpressionTool) - JavaScript to parse JSON
#
#   4. process_single_pair (CommandLineTool) - Runs sar_coherence_parallel.py
#
#   5. simple_stac_merge (CommandLineTool) - Runs simple_stac_merge.py
#

# INPUTS (in JSON file):
#   - temporal_extent: ["start_date", "end_date"] e.g., ["2024-08-01", "2024-08-30"]
#   - temporal_baseline: Days between pairs (e.g., 12)
#   - burst_id: Sentinel-1 burst identifier (e.g., 249435)
#   - polarization: "vv" or "vh"
#   - sub_swath: "IW1", "IW2", or "IW3"
#   - coherence_window_rg/az: Window sizes for coherence estimation
#
# LOCAL USAGE:
#   cwltool --no-read-only --parallel --tmpdir-prefix=$HOME/tmp/ \
#           --preserve-environment=AWS_ACCESS_KEY_ID \
#           --preserve-environment=AWS_SECRET_ACCESS_KEY \
#           --preserve-environment=AWS_ENDPOINT_URL_S3 \
#           cwl/sar_coherence_parallel_temporal_extent.cwl sar/example_inputs/input_dict_2018_vh_new.json

cwlVersion: v1.2

$graph:
  - id: main
    class: Workflow

    doc: |
      Parallel InSAR coherence workflow:
      1. Generate InSAR pairs from input date range and burst parameters
      2. Process each pair in parallel (scatter)
      2. STAC results (removed for now)
    
    requirements:
      - class: ScatterFeatureRequirement
      - class: StepInputExpressionRequirement
      - class: InlineJavascriptRequirement
      - class: SubworkflowFeatureRequirement
    
    inputs:
      burst_id:
        type: int
        doc: "Sentinel-1 burst ID"
      
      polarization:
        type: string
        doc: "Polarization (vv or vh)"
      
      sub_swath:
        type: string
        default: "IW2"
        doc: "Sub-swath identifier (IW1, IW2, or IW3)"
      
      temporal_extent:
        type: string[]
        doc: "Temporal extent as [start_date, end_date], e.g., ['2024-08-01', '2024-09-30']"
      
      temporal_baseline:
        type: int
        doc: "Temporal baseline in days for pair generation"
      
      coherence_window_rg:
        type: int?
        default: 10
        doc: "Coherence window size in range direction"
      
      coherence_window_az:
        type: int?
        default: 2
        doc: "Coherence window size in azimuth direction"
    
    outputs:
      coherence_results:
        type: Directory
        outputSource: stac_merge/simple_stac_merge_out
        doc: "Directory containing STAC Collection of the results and related files"
    
    steps:
      generate_pairs:
        run: "#get_insar_pairs"
        in:
          burst_id: burst_id
          polarization: polarization
          sub_swath: sub_swath
          temporal_extent: temporal_extent
          temporal_baseline: temporal_baseline
        out: [insar_pairs_json]
      
      extract_pairs:
        run: "#extract_pairs_array"
        in:
          pairs_json_file: generate_pairs/insar_pairs_json
        out: [pairs_array]
      
      process_pairs:
        run: "#process_single_pair"
        scatter: InSAR_pair
        in:
          InSAR_pair: extract_pairs/pairs_array
          burst_id: burst_id
          polarization: polarization
          sub_swath: sub_swath
          coherence_window_rg: coherence_window_rg
          coherence_window_az: coherence_window_az
        out: [pair_output]

      stac_merge:
        run: "#simple_stac_merge"
        in:
          simple_stac_merge_in: process_pairs/pair_output
        out: [simple_stac_merge_out]
          
  
  - class: CommandLineTool
    id: get_insar_pairs
    
    doc: "Generate InSAR pairs based on burst ID and temporal parameters"
    
    baseCommand: /src/sar/get_bursts.py
    
    arguments:
      - arguments.json

    requirements:
      - class: InitialWorkDirRequirement
        listing:
          - entryname: "arguments.json"
            entry: |
              ${
                return JSON.stringify({
                  "burst_id": inputs.burst_id,
                  "polarization": inputs.polarization,
                  "sub_swath": inputs.sub_swath,
                  "temporal_extent": inputs.temporal_extent,
                  "temporal_baseline": inputs.temporal_baseline
                });
              }
      - class: DockerRequirement
        dockerPull: ghcr.io/cloudinsar/openeo_insar:20260127T1610
      - class: NetworkAccess
        networkAccess: true
      - class: InlineJavascriptRequirement
    
    inputs:
      burst_id:
        type: int
      polarization:
        type: string
      sub_swath:
        type: string
      temporal_extent:
        type: string[]
      temporal_baseline:
        type: int
    
    outputs:
      insar_pairs_json:
        type: File
        outputBinding:
          glob: "insar_pairs_inputs.json"
  
  - class: ExpressionTool
    id: extract_pairs_array
    
    doc: "Extract InSAR_pairs array from JSON file"
    
    requirements:
      - class: InlineJavascriptRequirement
    
    inputs:
      pairs_json_file:
        type: File
        loadContents: true
    
    outputs:
      pairs_array:
        type:
          type: array
          items:
            type: array
            items: string
    
    expression: |
      ${
        var data = JSON.parse(inputs.pairs_json_file.contents);
        return {"pairs_array": data.InSAR_pairs};
      }

  - class: CommandLineTool
    id: simple_stac_merge

    doc: "Merge the coherence results in a single STAC Collection"

    baseCommand: ["/data/simple_stac_merge.py", "S1_2images_collection.json"]

    requirements:
      - class: DockerRequirement
        dockerPull: vito-docker.artifactory.vgt.vito.be/openeo-geopyspark-driver-example-stac-catalog:1.7
      - class: NetworkAccess
        networkAccess: true

    inputs:
      simple_stac_merge_in:
        type: Directory[]
        inputBinding: { }
    outputs:
      simple_stac_merge_out:
        type: Directory
        outputBinding:
          glob: .

  - class: CommandLineTool
    id: process_single_pair
    
    doc: "Process a single InSAR pair to generate coherence"
    
    baseCommand: /src/sar/sar_coherence_parallel.py

    arguments:
      - arguments.json
    
    requirements:
      - class: InitialWorkDirRequirement
        listing:
          - entryname: "arguments.json"
            entry: |
              ${
                return JSON.stringify({
                  "InSAR_pairs": [inputs.InSAR_pair],
                  "burst_id": inputs.burst_id,
                  "polarization": inputs.polarization,
                  "sub_swath": inputs.sub_swath,
                  "coherence_window_rg": inputs.coherence_window_rg,
                  "coherence_window_az": inputs.coherence_window_az
                });
              }
      - class: DockerRequirement
        dockerPull: ghcr.io/cloudinsar/openeo_insar:20260127T1610
      - class: NetworkAccess
        networkAccess: true
      - class: ResourceRequirement
        ramMin: 7000
        ramMax: 7000
        coresMin: 2
        coresMax: 7
      - class: InlineJavascriptRequirement
      
    inputs:
      InSAR_pair:
        type: string[]
        doc: "Single InSAR pair as [primary_date, secondary_date]"
      burst_id:
        type: int
      polarization:
        type: string
      sub_swath:
        type: string
      coherence_window_rg:
        type: int?
      coherence_window_az:
        type: int?
    
    outputs:
      pair_output:
        type: Directory
        outputBinding:
          glob: .
