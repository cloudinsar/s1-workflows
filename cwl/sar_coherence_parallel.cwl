#!/usr/bin/env cwl-runner
# Example on how to run locally: cwltool --tmpdir-prefix=$HOME/tmp/ --force-docker-pull --leave-container --leave-tmpdir --parallel cwl/sar_coherence_parallel.cwl sar/example_inputs/input_dict_2024_vv.json
cwlVersion: v1.2
$graph:
  - id: sub_collection_maker
    class: CommandLineTool
    baseCommand: /src/sar/sar_coherence_easy_to_parallelize.py
    requirements:
      - class: InitialWorkDirRequirement
        listing:
          - entryname: "arguments.json"
            entry: $(inputs)
      - class: DockerRequirement
        dockerPull: ghcr.io/cloudinsar/openeo_insar:20260107T1050
      - class: NetworkAccess
        networkAccess: true
      - class: ResourceRequirement
        ramMin: 7000
        ramMax: 7000
        coresMin: 2

    inputs:
      # TODO: Make original array of pairs form?
      InSAR_pairs:
        type:
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
        type: int
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

    baseCommand: ["/data/simple_stac_merge.py", "S1_2images_collection.json"]
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
        type: int
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
