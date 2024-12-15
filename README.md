# Kubric-Pallets

This is a toolset for generation of synthetic data for 6DOF pose detection of warehouse pallets.
The data is generated using [Google Research's Kubric library](https://github.com/google-research/kubric) which uses Blender for rendering.

## Installation

In a project directory:

### Clone this repo

Make sure to use Git LFS to clone this repo as it contains large files.

`git lfs clone https://github.com/RunnersNum40/pallet-detection.git`

### Clone Kubric repo

`git clone https://github.com/google-research/kubric.git`

### Pull Kubric Docker image

`docker pull kubricdockerhub/kubruntu`

### Switch into project directory

`cd pallet-detection`

### Setup Kubric in Venv

`python -m venv .venv`
`source .venv/bin/activate`
`pip install -e ../kubric`

### Run Dataset Generation

Make sure docker is running and execute the following command:

```bash
docker run --rm --interactive \
           --user $(id -u):$(id -g) \
           --volume "$(pwd):/kubric" \
           kubricdockerhub/kubruntu \
          /usr/bin/python3 warehouse.py
```

### Run Improved Yolov5 Method

`cd model` and then run yolov5_improved.ipynb
