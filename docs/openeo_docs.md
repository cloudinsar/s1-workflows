## How to run coherence and preprocessing in OpenEO

Example of a process graph to run coherence:
![image](./img/openeo_insar_coherence_in_editor.png)
The parameters used in the insar_coherence node are shown here:
![image](./img/openeo_insar_coherence_options.png)

Preprocessing without coherence can be done with a different node. The result is difficult to visualise on a map because
it has no geospatial information.
However, it shows fine in Q-GIS:
![image](./img/openeo_insar_preprocessing.png)

## How is insar integrated in openEO

- The Python notebooks from Eurac where converted to plain Python scripts that output a STAC collection.
- Those scripts are embedded in a docker image.
- Those docker images are referred to in `.cwl` files
- The insar_coherence and insar_preprocessing openEO processes will call those files on Calrissian, and the output STAC
  catalog will be written into an S3 bucket.

The following image showcases the architecture of the OpenEO InSAR process:
![image](./img/openeo_insar.drawio.png)

## How to access:

Follow the instructions here to make an account: https://documentation.dataspace.copernicus.eu/Registration.html

### Run preprocessing in OpenEO:

```python
import openeo

url = "https://openeo.dataspace.copernicus.eu"
connection = openeo.connect(url).authenticate_oidc()

datacube = openeo.rest.datacube.DataCube(
  openeo.rest.datacube.PGNode(
    "insar_preprocessing",
    arguments={
      "burst_id": 249435,
      "sub_swath": "IW2",
      "InSAR_pairs": [
        ["2024-08-09", "2024-08-21"],
        ["2024-08-09", "2024-09-02"],
      ],
      "polarization": "vv"
    },
  ),
  connection=connection,
)

job = datacube.create_job()
job.start_and_wait()
job.get_results().download_files()
```

### Run coherence in OpenEO:

```python
import openeo

url = "https://openeo.dataspace.copernicus.eu"
connection = openeo.connect(url).authenticate_oidc()

datacube = openeo.rest.datacube.DataCube(
  openeo.rest.datacube.PGNode(
    "insar_coherence",
    arguments={
      "burst_id": 249435,
      "sub_swath": "IW2",
      "InSAR_pairs": [
        ["2024-08-09", "2024-08-21"],
        ["2024-08-09", "2024-09-02"],
      ],
      "polarization": "vv"
    },
  ),
  connection=connection,
)

job = datacube.create_job()
job.start_and_wait()
job.get_results().download_files()
```
