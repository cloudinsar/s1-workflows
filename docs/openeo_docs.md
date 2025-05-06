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
