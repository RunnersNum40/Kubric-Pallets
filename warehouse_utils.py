import os
import logging
import re
from kubric.safeimport.bpy import bpy


def discover_assets(base_path, extensions=(".obj", ".glb", ".fbx")):
    """
    Recursively discovers asset files in the specified directory.
    """
    if not os.path.exists(base_path):
        logging.warning(f"Asset path does not exist: {base_path}")
        return []

    asset_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith(extensions):
                asset_files.append(os.path.join(root, file))

    return asset_files


def discover_textures(base_path):
    """
    Discovers texture sets in the specified directory and groups them into dictionaries.
    """
    if not os.path.exists(base_path):
        logging.warning(f"Texture path does not exist: {base_path}")
        return []

    texture_files = [
        os.path.join(root, file)
        for root, _, files in os.walk(base_path)
        for file in files
        if file.lower().endswith((".jpg", ".png"))
    ]

    if not texture_files:
        logging.warning(f"No textures found in {base_path}")
        return []

    patterns = {
        "color": re.compile(r"(color|albedo)", re.IGNORECASE),
        "normal": re.compile(r"(normal)", re.IGNORECASE),
        "roughness": re.compile(r"(roughness)", re.IGNORECASE),
    }

    grouped_textures = {}
    for file in texture_files:
        for key, pattern in patterns.items():
            if pattern.search(file):
                base_name = os.path.basename(file).split("_")[0]
                if base_name not in grouped_textures:
                    grouped_textures[base_name] = {}
                grouped_textures[base_name][key] = file

    texture_sets = [
        {
            "color": textures.get("color"),
            "normal": textures.get("normal"),
            "roughness": textures.get("roughness"),
        }
        for textures in grouped_textures.values()
    ]

    return texture_sets


def apply_texture(asset, texture_set, scale):
    """
    Applies textures to a material using Blender nodes with adjustable texture scale.
    """
    material = bpy.data.materials.new(name=f"{asset.name}_material")

    if not material.use_nodes:
        material.use_nodes = True

    node_tree = material.node_tree
    nodes = node_tree.nodes
    links = node_tree.links

    for node in nodes:
        nodes.remove(node)

    principled_node = nodes.new("ShaderNodeBsdfPrincipled")
    principled_node.location = (0, 0)

    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (400, 0)
    links.new(principled_node.outputs["BSDF"], output_node.inputs["Surface"])

    tex_coord_node = nodes.new("ShaderNodeTexCoord")
    tex_coord_node.location = (-800, 0)

    mapping_node = nodes.new("ShaderNodeMapping")
    mapping_node.location = (-600, 0)
    links.new(tex_coord_node.outputs["UV"], mapping_node.inputs["Vector"])

    if isinstance(scale, (tuple, list)) and len(scale) == 3:
        mapping_node.inputs["Scale"].default_value = scale
    else:
        mapping_node.inputs["Scale"].default_value = (scale, scale, scale)

    def add_texture_node(texture_path, input_name, location, use_color_space=True):
        if not texture_path:
            return
        texture_node = nodes.new("ShaderNodeTexImage")
        texture_node.location = location
        texture_node.image = bpy.data.images.load(texture_path)
        texture_node.image.colorspace_settings.name = (
            "sRGB" if use_color_space else "Non-Color"
        )
        links.new(mapping_node.outputs["Vector"], texture_node.inputs["Vector"])
        links.new(texture_node.outputs["Color"], principled_node.inputs[input_name])

    add_texture_node(
        texture_set.get("color"), "Base Color", (-400, 0), use_color_space=True
    )
    add_texture_node(
        texture_set.get("normal"), "Normal", (-400, -200), use_color_space=False
    )
    add_texture_node(
        texture_set.get("roughness"), "Roughness", (-400, -400), use_color_space=False
    )

    for obj in bpy.data.objects:
        if obj.name.startswith(asset.name):
            if not obj.data.materials:
                obj.data.materials.append(material)
            else:
                obj.data.materials[0] = material
