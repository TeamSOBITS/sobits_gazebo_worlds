#!/usr/bin/env python3

import argparse
import math
import os
import random
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


MARKER = "<!-- RANDOM_YCB_OBJECTS -->"

DEFAULT_OBJECT_PREFIX = "random_ycb"


YCB_CATEGORY_KEYWORDS = {
    "food": (
        "cheez-it",
        "cracker",
        "sugar",
        "pudding",
        "gelatin",
        "spam",
        "tuna",
        "tomato_soup",
        "mustard",
        "strawberry",
        "apple",
        "lemon",
        "peach",
        "pear",
        "orange",
        "plum",
        "banana",
    ),
    "kitchen_item": (
        "pitcher",
        "bleach",
        "windex",
        "bowl",
        "mug",
        "plate",
        "skillet",
        "fork",
        "spoon",
        "knife",
        "spatula",
    ),
}


def get_ycb_category(uri):
    if not uri.startswith("model://"):
        raise RuntimeError(f"Unsupported YCB URI format: {uri}")

    parts = uri.removeprefix("model://").split("/")
    if len(parts) >= 3 and parts[0] == "ycb":
        return parts[1]

    model_name = parts[0]
    if model_name.startswith("ycb_"):
        for category, keywords in YCB_CATEGORY_KEYWORDS.items():
            if any(keyword in model_name for keyword in keywords):
                return category
        return "other"

    if len(parts) < 3 or parts[0] != "ycb":
        raise RuntimeError(f"Unsupported YCB URI format: {uri}")

    return parts[1]


def discover_ycb_uris(models_root):
    models_root = Path(models_root)
    candidate_roots = [models_root]
    if not models_root.is_dir():
        for root in model_search_roots(models_root):
            if root.is_dir() and any(path.name.startswith("ycb_") for path in root.iterdir() if path.is_dir()):
                candidate_roots.append(root)

    uris = []
    checked_roots = []
    for candidate_root in candidate_roots:
        if not candidate_root.is_dir():
            checked_roots.append(candidate_root)
            continue

        checked_roots.append(candidate_root)
        item_dirs = sorted(candidate_root.glob("*/*"))
        if any(path.name.startswith("ycb_") for path in candidate_root.iterdir() if path.is_dir()):
            item_dirs.extend(sorted(candidate_root.glob("ycb_*")))

        for item_dir in item_dirs:
            if not item_dir.is_dir():
                continue

            has_model_definition = (item_dir / "model.config").exists() or any(item_dir.glob("model*.sdf"))
            if not has_model_definition:
                continue

            if item_dir.name.startswith("ycb_"):
                relative_path = item_dir.name
            else:
                relative_path = item_dir.relative_to(candidate_root.parent).as_posix()
            uris.append(f"model://{relative_path}")

    if not uris:
        checked = "\n  - ".join(str(path) for path in checked_roots)
        raise RuntimeError(f"No YCB models were discovered. Checked:\n  - {checked}")

    return sorted(set(uris))


def parse_base_world(base_world_path):
    root = ET.fromstring(Path(base_world_path).read_text())
    world = root.find("world")
    if world is None:
        raise RuntimeError(f"World tag was not found in: {base_world_path}")

    includes = {}
    for include in world.findall("include"):
        name = include.findtext("name")
        uri = include.findtext("uri")
        pose_text = include.findtext("pose", default="0 0 0 0 0 0")
        if not name or not uri:
            continue

        pose = [float(value) for value in pose_text.split()]
        while len(pose) < 6:
            pose.append(0.0)

        includes[name] = {
            "uri": uri,
            "pose": pose,
        }

    return includes


def find_model_sdf(model_dir):
    for candidate in ("model.sdf", "model-1_4.sdf"):
        path = model_dir / candidate
        if path.exists():
            return path

    matches = sorted(model_dir.glob("model*.sdf"))
    if matches:
        return matches[0]

    raise RuntimeError(f"No model.sdf was found under: {model_dir}")


def model_search_roots(base_world_path):
    roots = [Path(base_world_path).resolve().parent.parent / "models"]
    src_root = Path(__file__).resolve().parents[2]
    roots.append(src_root / "tmc_wrs_gz" / "tmc_wrs_gz_worlds" / "models")

    for value in (
        os.environ.get("GZ_SIM_RESOURCE_PATH", ""),
        os.environ.get("GAZEBO_MODEL_PATH", ""),
    ):
        for entry in value.split(os.pathsep):
            if entry and "$" not in entry:
                roots.append(Path(entry).expanduser())

    for package_name in ("tmc_wrs_gz_worlds",):
        try:
            roots.append(Path(get_package_share_directory(package_name)) / "models")
        except PackageNotFoundError:
            pass

    unique_roots = []
    seen = set()
    for root in roots:
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_roots.append(resolved)

    return unique_roots


def resolve_model_sdf(base_world_path, model_relative_path):
    checked_dirs = []
    for models_dir in model_search_roots(base_world_path):
        model_dir = models_dir / model_relative_path
        checked_dirs.append(model_dir)
        try:
            return find_model_sdf(model_dir)
        except RuntimeError:
            continue

    checked = "\n  - ".join(str(path) for path in checked_dirs)
    raise RuntimeError(f"No model.sdf was found for model://{model_relative_path}. Checked:\n  - {checked}")


def find_surface_element(link, surface_name):
    if surface_name:
        surface = link.find(f"./collision[@name='{surface_name}']")
        if surface is None:
            surface = link.find(f"./visual[@name='{surface_name}']")
        if surface is None:
            visual_name = f"{surface_name}_v"
            surface = link.find(f"./visual[@name='{visual_name}']")
        if surface is None:
            raise RuntimeError(f"Surface '{surface_name}' was not found in model.")
        return surface

    surface = link.find("./collision[@name='top']")
    if surface is None:
        surface = link.find("./visual[@name='top_v']")
    if surface is None:
        raise RuntimeError("No default top surface geometry was found in model.")
    return surface


def load_surface_geometry(base_world_path, area_name, surface_name=None):
    includes = parse_base_world(base_world_path)
    include = includes.get(area_name)
    if include is None:
        raise RuntimeError(f"Placement area '{area_name}' was not found in base world {base_world_path}")

    uri = include["uri"]
    if not uri.startswith("model://"):
        raise RuntimeError(f"Unsupported model URI for '{area_name}': {uri}")

    model_relative_path = uri.removeprefix("model://")
    model_sdf_path = resolve_model_sdf(base_world_path, model_relative_path)

    model_root = ET.fromstring(model_sdf_path.read_text())
    link = model_root.find(".//link")
    if link is None:
        raise RuntimeError(f"No link tag was found in: {model_sdf_path}")

    try:
        surface = find_surface_element(link, surface_name)
    except RuntimeError as exc:
        raise RuntimeError(f"{exc} File: {model_sdf_path}") from exc

    pose_text = surface.findtext("pose", default="0 0 0 0 0 0")
    surface_pose = [float(value) for value in pose_text.split()]
    while len(surface_pose) < 6:
        surface_pose.append(0.0)

    size_text = surface.findtext("./geometry/box/size")
    if size_text is None:
        raise RuntimeError(f"Surface '{surface_name or 'top'}' is not a box in: {model_sdf_path}")
    size = [float(value) for value in size_text.split()]

    world_pose = include["pose"]
    center = [world_pose[0], world_pose[1]]
    yaw = world_pose[5]
    z = world_pose[2] + surface_pose[2] + size[2] / 2.0

    return {
        "center": center,
        "size": size[:2],
        "yaw": yaw,
        "z": z,
    }


def load_placement_areas(config_path, base_world_path):
    raw = yaml.safe_load(Path(config_path).read_text()) or {}
    placement_areas = raw.get("placement_areas")

    if not placement_areas:
        raise RuntimeError(f"No placement_areas were found in: {config_path}")

    normalized = []
    for area in placement_areas:
        name = area["name"]
        surface_name = area.get("surface_name")
        area_key = area.get("area_key", f"{name}:{surface_name or 'top'}")
        min_distance = float(area.get("min_object_spacing", area.get("min_distance", 0.13)))
        inferred = load_surface_geometry(base_world_path, name, surface_name)
        z = float(area.get("z", inferred["z"]))

        if "x_range" in area and "y_range" in area:
            x_range = tuple(area["x_range"])
            y_range = tuple(area["y_range"])
        else:
            geometry_area = {
                "name": name,
                "center": area.get("center", inferred["center"]),
                "size": area.get("size", inferred["size"]),
                "yaw": area.get("yaw", inferred["yaw"]),
                "edge_margin": area.get("edge_margin", area.get("margin", 0.0)),
            }
            x_range, y_range = compute_ranges_from_geometry(geometry_area)

        normalized.append(
            {
                "area_key": area_key,
                "name": name,
                "x_range": x_range,
                "y_range": y_range,
                "z": z,
                "min_distance": min_distance,
                "allowed_categories": area.get("allowed_categories", area.get("object_categories")),
                "selection_weight": float(area.get("selection_weight", 1.0)),
                "max_objects": area.get("max_objects"),
            }
        )

    return normalized


def compute_ranges_from_geometry(area):
    center_x, center_y = area["center"]
    size_x, size_y = area["size"]
    yaw = float(area.get("yaw", 0.0))
    edge_margin = float(area.get("edge_margin", area.get("margin", 0.0)))

    usable_size_x = size_x - 2.0 * edge_margin
    usable_size_y = size_y - 2.0 * edge_margin
    if usable_size_x <= 0.0 or usable_size_y <= 0.0:
        raise RuntimeError(
            f"Placement area '{area['name']}' has an invalid edge_margin {edge_margin} for size {area['size']}."
        )

    cos_yaw = abs(math.cos(yaw))
    sin_yaw = abs(math.sin(yaw))

    half_extent_x = 0.5 * (usable_size_x * cos_yaw + usable_size_y * sin_yaw)
    half_extent_y = 0.5 * (usable_size_x * sin_yaw + usable_size_y * cos_yaw)

    x_range = (center_x - half_extent_x, center_x + half_extent_x)
    y_range = (center_y - half_extent_y, center_y + half_extent_y)
    return x_range, y_range


def sample_pose(area, existing_poses):
    return sample_pose_with_rng(area, existing_poses, random)


def sample_pose_with_rng(area, existing_poses, rng):
    for _ in range(200):
        x = rng.uniform(*area["x_range"])
        y = rng.uniform(*area["y_range"])
        yaw = rng.uniform(-math.pi, math.pi)

        if all(math.dist((x, y), (px, py)) >= area["min_distance"] for px, py, _pz in existing_poses):
            return x, y, area["z"], yaw

    raise RuntimeError(f"Could not place another object on {area['name']}. Reduce --object-count.")


def build_random_includes(object_count, placement_areas, ycb_uris, object_prefix):
    specs = generate_random_object_specs_from_data(
        object_count,
        placement_areas,
        ycb_uris,
        object_prefix,
    )
    return render_random_includes(specs)


def render_random_includes(object_specs):
    if not object_specs:
        return MARKER

    blocks = []
    for spec in object_specs:
        x, y, z, yaw = spec["pose"]
        blocks.append(
            "\n".join(
                [
                    "    <include>",
                    f"      <name>{spec['name']}</name>",
                    f"      <uri>{spec['uri']}</uri>",
                    f"      <static>{1 if spec.get('static', True) else 0}</static>",
                    f"      <pose relative_to=''>{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw:.3f}</pose>",
                    "    </include>",
                ]
            )
        )

    return "\n\n".join(blocks)


def generate_random_object_specs_from_data(
    object_count,
    placement_areas,
    ycb_uris,
    object_prefix=DEFAULT_OBJECT_PREFIX,
    rng=None,
):
    if object_count < 0:
        raise ValueError("--object-count must be >= 0")

    if object_count == 0:
        return []

    available_categories = sorted({get_ycb_category(uri) for uri in ycb_uris})
    rng = rng or random

    placements = {area["area_key"]: [] for area in placement_areas}
    specs = []

    for index in range(1, object_count + 1):
        selectable_areas = []
        selectable_weights = []
        for area in placement_areas:
            max_objects = area.get("max_objects")
            if max_objects is not None and len(placements[area["area_key"]]) >= int(max_objects):
                continue
            selectable_areas.append(area)
            selectable_weights.append(area.get("selection_weight", 1.0))

        if not selectable_areas:
            raise RuntimeError("No placement areas are available anymore. Increase max_objects or reduce object_count.")

        area = rng.choices(selectable_areas, weights=selectable_weights, k=1)[0]
        allowed_categories = area.get("allowed_categories")
        if allowed_categories:
            allowed_categories = set(allowed_categories)
            eligible_uris = [uri for uri in ycb_uris if get_ycb_category(uri) in allowed_categories]
            if not eligible_uris:
                raise RuntimeError(
                    f"Placement area '{area['area_key']}' requested categories {sorted(allowed_categories)}, "
                    f"but available categories are {available_categories}."
                )
        else:
            eligible_uris = ycb_uris

        uri = rng.choice(eligible_uris)
        x, y, z, yaw = sample_pose_with_rng(area, placements[area["area_key"]], rng)
        placements[area["area_key"]].append((x, y, z))

        specs.append(
            {
                "name": f"{object_prefix}_{index:02d}",
                "uri": uri,
                "pose": (x, y, z, yaw),
                "static": True,
                "area_key": area["area_key"],
                "placement_name": area["name"],
            }
        )

    return specs


def generate_random_object_specs(
    base_world_path,
    placement_config,
    models_root,
    object_count,
    object_prefix=DEFAULT_OBJECT_PREFIX,
    seed=None,
):
    rng = random.Random(seed) if seed is not None else random.Random()
    placement_areas = load_placement_areas(placement_config, base_world_path)
    ycb_uris = discover_ycb_uris(models_root)
    return generate_random_object_specs_from_data(
        object_count,
        placement_areas,
        ycb_uris,
        object_prefix=object_prefix,
        rng=rng,
    )


def extract_random_object_specs_from_world(world_path, object_prefix=DEFAULT_OBJECT_PREFIX):
    root = ET.fromstring(Path(world_path).read_text(encoding="utf-8"))
    world = root.find("world")
    if world is None:
        raise RuntimeError(f"World tag was not found in: {world_path}")

    specs = []
    prefix = f"{object_prefix}_"
    for include in world.findall("include"):
        name = include.findtext("name")
        if not name or not name.startswith(prefix):
            continue

        uri = include.findtext("uri")
        pose_text = include.findtext("pose", default="0 0 0 0 0 0")
        pose = [float(value) for value in pose_text.split()]
        while len(pose) < 6:
            pose.append(0.0)

        specs.append(
            {
                "name": name,
                "uri": uri,
                "pose": (pose[0], pose[1], pose[2], pose[5]),
                "static": include.findtext("static", default="1").strip() != "0",
            }
        )

    specs.sort(key=lambda spec: spec["name"])
    return specs


def main():
    parser = argparse.ArgumentParser(description="Generate Gazebo worlds with randomized YCB objects.")
    parser.add_argument("--base-world", required=True, help="Path to the base world template.")
    parser.add_argument("--placement-config", required=True, help="Path to the YAML placement config.")
    parser.add_argument("--models-root", required=True, help="Path to the models/ycb directory.")
    parser.add_argument("--output", required=True, help="Path to the generated world file.")
    parser.add_argument("--seed", type=int, default=None, help="Seed for deterministic placement.")
    parser.add_argument("--object-count", type=int, default=6, help="Number of YCB objects to place.")
    parser.add_argument("--object-prefix", default=DEFAULT_OBJECT_PREFIX, help="Prefix for generated object names.")
    args = parser.parse_args()

    base_world = Path(args.base_world).read_text()
    random_object_specs = generate_random_object_specs(
        args.base_world,
        args.placement_config,
        args.models_root,
        args.object_count,
        object_prefix=args.object_prefix,
        seed=args.seed,
    )
    random_objects_xml = render_random_includes(random_object_specs)

    if MARKER not in base_world:
        raise RuntimeError(f"Marker {MARKER!r} was not found in {args.base_world}")

    generated_world = base_world.replace(MARKER, random_objects_xml)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated_world)


if __name__ == "__main__":
    main()
