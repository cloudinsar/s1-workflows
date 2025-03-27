## Prerequisites:
- docker
- 10-20 GB of disk space
- ...

## Sentinel-1 SLC burst processing workflow

Two different SLC burst processing workflow are proposed:
1) SNAP InSAR workflow
2) SNAP pre-processing + OpenEO InSAR workflow

Both workflows use the CDSE utilities (https://github.com/eu-cdse/utilities) to access to Sentinel-1 bursts

### 1) SNAP InSAR workflow

![image](https://github.com/user-attachments/assets/40eb2f08-12fa-447c-af2b-8f62fdffb99d)

The selection of sub swath, burstId and InSAR pair list can be accomplished by running the pyhton notebook notebooks/show_s1bursts.ipynb.

A sample SNAP graph for generating InSAR coherence is available at notebooks/graphs/coh_2images_GeoTiff.xml:
<img src="https://github.com/user-attachments/assets/d423825a-c3eb-4db9-8d49-4a43ddd22639" width=50% height=50%>

More complex graphs (e.g. for interferogram formation, uinterferogram filtering, unwrappinp, etc.) will be avaialable soon.

An example of the SNAP preprocessing including Sentinel-1 burst data access with the CDSE utilities is available at notebooks/s1_workflow.ipynb

### 2) SNAP pre-processing + OpenEO InSAR workflow

![image](https://github.com/user-attachments/assets/92ffead5-ede6-4999-a563-20a6bd6e963c)

The selection of sub swath, burstId and InSAR pair list can be accomplished by running the pyhton notebook notebooks/show_s1bursts.ipynb.

The SNAP pre-processing graph (notebooks/graphs/pre-processing_2images_SaveMst_GeoTiff.xml and notebooks/graphs/pre-processing_2images_SaveOnlySlv_GeoTiff.xml) involve the following operations:
![image](https://github.com/user-attachments/assets/11223d88-3aa3-4f00-9ad8-003c2af5a7aa)

InSAR OpenEO processes will be implemented and available soon.

An example of the SNAP preprocessing including Sentinel-1 burst data access with the CDSE utilities is available at notebooks/s1_workflow.ipynb

## Run burst extraction and preprocessing in one docker image:

Running those command will run the same kind of docker image that OpenEO runs to get the preprocessed data.
If not running on Ubuntu, replace /home/ubuntu with the path to the folder where the data will be stored.
When no arguments are passed to OpenEO_insar.py, some example arguments are used.
```bash
docker build -t openeo_insar:1.2 . -f OpenEO_Dockerfile
docker run -it -v /home/ubuntu:/root -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY --rm openeo_insar:1.2 python3 OpenEO_insar.py
```
