# ClouDInSAR: sample notebooks

## Set-up Instructions

The environment to run the following notebooks is provided as a Docker image and the following instructions require Docker to be already installed on your machine. The following commands need to be executed in a terminal and have been tested on Linux (Ubuntu).

1. Pull required Docker image:

```sh
docker image pull clausmichele/esa-snap:esa-snap-11-snappy-python-3.10_0.3
```

2. Start JupyterLab using the Docker image:

```sh
docker run -p 8889:8889 -ti esa-snap-11-snappy-python-3.10_0.3 jupyter lab --ip=0.0.0.0 --port 8889 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password=''
```

3. Open the following link in a browser:

http://localhost:8889/lab

4. Open a Terminal in JupyterLab and clone the repository via:

```sh
git clone https://github.com/cloudinsar/s1-workflows
```

## Run the sample notebook

Access the s1-workflows/notebooks folder in the left panel and then open the InSAR_workflow_input_selection.ipynb notebook.