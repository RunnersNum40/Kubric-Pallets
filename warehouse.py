import json
import logging
import math
import os
import random
from concurrent.futures import ProcessPoolExecutor

from scipy.spatial.transform import Rotation

import kubric as kb
from kubric.renderer.blender import Blender as KubricRenderer
from warehouse_utils import (
    apply_texture,
    discover_assets,
    discover_textures,
)

logging.basicConfig(level=logging.DEBUG)

# Constants
ASSET_BASE_PATH = "assets"
OUTPUT_DIR = "output"
CAMERA_FOCUS_POINT = (0, 0, 0.5)
CAMERA_FOCAL_LENGTH_GAUSSIAN = (5, 2)  # Mean and std dev for random focal lengths
TEXTURE_SCALE_RANGE = (0.5, 1.5)
RANGES = {
    "pallet": (1, 5),
    "rack": (10, 30),
    "forklift": (5, 10),
}

# Discover assets and textures
ASSET_CATEGORIES = {
    "pallet": discover_assets(os.path.join(ASSET_BASE_PATH, "pallet")),
    "rack": discover_assets(os.path.join(ASSET_BASE_PATH, "rack")),
    "forklift": discover_assets(os.path.join(ASSET_BASE_PATH, "forklift")),
}
TEXTURE_CATEGORIES = {
    "wood": discover_textures(os.path.join(ASSET_BASE_PATH, "wood")),
    "metal": discover_textures(os.path.join(ASSET_BASE_PATH, "metal")),
    "plastic": discover_textures(os.path.join(ASSET_BASE_PATH, "plastic")),
    "floor": discover_textures(os.path.join(ASSET_BASE_PATH, "floor")),
}


def setup_building(scene):
    """Adds the floor, ceiling, and walls of the warehouse."""
    warehouse_length = random.uniform(30, 100)
    warehouse_width = random.uniform(20, 70)
    warehouse_height = random.uniform(8, 20)

    valid_texture_categories = (
        TEXTURE_CATEGORIES["floor"]
        + TEXTURE_CATEGORIES["wood"]
        + TEXTURE_CATEGORIES["metal"]
        + TEXTURE_CATEGORIES["plastic"]
    )

    floor = kb.Cube(
        name="floor",
        scale=(warehouse_length, warehouse_width, 0.1),
        position=(0, 0, -0.1),
    )
    scene += floor
    apply_texture(
        floor,
        random.choice(valid_texture_categories),
        scale=random.uniform(100, 300),
    )

    # ceiling = kb.Cube(
    #     name="ceiling",
    #     scale=(warehouse_length, warehouse_width, 0.1),
    #     position=(0, 0, warehouse_height),
    # )
    # scene += ceiling
    # apply_texture(
    #     ceiling,
    #     random.choice(valid_texture_categories),
    #     scale=random.uniform(100, 300),
    # )

    wall_thickness = 0.2
    walls = [
        kb.Cube(
            name="front_wall",
            scale=(warehouse_length, wall_thickness, warehouse_height),
            position=(0, -warehouse_width / 2, warehouse_height / 2),
        ),
        kb.Cube(
            name="back_wall",
            scale=(warehouse_length, wall_thickness, warehouse_height),
            position=(0, warehouse_width / 2, warehouse_height / 2),
        ),
        kb.Cube(
            name="left_wall",
            scale=(wall_thickness, warehouse_width, warehouse_height),
            position=(-warehouse_length / 2, 0, warehouse_height / 2),
        ),
        kb.Cube(
            name="right_wall",
            scale=(wall_thickness, warehouse_width, warehouse_height),
            position=(warehouse_length / 2, 0, warehouse_height / 2),
        ),
    ]
    for wall in walls:
        scene += wall
        apply_texture(
            wall,
            random.choice(valid_texture_categories),
            scale=random.uniform(50, 150),
        )

    return {
        "length": warehouse_length,
        "width": warehouse_width,
        "height": warehouse_height,
    }


def add_random_lighting(scene, num_lights, warehouse_dims):
    """Adds random lights to the warehouse."""
    warehouse_length = warehouse_dims["length"]
    warehouse_width = warehouse_dims["width"]
    warehouse_height = warehouse_dims["height"]

    scene.ambient_illumination = kb.Color(
        random.uniform(0.5, 1), random.uniform(0.5, 1), random.uniform(0.5, 1)
    )

    for i in range(num_lights):
        light_position = (
            random.uniform(-warehouse_length / 2, warehouse_length / 2),
            random.uniform(-warehouse_width / 2, warehouse_width / 2),
            random.uniform(warehouse_height * 0.8, warehouse_height * 0.95),
        )
        color = (
            random.uniform(0.5, 1),
            random.uniform(0.5, 1),
            random.uniform(0.5, 1),
        )
        intensity = random.uniform(1, 10)
        if i == 0:
            light = kb.DirectionalLight(
                position=light_position,
                look_at=(0, 0, 0),
                intensity=intensity,
                color=color,
            )
        else:
            light = kb.PointLight(
                position=light_position,
                intensity=intensity,
                color=color,
            )
        scene += light


def add_random_objects(scene, category, num_objects, texture_list):
    """Adds a random number of objects from a specified category."""
    for _ in range(num_objects):
        asset_path = random.choice(ASSET_CATEGORIES[category])
        scale = random.uniform(0.8, 1.2)
        position = (
            random.uniform(-10, 10),
            random.uniform(-10, 10),
            0,
        )
        base_rotation = kb.Quaternion(axis=[1, 0, 0], angle=math.pi / 2)
        jiggle_x = kb.Quaternion(axis=[1, 0, 0], angle=random.uniform(-0.05, 0.05))
        jiggle_y = kb.Quaternion(axis=[0, 1, 0], angle=random.uniform(-0.05, 0.05))
        jiggle_z = kb.Quaternion(axis=[0, 0, 1], angle=random.uniform(-0.05, 0.05))
        rotation = base_rotation * jiggle_x * jiggle_y * jiggle_z

        obj = kb.FileBasedObject(
            name=os.path.basename(asset_path),
            simulation_filename=asset_path,
            render_filename=asset_path,
            scale=(scale, scale, scale),
            position=position,
            quaternion=rotation,
        )
        scene += obj
        apply_texture(
            obj, random.choice(texture_list), scale=random.uniform(*TEXTURE_SCALE_RANGE)
        )


def place_pallet(scene, dims):
    """Places a target pallet in the scene."""
    asset_path = random.choice(ASSET_CATEGORIES["pallet"])
    scale = random.uniform(0.9, 1.1)
    position = (
        random.uniform(-dims["length"], dims["length"]) / 2,
        random.uniform(-dims["width"], dims["width"]) / 2,
        random.uniform(0, 1),
    )

    base_rotation = kb.Quaternion(axis=[1, 0, 0], angle=math.pi / 2)
    jiggle_x = kb.Quaternion(axis=[1, 0, 0], angle=random.uniform(-0.05, 0.05))
    jiggle_y = kb.Quaternion(axis=[0, 1, 0], angle=random.uniform(-0.05, 0.05))
    jiggle_z = kb.Quaternion(axis=[0, 0, 1], angle=random.uniform(-0.05, 0.05))
    rotation = base_rotation * jiggle_x * jiggle_y * jiggle_z

    obj = kb.FileBasedObject(
        name=f"target_{os.path.basename(asset_path)}",
        simulation_filename=asset_path,
        render_filename=asset_path,
        scale=(scale, scale, scale),
        position=position,
        quaternion=rotation,
    )
    scene += obj
    apply_texture(
        obj,
        random.choice(TEXTURE_CATEGORIES["wood"]),
        scale=random.uniform(*TEXTURE_SCALE_RANGE),
    )
    return obj


def setup_cameras(target_position, num_angles, distances):
    """Places cameras around the target at specified angles and distances."""
    cameras = []
    for angle in ((360 / num_angles) * i for i in range(num_angles)):
        for distance in distances:
            x = target_position[0] + distance * math.cos(math.radians(angle))
            y = target_position[1] + distance * math.sin(math.radians(angle))
            z = max(target_position[2] + random.uniform(-0.2, 0.2), 0.1)
            camera = kb.PerspectiveCamera(
                position=(x, y, z),
                look_at=target_position,
                focal_length=random.gauss(*CAMERA_FOCAL_LENGTH_GAUSSIAN),
                min_render_distance=0.1,
                max_render_distance=100.0,
            )
            cameras.append(camera)
    return cameras


def map_float(iter):
    return map(float, iter)


def save_render_data(output_dir, scene_index, camera_index, camera, pallet, renderer):
    """Saves the rendered data and metadata for each camera in the scene."""
    frame = renderer.render_still()

    scene_dir = os.path.join(output_dir, f"scene_{scene_index}")
    camera_dir = os.path.join(scene_dir, f"cam_{camera_index}")
    os.makedirs(camera_dir, exist_ok=True)

    rgba_path = os.path.join(camera_dir, "rgba.png")
    kb.write_png(frame["rgba"], rgba_path)

    depth_path = os.path.join(camera_dir, "depth.tiff")
    kb.write_tiff(frame["depth"], depth_path)

    depth_png_path = os.path.join(camera_dir, "depth_normalized.png")
    kb.write_scaled_png(frame["depth"].clip(0, 100), depth_png_path)

    segmentation_path = os.path.join(camera_dir, "segmentation.png")
    kb.write_palette_png(frame["segmentation"], segmentation_path)

    relative_position = tuple(
        float(p - c) for p, c in zip(pallet.position, camera.position)
    )
    relative_orientation = Rotation.from_quat(
        camera.quaternion
    ).inv() * Rotation.from_quat(pallet.quaternion)

    camera_metadata = {
        "camera_index": camera_index,
        "position": list(map(float, camera.position)),
        "relative_position_xyz": relative_position,
        "relative_orientation_xyz": relative_orientation.as_euler(
            "xyz", degrees=True
        ).tolist(),
        "focal_length": camera.focal_length,
        "rgba_path": os.path.relpath(rgba_path, output_dir),
        "depth_path": os.path.relpath(depth_path, output_dir),
    }

    with open(os.path.join(camera_dir, "metadata.json"), "w") as f:
        json.dump(camera_metadata, f, indent=4)


def generate_scene(output_dir, scene_index, num_angles, distances):
    """Generates a single warehouse scene."""
    logging.info(f"Generating scene {scene_index}")
    scene = kb.Scene(resolution=(1280, 720), frame_start=0, frame_end=1)
    renderer = KubricRenderer(scene)

    dims = setup_building(scene)
    add_random_lighting(scene, num_lights=random.randint(5, 10), warehouse_dims=dims)

    add_random_objects(
        scene,
        "rack",
        random.randint(*RANGES["rack"]),
        TEXTURE_CATEGORIES["metal"] + TEXTURE_CATEGORIES["plastic"],
    )
    add_random_objects(
        scene,
        "forklift",
        random.randint(*RANGES["forklift"]),
        TEXTURE_CATEGORIES["plastic"] + TEXTURE_CATEGORIES["metal"],
    )
    add_random_objects(
        scene,
        "pallet",
        random.randint(*RANGES["pallet"]),
        TEXTURE_CATEGORIES["wood"],
    )

    target_pallet = place_pallet(scene, dims)

    scene_dir = os.path.join(output_dir, f"scene_{scene_index}")
    os.makedirs(scene_dir, exist_ok=True)

    scene_metadata = {
        "scene_index": scene_index,
        "warehouse_dimensions": dims,
        "lighting_conditions": {
            "ambient_color": list(map(float, scene.ambient_illumination)),
            "num_lights": len([o for o in scene.assets if isinstance(o, kb.Light)]),
        },
        "objects": [
            {
                "name": obj.name,
                "position": list(map(float, obj.position)),
                "scale": list(map(float, obj.scale)),
                "rotation": list(Rotation.from_quat(obj.quaternion).as_euler("xyz")),
            }
            for obj in scene.assets
            if isinstance(obj, kb.PhysicalObject)
        ],
    }
    with open(os.path.join(scene_dir, "metadata.json"), "w") as f:
        json.dump(scene_metadata, f, indent=4)

    cameras = setup_cameras(target_pallet.position, num_angles, distances)
    for camera_index, camera in enumerate(cameras):
        scene.camera = camera
        save_render_data(
            output_dir, scene_index, camera_index, camera, target_pallet, renderer
        )


def generate_warehouse_scenes(
    output_dir, num_scenes, num_angles, distances, num_workers=4
):
    """Parallelized scene generation."""
    os.makedirs(output_dir, exist_ok=True)
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        tasks = [
            executor.submit(
                generate_scene,
                output_dir,
                scene_index,
                num_angles,
                distances,
            )
            for scene_index in range(num_scenes)
        ]
        for future in tasks:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error generating a scene: {e}")


generate_warehouse_scenes(
    OUTPUT_DIR,
    num_scenes=1024,
    num_angles=8,
    distances=[0.8, 1.0, 1.2, 1.5],
    num_workers=8,
)
