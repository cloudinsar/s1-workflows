# s1-workflows
Collection of Sentinel-1 workflows and tests using ESA SNAP

## Prerequisites:
- docker
- 10-20 GB of disk space

## Minimal Example: extract and co-register two bursts

### Get the sample data

We use the sentinel1_burst_extractor.sh from https://github.com/eu-cdse/utilities to get our source data.

Build the cdse utilities docker as explained here: https://github.com/eu-cdse/utilities

Get the data with the following query (get the credentials for CDSE and replace AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY):

```
docker run -it -v /home/ubuntu/utilities:/home/ubuntu -e AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY cdse_utilities sentinel1_burst_extractor_spatiotemporal.sh -o /home/ubuntu -s 2024-08-11 -e 2024-08-23 -x 13.228 -y 52.516 -p vv
```

### Build the SNAP docker image

Clone this repo and follow the instructions: https://github.com/cloudinsar/esa-snap-docker

### Run the SNAP workflow (BEAM-DIMAP output):
```
docker run -it -v /home/ubuntu/s1-workflows/:/src/preprocessing/ esa-snap-11 gpt /src/preprocessing/pre-processing_stackOverview_2images_ZNAP.xml -Pinput1=/src/preprocessing/S1A_SLC_20240811T165248_311760_IW2_VV_027360.SAFE/manifest.safe -Pinput2=/src/preprocessing/S1A_SLC_20240823T165249_311760_IW2_VV_022944.SAFE/manifest.safe -Ptarget1=/src/preprocessing/docker_result/stackOverview_2images_ZNAP.json -Ptarget2=/src/preprocessing/docker_result/S1A_SLC_20240811T165248_311760_IW2_VV_027360_Orb_Stack_2images_ZNAP
```