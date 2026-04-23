# ClouDInSAR

CloudInSAR is an open-source project providing cloud-native Sentinel-1 InSAR processing workflows integrated into openEO and executed within the Copernicus Data Space Ecosystem (CDSE).
The project enables scalable, reproducible, and user-friendly access to Sentinel‑1 SLC‑based interferometric processing without the need for local data downloads or on-premise computing infrastructure.

## Overview
Sentinel-1 Interferometric Synthetic Aperture Radar (InSAR) is a powerful tool for monitoring surface deformation and other Earth surface processes. However, processing Sentinel-1 Single Look Complex (SLC) data remains computationally demanding and technically complex.
ClouDInSAR addresses these challenges by:

- extending openEO with native Sentinel-1 InSAR capabilities,
- enabling fully cloud-based InSAR workflows executed close to the data,
- providing modular, open-source processes suitable for both research and operational applications.

All processing chains are implemented using ESA SNAP and exposed through openEO process graphs, ensuring scientific robustness and transparency.

## Sentinel-1 InSAR openEO processes
The repository provides three main openEO User Defined Processes (UDPs):

1. [`sentinel1_sar_coherence`](https://algorithm-catalogue.apex.esa.int/apps/sentinel1_sar_coherence) -
Generates geocoded InSAR coherence products.

3. [`sentinel1_sar_interferogram`](https://algorithm-catalogue.apex.esa.int/apps/sentinel1_sar_interferogram) -
Generates geocoded interferograms including coherence, and wrapped and unwrapped phase.

4. `sentinel1_slc_preprocessing` -
Generates a STAC collection of co-registered Sentinel-1 SLC bursts in SAR geometry.

## Burst-based processing
All InSAR workflows in CloudInSAR are designed around a burst level processing approach, optimized for Sentinel-1 TOPS acquisitions. Instead of processing full swaths or scenes, the openEO InSAR processes operate on individual Sentinel-1 bursts, which significantly improves scalability and computational efficiency in cloud environments.
Each openEO InSAR process therefore requires the explicit specification of:

- `burst_id` – the unique identifier of the Sentinel-1 burst
- `subswath` – the Sentinel-1 sub-swath (IW1, IW2, or IW3) containing the burst

## Burst id selection and InSAR pairs definition
To support users in selecting the input parameters for the InSAR openEO processes, the repository provides the [`InSAR_workflow_input_selection.ipynb`](https://github.com/cloudinsar/s1-workflows/blob/main/input_selection/InSAR_workflow_input_selection.ipynb) notebook. This notebook assists users in:

- retrieving all Sentinel-1 bursts intersecting a given area of interest;
- visualizing burst footprints and acquisition geometries;
- filtering bursts by track, sub-swath, and relative position;
- identifying the appropriate burst_id and sub_swath values required as inputs for the openEO InSAR processes;
- show a calendar of Sentinel-1 acquisitions
- define the InSAR pairs based on perpendicular and temporal baseline filtering

The notebook relies on the supporting functions implemented in [`s1_burst_lib.py`](https://github.com/cloudinsar/s1-workflows/blob/main/input_selection/s1_burst_lib.py) and provides a reproducible and transparent way to prepare inputs for the openEO Sentinel-1 InSAR workflows.

## Documentation

- Process documentation: [APEx Algorithm Catalogue](https://algorithm-catalogue.apex.esa.int/)
- Example workflows: [`examples/`](https://github.com/cloudinsar/s1-workflows/tree/main/examples)

## Get Started
Clone the repository, explore the example notebooks, and start building your own cloud-native InSAR workflows with openEO.
