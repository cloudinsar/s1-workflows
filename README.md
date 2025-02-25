# s1-workflows
Collection of Sentinel-1 workflows and tests using ESA SNAP

## Prerequisites:
- docker
- 10-20 GB of disk space

## Minimal Example: extract and run the preprocessing on two bursts

### 1) Get the sample data

We use the CDSE burst extractor tool from https://github.com/eu-cdse/utilities to get the Sentinel-1 bursts from 2024-08-14 to 2024-08-26 intersecting the point (x=10.756, y=46.747):

Build the cdse utilities docker as explained here: https://github.com/eu-cdse/utilities. Then get the data with the following query (get the credentials for CDSE from https://eodata-s3keysmanager.dataspace.copernicus.eu/panel/s3-credentials and replace AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY):

```
docker run -it -v /home/<username>:/home/ubuntu -e AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID> -e AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY> cdse_utilities sentinel1_burst_extractor_spatiotemporal.sh -o /home/ubuntu -s 2024-08-14 -e 2024-08-26 -x 10.756 -y 46.747 -p vv
```

At the moment the filtering based on relative orbit number is not available in the CDSE utilities. Thus we manually select only the image acquired by a single orbit (i.e. 15) in the period of interest. The resulting list of files are:
- S1A_SLC_20240814T171550_030345_IW3_VV_042880.SAFE
- S1A_SLC_20240826T171550_030345_IW3_VV_043168.SAFE

![image](https://github.com/user-attachments/assets/274ab2d9-345a-418a-88ac-be5300a4ad1c)


### 2) Build the SNAP docker image

Clone this repo and follow the instructions: https://github.com/cloudinsar/esa-snap-docker

### 3) Run the preprocessing SNAP workflow (GeoTIFF output):

The preprocessing SNAP xml graph is defined as

![image](https://github.com/user-attachments/assets/ddc18de7-4813-45cd-8568-6c3eb5b738b3)

The SNAP xml graph for preprocessing is stored in the repo and can be run with the following command:

```
docker run -it -v /home/<username>/s1-workflows/:/src/preprocessing/ esa-snap-11 gpt /src/preprocessing/s1-workflows/graphs/pre-processing_stackOverview_2images_GeoTiff.xml -Pinput1=/src/preprocessing/S1A_SLC_20240814T171550_030345_IW3_VV_042880.SAFE/manifest.safe -Pinput2=/src/preprocessing/S1A_SLC_20240826T171550_030345_IW3_VV_043168.SAFE/manifest.safe -PstackOverview_filename=/src/preprocessing/docker_result/stackOverview_2images.json -PcoregisteredStack_filename=/src/preprocessing/S1A_SLC_20240814T171550_030345_IW3_VV_042880_Orb_Stack_2images
```

## Minimal Example: Run burst extraction and preprocessing in one docker image:

Running those command will run the same kind of docker image that OpenEO runs to get the preprocessed data.
If not running on Ubuntu, replace /home/ubuntu with the path to the folder where the data will be stored.
When no arguments are passed to OpenEO_insar.py, some example arguments are used.
```bash
docker build -t openeo_insar:1.2 . -f OpenEO_Dockerfile
docker run -it -v /home/ubuntu:/root -e AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID> -e AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY> --rm openeo_insar:1.2 python3 OpenEO_insar.py
```
