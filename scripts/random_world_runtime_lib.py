import math
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from geometry_msgs.msg import Pose

from ament_index_python.packages import get_package_share_directory


SCRIPTS_DIR = os.path.join(get_package_share_directory('sobits_gazebo_worlds'), 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from generate_worlds import extract_random_object_specs_from_world, generate_random_object_specs, resolve_model_sdf


def quaternion_from_yaw(yaw):
    half_yaw = yaw * 0.5
    return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


def build_pose(x, y, z, yaw):
    pose = Pose()
    pose.position.x = float(x)
    pose.position.y = float(y)
    pose.position.z = float(z)
    qx, qy, qz, qw = quaternion_from_yaw(yaw)
    pose.orientation.x = qx
    pose.orientation.y = qy
    pose.orientation.z = qz
    pose.orientation.w = qw
    return pose


def resolve_model_sdf_path(models_root, model_uri):
    if not model_uri.startswith('model://'):
        raise RuntimeError(f'Unsupported model URI format: {model_uri}')

    relative_path = model_uri.removeprefix('model://')
    from generate_worlds import find_model_sdf

    model_dir = Path(models_root) / relative_path
    if model_dir.is_dir():
        return find_model_sdf(model_dir)

    model_dir = Path(models_root).parent / relative_path
    if model_dir.is_dir():
        return find_model_sdf(model_dir)

    return resolve_model_sdf(models_root, relative_path)


def build_spawn_sdf(model_uri, entity_name, models_root, is_static=True):
    model_sdf_path = resolve_model_sdf_path(models_root, model_uri)
    root = ET.fromstring(Path(model_sdf_path).read_text(encoding='utf-8'))
    model = root.find('model')
    if model is None:
        raise RuntimeError(f'No model tag was found in: {model_sdf_path}')

    model.set('name', entity_name)
    static_element = model.find('static')
    if static_element is None:
        static_element = ET.SubElement(model, 'static')
    static_element.text = 'true' if is_static else 'false'
    return ET.tostring(root, encoding='unicode')


def generate_layout_specs(base_world, placement_config, models_root, object_count, object_prefix, seed):
    return generate_random_object_specs(
        base_world,
        placement_config,
        models_root,
        object_count,
        object_prefix=object_prefix,
        seed=seed,
    )


def load_initial_layout_specs(initial_layout_world_path, object_prefix):
    if not initial_layout_world_path or not os.path.exists(initial_layout_world_path):
        return []
    return extract_random_object_specs_from_world(initial_layout_world_path, object_prefix=object_prefix)
