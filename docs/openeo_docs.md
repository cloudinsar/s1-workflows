## How to run coherence and preprocessing in OpenEO

Example of a process graph to run coherence:
![image](./img/openeo_insar_coherence_in_editor.png)
The parameters used in the insar_coherence node are shown here:
![image](./img/openeo_insar_coherence_options.png)

Preprocessing without coherence can be done with a different node. The result is a stack of coregistered SLC in SAR geometry, therefore it cannot be geo-referred on a map. A sample result is shown including the amplitude image derived from the real and imaginary part of the SLC:

![amplitude](https://github.com/user-attachments/assets/e91e39c1-150a-400b-9f4a-1deec5f37016)

the latitude raster:

![lat](https://github.com/user-attachments/assets/d83434e5-3e8d-4263-a53e-8d3d0316c173)

the longitude raster:

![lon](https://github.com/user-attachments/assets/da40297a-f611-4f92-a713-87274fdbe075)


## How is insar integrated in openEO

- The Python notebooks from Eurac where converted to plain Python scripts that output a STAC collection.
- Those scripts are embedded in a docker image.
- Those docker images are referred to in `.cwl` files
- The sar_coherence and sar_slc_preprocessing openEO processes will call those files on Calrissian, and the output STAC
  catalog will be written into an S3 bucket.

The following image showcases the architecture of the OpenEO InSAR process:
![image](./img/openeo_insar.drawio.png)

## How to access:

Follow the instructions here to make an account: https://documentation.dataspace.copernicus.eu/Registration.html

### Run preprocessing in OpenEO:

Please consult the integration tests to see examples on how to run the processes in openEO:
https://github.com/cloudinsar/s1-workflows/blob/main/tests/test_insar_backend.py

### Run locally for debugging:

Most CWL scripts have an example command to run them locally with `cwltool`. For example:
[sar_coherence](https://github.com/cloudinsar/s1-workflows/blob/main/cwl/sar_coherence.cwl#L2)

You will need S3 credentials: https://documentation.dataspace.copernicus.eu/APIs/S3.html
```bash
export AWS_ACCESS_KEY_ID="***"
export AWS_SECRET_ACCESS_KEY="***"
export AWS_ENDPOINT_URL_S3="https://eodata.dataspace.copernicus.eu"
```
