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
#   - polarization: one of "vv", "vh"
#   - sub_swath: one of "IW1", "IW2", "IW3"
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
      This process generates a time series of Sentinel‑1 interferometric coherence for a set of interferometric pairs. The area of interest is specified at burst level using the Sentinel‑1 burst_id and sub_swath, ensuring precise spatial targeting and consistent acquisition geometry across the time series.
      Interferometric pairs are automatically defined by specifying a temporal extent and temporal baseline.
      The workflow is implemented using ESA SNAP operators and is defined as a Common Workflow Language (CWL) pipeline [sar_coherence.cwl](https://github.com/cloudinsar/s1-workflows/blob/main/cwl/sar_coherence_parallel_temporal_extent.cwl).
      Interferometric coherence provides a quantitative measure of phase stability between acquisitions and is widely used to assess surface change and temporal decorrelation driven by factors such as snow cover, vegetation dynamics, surface moisture, or mass movement. Coherence time series can be used for a variety of scientific and operational applications, including land cover classification, change detection, and as a diagnostic input for more advanced SAR analysis workflows.
      
      An example on how to use it:
      
      ```python
      import openeo

      connection = openeo.connect("openeo.dataspace.copernicus.eu/").authenticate_oidc()
      stac_resource = connection.datacube_from_process(
          "sentinel1_sar_coherence",
          namespace="https://raw.githubusercontent.com/ESA-APEx/apex_algorithms/refs/heads/main/algorithm_catalog/eurac/sentinel1_sar_coherence/openeo_udp/sentinel1_sar_coherence.json",
          **{
              "temporal_extent": ["2018-01-28", "2018-02-04"],
              "temporal_baseline": 6,
              "burst_id": 329488,
              "coherence_window_az": 2,
              "coherence_window_rg": 10,
              "polarization": "VH",
              "sub_swath": "IW2"
          }
      )
      
      job = stac_resource.create_job(title="sentinel1_sar_coherence test")
      job.start_and_wait()
      job.get_results().download_files()
      ```
    
    requirements:
      - class: ScatterFeatureRequirement
      - class: StepInputExpressionRequirement
      - class: InlineJavascriptRequirement
      - class: SubworkflowFeatureRequirement
    
    inputs:
      burst_id:
        type: int?
        doc: |
          A temporal extent could have multiple bursts per day. Use [this notebook](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/LPS_DEMO/Input_selection.ipynb) to find a fitting `burst_id`.
          Alternatively, the burst id map can be downloaded here: [Burst ID Maps 2022-05-30](https://sar-mpc.eu/files/S1_burstid_20220530.zip).
          You can also specify `temporal_extent` instead, so that a `burst_id` gets automatically selected.
      
      polarization:
        - type: enum
          symbols: [ "VV", "VH" ]

      sub_swath:
        type:
          type: enum
          symbols: [ "IW1", "IW2", "IW3" ]
        doc: "Sub-swath identifier"
      
      temporal_extent:
        type: string[]
        doc: "Temporal extent as [start_date, end_date], e.g., ['2024-08-01', '2024-09-30']. Specify at least a 6 days interval to make sure at least one pair gets found."

      spatial_extent:
        type: Any?
        doc: Specifies area where to search for bursts. If multiple bursts are found, the one with the lowest id number will be selected. This parameter can be used instead of `burst_id`.

      temporal_baseline:
        type: int
        doc: "Should be a multiple of 6. This is used to select how many days the secondary date will be after the primary for each date pair."
      
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
          spatial_extent: spatial_extent
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
          spatial_extent: spatial_extent
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
                  "spatial_extent": inputs.spatial_extent,
                  "polarization": inputs.polarization,
                  "sub_swath": inputs.sub_swath,
                  "temporal_extent": inputs.temporal_extent,
                  "temporal_baseline": inputs.temporal_baseline
                });
              }
      - class: DockerRequirement
        dockerPull: ghcr.io/cloudinsar/openeo_insar:20260331T1144
      - class: NetworkAccess
        networkAccess: true
      - class: InlineJavascriptRequirement
    
    inputs:
      burst_id:
        type: int?
      spatial_extent:
        type: Any?
      polarization:
        - type: enum
          symbols: [ "VV", "VH" ]
      sub_swath:
        - type: enum
          symbols: [ "IW1", "IW2", "IW3" ]
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

    # https://github.com/Open-EO/openeo-geopyspark-driver/blob/master/docker/local_batch_job/example_stac_catalog/simple_stac_merge.py
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
                  "spatial_extent": inputs.spatial_extent,
                  "polarization": inputs.polarization,
                  "sub_swath": inputs.sub_swath,
                  "coherence_window_rg": inputs.coherence_window_rg,
                  "coherence_window_az": inputs.coherence_window_az
                });
              }
      - class: DockerRequirement
        dockerPull: ghcr.io/cloudinsar/openeo_insar:20260331T1144
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
        type: int?
      spatial_extent:
        type: Any?
      polarization:
        - type: enum
          symbols: [ "VV", "VH" ]
      sub_swath:
        - type: enum
          symbols: [ "IW1", "IW2", "IW3" ]
      coherence_window_rg:
        type: int?
      coherence_window_az:
        type: int?
    
    outputs:
      pair_output:
        type: Directory
        outputBinding:
          glob: .
