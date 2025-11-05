#!/usr/bin/env cwl-runner
# Example on how to run locally: cwltool --tmpdir-prefix=$HOME/tmp/ --force-docker-pull --leave-container --parallel sar_coherence.cwl /home/emile/openeo/s1-workflows/sar/example_inputs/input_dict_2024_vv.json
cwlVersion: v1.2
$graph:
  - id: sub_collection_maker
    class: CommandLineTool
    baseCommand: /src/sar/sar_coherence.py
    requirements:
      - class: InitialWorkDirRequirement
        listing:
          - entryname: "arguments.json"
            entry: $(inputs)
      - class: DockerRequirement
        dockerPull: registry.stag.warsaw.openeo.dataspace.copernicus.eu/rand/openeo_insar:1.47
      - class: NetworkAccess
        networkAccess: true

    inputs:
      # TODO: rename toInSAR_pairs?
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
      n_az_looks:
        type: int?
      n_rg_looks:
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
          n_az_looks: n_az_looks
          n_rg_looks: n_rg_looks
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
        dockerPull: vito-docker.artifactory.vgt.vito.be/openeo-geopyspark-driver-example-stac-catalog:1.4

    baseCommand: "/data/simple_stac_merge.py"
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
      n_az_looks:
        type: int?
      n_rg_looks:
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
          n_az_looks: main/n_az_looks
          n_rg_looks: main/n_rg_looks
          polarization: main/polarization
          sub_swath: main/sub_swath
        out: [ scatter_node_out ]
        run: "#scatter_node"
      gatherer_node_step2:
        in:
          simple_stac_merge_in1: gatherer_node_step1/scatter_node_out
        out: [ simple_stac_merge_out ]
        run: "#simple_stac_merge"
      directory_to_file_list:
        run:
          class: ExpressionTool
          requirements:
            InlineJavascriptRequirement: { }
            LoadListingRequirement:
              loadListing: shallow_listing
          inputs:
            directory_to_file_list_in: Directory
          expression: '${return {"directory_to_file_list_out": inputs.directory_to_file_list_in.listing};}'
          outputs:
            directory_to_file_list_out: File[]
        in:
          directory_to_file_list_in: gatherer_node_step2/simple_stac_merge_out
        out: [ directory_to_file_list_out ]
    outputs:
      - id: gatherer_node_out
        outputSource: directory_to_file_list/directory_to_file_list_out
        type: File[]
