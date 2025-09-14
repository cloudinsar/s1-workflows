## Prerequisites:
- docker
- 10-20 GB of disk space
- ...

## Sentinel-1 SLC burst processing workflow

Two different SLC burst processing workflow are proposed:
1) openEO-SNAP InSAR workflow
2) openEO-SNAP pre-processing + OpenEO InSAR workflow

The openEO-SNAP InSAR workflow is a more straightforward workflow using SNAP for most operations. It is designed to be efficient and user-friendly, providing a benchmark for performance evaluation. The openEO-SNAP pre-processing + OpenEO InSAR workflow offers greater flexibility and allows users to implement their own functions directly in OpenEO.

Both workflows use the [CDSE utilities](https://github.com/eu-cdse/utilities) to access to Sentinel-1 bursts

### 1) openEO-SNAP InSAR workflow

![image](https://github.com/user-attachments/assets/40eb2f08-12fa-447c-af2b-8f62fdffb99d)

The selection of sub swath, burstId and InSAR pair list can be accomplished by running the pyhton notebook [InSAR_workflow_input_selection.ipynb](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/InSAR_workflow_input_selection.ipynb).

A sample SNAP graph for generating InSAR coherence is available at [coh_2images_GeoTiff.xml](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/graphs/coh_2images_GeoTiff.xml):
<img src="https://github.com/user-attachments/assets/d423825a-c3eb-4db9-8d49-4a43ddd22639" width=50% height=50%>

More complex graphs (e.g. for interferogram formation, interferogram filtering, unwrapping, etc.) will be avaialable soon.

An example of the SNAP preprocessing and coherence calculation including Sentinel-1 burst data access with openEO is showcased here: [run-coherence-in-openeo](https://github.com/cloudinsar/s1-workflows/blob/main/docs/openeo_docs.md#run-coherence-in-openeo)

### 2) SNAP pre-processing + OpenEO InSAR workflow

![image](https://github.com/user-attachments/assets/92ffead5-ede6-4999-a563-20a6bd6e963c)

The selection of sub swath, burstId and InSAR pair list can be accomplished by running the pyhton notebook [InSAR_workflow_input_selection.ipynb](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/InSAR_workflow_input_selection.ipynb).

The SNAP pre-processing graph ([pre-processing_2images_SaveMst_GeoTiff.xml](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/graphs/pre-processing_2images_SaveMst_GeoTiff.xml) and [pre-processing_2images_SaveOnlySlv_GeoTiff.xml](https://github.com/cloudinsar/s1-workflows/blob/main/notebooks/graphs/pre-processing_2images_SaveOnlySlv_GeoTiff.xml)) involve the following operations:
![image](https://github.com/user-attachments/assets/11223d88-3aa3-4f00-9ad8-003c2af5a7aa)

InSAR OpenEO processes will be implemented and available soon.

An example of the SNAP preprocessing including Sentinel-1 burst data access with openEO is showcased here: [run-preprocessing-in-openeo](https://github.com/cloudinsar/s1-workflows/blob/main/docs/openeo_docs.md#run-preprocessing-in-openeo)

## Run coherence and preprocessing in a docker image:

Running those commands will run the same docker image that OpenEO runs to get the preprocessed data.
First CD to this the root of this repo.
When no arguments are passed to the Python script, some example arguments are used.
To run preprocessing, replace OpenEO_insar_coherence.py with OpenEO_insar_preprocessing.py
`-v $PWD:/src` is for better performance when developing. If it causes issues, you can remove it.
```bash
docker build -t openeo_insar:1.14 . -f OpenEO_Dockerfile
# Linux:
docker run -it -v $PWD:/src -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY --rm openeo_insar:1.14 python3 /src/OpenEO_insar_coherence.py
# Windows:
docker run -it -v %cd%:/src -e AWS_ACCESS_KEY_ID=%AWS_ACCESS_KEY_ID% -e AWS_SECRET_ACCESS_KEY=%AWS_SECRET_ACCESS_KEY% --rm openeo_insar:1.14 python3 /src/OpenEO_insar_coherence.py
```

## More Documentation:

- [OpenEO integration](docs/openeo_docs.md)
- [Sample notebooks documentation](notebooks/README.md)
