import os
import json
import h5py
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def create_transformation_matrix(position, euler_angles):
    """
    Creates a 4x4 homogeneous transformation matrix from position and Euler angles.
    """
    r = Rotation.from_euler("xyz", euler_angles, degrees=True)
    rotation_matrix = r.as_matrix()
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation_matrix
    transformation_matrix[:3, 3] = position
    return transformation_matrix


def read_image(image_path):
    """
    Reads an image from a file and converts it to a numpy array.
    """
    img = Image.open(image_path)
    return np.array(img)


def process_scene(scene_path, hdf5_group):
    """
    Processes a single scene and stores its metadata, objects, and camera data into an HDF5 group.
    """
    logging.info(f"Processing scene: {scene_path}")

    with open(os.path.join(scene_path, "metadata.json"), "r") as f:
        scene_metadata = json.load(f)

    hdf5_group.attrs["scene_index"] = scene_metadata["scene_index"]
    hdf5_group.attrs["warehouse_dimensions"] = tuple(
        scene_metadata["warehouse_dimensions"].values()
    )
    hdf5_group.attrs["ambient_light"] = tuple(
        scene_metadata["lighting_conditions"]["ambient_color"]
    )
    hdf5_group.attrs["num_lights"] = scene_metadata["lighting_conditions"]["num_lights"]

    objects_group = hdf5_group.create_group("objects")
    for obj_index, obj in enumerate(scene_metadata["objects"]):
        obj_key = f"object_{obj_index}"
        obj_group = objects_group.create_group(obj_key)

        transformation_matrix = create_transformation_matrix(
            obj["position"], obj["rotation"]
        )
        obj_group.create_dataset("transformation_matrix", data=transformation_matrix)

        obj_group.attrs["name"] = obj["name"]
        obj_group.attrs["position"] = obj["position"]
        obj_group.attrs["scale"] = obj["scale"]
        obj_group.attrs["rotation"] = obj["rotation"]

    cameras_group = hdf5_group.create_group("cameras")
    camera_dirs = [d for d in os.listdir(scene_path) if d.startswith("cam_")]

    for cam_dir in camera_dirs:
        camera_path = os.path.join(scene_path, cam_dir, "metadata.json")
        if not os.path.exists(camera_path):
            continue

        with open(camera_path, "r") as f:
            camera_metadata = json.load(f)

        cam_key = f"camera_{camera_metadata['camera_index']}"
        cam_group = cameras_group.create_group(cam_key)

        transformation_matrix = create_transformation_matrix(
            camera_metadata["relative_position_xyz"],
            camera_metadata["relative_orientation_xyz"],
        )
        cam_group.create_dataset("transformation_matrix", data=transformation_matrix)

        cam_group.attrs["position"] = camera_metadata["position"]
        cam_group.attrs["relative_position"] = camera_metadata["relative_position_xyz"]
        cam_group.attrs["relative_orientation"] = camera_metadata[
            "relative_orientation_xyz"
        ]
        cam_group.attrs["focal_length"] = camera_metadata["focal_length"]

        rgba_path = os.path.join(scene_path, cam_dir, camera_metadata["rgba_path"])
        depth_path = os.path.join(scene_path, cam_dir, camera_metadata["depth_path"])

        if os.path.exists(rgba_path):
            rgba_image = read_image(rgba_path)
            cam_group.create_dataset("rgba_image", data=rgba_image, compression="gzip")

        if os.path.exists(depth_path):
            depth_image = read_image(depth_path)
            cam_group.create_dataset(
                "depth_image", data=depth_image, compression="gzip"
            )


def convert_to_hdf5(data_root, output_path):
    """
    Converts a directory of scenes and cameras into a single HDF5 file.
    """
    logging.info(
        f"Starting conversion to HDF5. Data root: {data_root}, Output path: {output_path}"
    )
    with h5py.File(output_path, "w") as hdf5_file:
        scene_dirs = [d for d in os.listdir(data_root) if d.startswith("scene_")]
        for scene_dir in scene_dirs:
            scene_path = os.path.join(data_root, scene_dir)
            scene_group = hdf5_file.create_group(scene_dir)
            process_scene(scene_path, scene_group)

    logging.info(f"HDF5 file created at {output_path}")


# Paths
data_root = "output"  # Replace with the path to your data
output_path = "dataset.h5"

# Convert the dataset to HDF5 format
convert_to_hdf5(data_root, output_path)
