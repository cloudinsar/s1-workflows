#!/usr/bin/env cwl-runner
# Example on how to run locally: cwltool --tmpdir-prefix=$HOME/tmp/ --force-docker-pull --leave-container --leave-tmpdir --no-read-only --parallel --preserve-environment=AWS_ENDPOINT_URL_S3 --preserve-environment=AWS_ACCESS_KEY_ID --preserve-environment=AWS_SECRET_ACCESS_KEY cwl/sar_interferogram_parallel.cwl sar/example_inputs/input_dict_2024_vv.json
cwlVersion: v1.2
$graph:
  - id: sub_collection_maker
    class: CommandLineTool
    doc: |
      This process computes a time series of Interferometric Coherence, Wrapped Interferograms and Unwrapped Interferograms for a Sentinel-1 burst of interest.
      The interferometric pairs to be processed must be specified in the InSAR_pair list. The burst of interest must be selected by providing the burst_id and sub_swath.
      The implementation is based on SNAP and defined as a CWL (Common Workflow Language) available here: [sar_interferogram.cwl](https://github.com/cloudinsar/s1-workflows/blob/main/cwl/sar_interferogram.cwl)
      <https://www.eurac.edu/en/projects/cloudinsar>.

      An example on how to use it:
      
      ```python
      import openeo

      connection = openeo.connect("openeo.dataspace.copernicus.eu/").authenticate_oidc()
      stac_resource = connection.datacube_from_process(
        "sar_interferogram",
        namespace="https://raw.githubusercontent.com/ESA-APEx/apex_algorithms/refs/heads/insar/algorithm_catalog/eurac/sar_interferogram/openeo_udp/sar_interferogram.json",
        **{
            "InSAR_pairs": [
                [
                    "2018-01-28",
                    "2018-02-03"
                ]
            ],
            "burst_id": 329488,
            "coherence_window_az": 2,
            "coherence_window_rg": 10,
            "n_az_looks": 1,
            "n_rg_looks": 4,
            "polarization": "VH",
            "sub_swath": "IW2"
        }
      )
      
      job = stac_resource.create_job(title="sar_interferogram test")
      job.start_and_wait()
      job.get_results().download_files()
      ```
    baseCommand: /src/sar/sar_interferogram_parallel.py
    requirements:
      - class: InitialWorkDirRequirement
        listing:
          - entryname: "arguments.json"
            entry: $(inputs)
      - class: DockerRequirement
        dockerPull: ghcr.io/cloudinsar/openeo_insar:20260331T0925-parallel_interferogram
      - class: NetworkAccess
        networkAccess: true
      - class: ResourceRequirement
        ramMin: 7000
        ramMax: 7000
        coresMin: 2
        coresMax: 7

    inputs:
      InSAR_pairs:
        type:
          type: array
          items: string
        doc: "The list of [primary date, secondary date] pairs used to compute the interferogram. Use [this notebook](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/LPS_DEMO/Input_selection.ipynb) to create the list of insar pairs based on your requirements."
      burst_id:
        type: int
        doc: |
              The Sentinel-1 burst identifier. Use [this notebook](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/LPS_DEMO/Input_selection.ipynb) to find a fitting `burst_id`.
              Alternatively, the burst id map can be downloaded here: [Burst ID Maps 2022-05-30](https://sar-mpc.eu/files/S1_burstid_20220530.zip)."
      coherence_window_rg:
        type: int?
        default: 10
        doc: "Coherence window size in range direction"
      coherence_window_az:
        type: int?
        default: 2
        doc: "Coherence window size in azimuth direction"
      n_rg_looks:
        type: int?
        default: 4
        doc: "Multi-look window size in range direction"
      n_az_looks:
        type: int?
        default: 1
        doc: "Multi-look window size in azimuth direction"
      polarization:
        type: string
      sub_swath:
        type: string

    arguments:
      - arguments.json

    outputs:
      sub_collection_maker_out:
        type: Directory
        outputBinding:
          glob: .

  - id: scatter_node
    class: Workflow
    inputs:
      InSAR_pairs:
        type:
          type: array
          items:
            type: array
            items: string
      burst_id:
        type: int?
      coherence_window_az:
        type: int?
      coherence_window_rg:
        type: int?
      polarization:
        type: string
      sub_swath:
        type: string?

    requirements:
      - class: ScatterFeatureRequirement

    steps:
      scatter_node_step:
        scatter: [ InSAR_pairs ]
        scatterMethod: flat_crossproduct
        in:
          InSAR_pairs: InSAR_pairs
          burst_id: burst_id
          coherence_window_az: coherence_window_az
          coherence_window_rg: coherence_window_rg
          polarization: polarization
          sub_swath: sub_swath

        out: [ sub_collection_maker_out ]
        run: "#sub_collection_maker"

    outputs:
      - id: scatter_node_out
        outputSource: scatter_node_step/sub_collection_maker_out
        type: Directory[]

  - id: simple_stac_merge
    class: CommandLineTool
    requirements:
      - class: DockerRequirement
        dockerPull: vito-docker.artifactory.vgt.vito.be/openeo-geopyspark-driver-example-stac-catalog:1.7
      - class: NetworkAccess
        networkAccess: true

    baseCommand: ["/data/simple_stac_merge.py", "collection.json"]
    inputs:
      simple_stac_merge_in1:
        type: Directory[]
        inputBinding: { }
    outputs:
      simple_stac_merge_out:
        type: Directory
        outputBinding:
          glob: .

  - id: main
    class: Workflow
    inputs:
      InSAR_pairs:
        type:
          type: array
          items:
            type: array
            items: string
      burst_id:
        type: int?
      coherence_window_az:
        type: int?
      coherence_window_rg:
        type: int?
      polarization:
        type: string
      sub_swath:
        type: string?

    requirements:
      - class: SubworkflowFeatureRequirement

    steps:
      gatherer_node_step1:
        in:
          InSAR_pairs: main/InSAR_pairs
          burst_id: main/burst_id
          coherence_window_az: main/coherence_window_az
          coherence_window_rg: main/coherence_window_rg
          polarization: main/polarization
          sub_swath: main/sub_swath
        out: [ scatter_node_out ]
        run: "#scatter_node"
      gatherer_node_step2:
        in:
          simple_stac_merge_in1: gatherer_node_step1/scatter_node_out
        out: [ simple_stac_merge_out ]
        run: "#simple_stac_merge"
    outputs:
      - id: gatherer_node_out
        outputSource: gatherer_node_step2/simple_stac_merge_out
        type: Directory
