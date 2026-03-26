import math
import os
import random
import xml.etree.ElementTree as ET


HUMAN_RADIUS = 0.35
HUMAN_WALL_CLEARANCE = 0.25
HUMAN_HUMAN_CLEARANCE = 0.85
FLOOR_OBJECT_Z_THRESHOLD = 0.05
FLOOR_INCLUDE_NAMES = {'floor_plane', 'ground_plane'}
FRAME_NAME_SUFFIX = '_frame'
FLOOR_MODEL_URI = 'model://floor_plane'
FRAME_MODEL_URIS = {'model://rcjo2025_frame'}

MODEL_FOOTPRINT_OVERRIDES = {
    'sofa': [(0.0, 0.0, 0.95, 0.95, 0.0)],
    'bed': [(0.0, 0.0, 1.40, 2.10, 0.0)],
    'kachaka_shelf': [(0.0, 0.22, 0.46, 0.44, 0.0)],
}


def get_world_name(world_file_path):
    root = ET.fromstring(open(world_file_path).read())
    world = root.find('world')
    if world is None:
        raise RuntimeError(f'World tag was not found in: {world_file_path}')
    name = world.get('name')
    if not name:
        raise RuntimeError(f'World name attribute was not found in: {world_file_path}')
    return name


def parse_pose(pose_text):
    pose = [float(value) for value in pose_text.split()]
    while len(pose) < 6:
        pose.append(0.0)
    return pose


def load_world_includes(world_file_path):
    root = ET.fromstring(open(world_file_path).read())
    world = root.find('world')
    if world is None:
        raise RuntimeError(f'World tag was not found in: {world_file_path}')

    includes = []
    for include in world.findall('include'):
        name = include.findtext('name')
        uri = include.findtext('uri')
        pose = parse_pose(include.findtext('pose', default='0 0 0 0 0 0'))
        includes.append({'name': name, 'uri': uri, 'pose': pose})
    return includes


def find_floor_and_frame_includes(includes):
    floor_include = None
    frame_include = None

    for include in includes:
        name = include.get('name')
        uri = include.get('uri')

        if floor_include is None and name in FLOOR_INCLUDE_NAMES:
            floor_include = include
        if frame_include is None and name and name.endswith(FRAME_NAME_SUFFIX):
            frame_include = include

        if uri == FLOOR_MODEL_URI and floor_include is None:
            floor_include = include
        if uri in FRAME_MODEL_URIS and frame_include is None:
            frame_include = include

    if floor_include is None:
        raise RuntimeError(
            'Could not find floor include from the world file. '
            f'Expected one of names {sorted(FLOOR_INCLUDE_NAMES)} or uri {FLOOR_MODEL_URI}.'
        )
    if frame_include is None:
        raise RuntimeError(
            'Could not find frame include from the world file. '
            f'Expected a name ending with {FRAME_NAME_SUFFIX!r} or one of uris {sorted(FRAME_MODEL_URIS)}.'
        )

    return floor_include, frame_include


def find_model_sdf(model_dir):
    for candidate in ('model.sdf', 'model-1_4.sdf'):
        path = os.path.join(model_dir, candidate)
        if os.path.exists(path):
            return path

    for filename in sorted(os.listdir(model_dir)):
        if filename.startswith('model') and filename.endswith('.sdf'):
            return os.path.join(model_dir, filename)

    raise RuntimeError(f'No model.sdf was found under: {model_dir}')


def rect_half_extents(size_x, size_y, yaw):
    cos_yaw = abs(math.cos(yaw))
    sin_yaw = abs(math.sin(yaw))
    return (
        0.5 * (size_x * cos_yaw + size_y * sin_yaw),
        0.5 * (size_x * sin_yaw + size_y * cos_yaw),
    )


def transform_rect(center_x, center_y, size_x, size_y, local_yaw, world_pose):
    world_x, world_y, _z, _roll, _pitch, world_yaw = world_pose
    cos_yaw = math.cos(world_yaw)
    sin_yaw = math.sin(world_yaw)

    rotated_center_x = world_x + center_x * cos_yaw - center_y * sin_yaw
    rotated_center_y = world_y + center_x * sin_yaw + center_y * cos_yaw
    half_x, half_y = rect_half_extents(size_x, size_y, local_yaw + world_yaw)

    return (
        rotated_center_x - half_x,
        rotated_center_x + half_x,
        rotated_center_y - half_y,
        rotated_center_y + half_y,
    )


def model_collision_rects(models_root, model_uri):
    if not model_uri.startswith('model://'):
        return []

    model_name = model_uri.removeprefix('model://')
    override = MODEL_FOOTPRINT_OVERRIDES.get(model_name)
    if override is not None:
        return override

    model_dir = os.path.join(models_root, model_name)
    if not os.path.isdir(model_dir):
        return []

    model_root = ET.fromstring(open(find_model_sdf(model_dir)).read())
    rects = []
    for collision in model_root.findall('.//collision'):
        pose = parse_pose(collision.findtext('pose', default='0 0 0 0 0 0'))
        geometry = collision.find('geometry')
        if geometry is None:
            continue

        box = geometry.find('box')
        if box is not None:
            size = [float(value) for value in box.findtext('size').split()]
            rects.append((pose[0], pose[1], size[0], size[1], pose[5]))
            continue

        cylinder = geometry.find('cylinder')
        if cylinder is not None:
            radius = float(cylinder.findtext('radius'))
            rects.append((pose[0], pose[1], 2.0 * radius, 2.0 * radius, 0.0))

    return rects


def build_obstacles_and_bounds(world_file_path, models_root):
    includes = load_world_includes(world_file_path)
    floor_include, frame_include = find_floor_and_frame_includes(includes)
    obstacles = []
    floor_bounds = None

    for include in includes:
        if not include['name'] or not include['uri']:
            continue
        if include is floor_include:
            continue
        if include['pose'][2] > FLOOR_OBJECT_Z_THRESHOLD:
            continue

        rects = model_collision_rects(models_root, include['uri'])
        transformed = [transform_rect(*rect, include['pose']) for rect in rects]

        if include is frame_include and transformed:
            min_x = min(rect[0] for rect in transformed) + HUMAN_RADIUS + HUMAN_WALL_CLEARANCE
            max_x = max(rect[1] for rect in transformed) - HUMAN_RADIUS - HUMAN_WALL_CLEARANCE
            min_y = min(rect[2] for rect in transformed) + HUMAN_RADIUS + HUMAN_WALL_CLEARANCE
            max_y = max(rect[3] for rect in transformed) - HUMAN_RADIUS - HUMAN_WALL_CLEARANCE
            floor_bounds = (min_x, max_x, min_y, max_y)

        obstacles.extend(transformed)

    if floor_bounds is None:
        raise RuntimeError('Could not infer floor bounds from rcjo2025_frame.')

    return floor_bounds, obstacles


def point_collides(x, y, obstacles, radius):
    for min_x, max_x, min_y, max_y in obstacles:
        if (min_x - radius) <= x <= (max_x + radius) and (min_y - radius) <= y <= (max_y + radius):
            return True
    return False


def generate_human_spawn_poses(world_file_path, models_root, human_count, seed_text):
    if human_count <= 0:
        return []

    floor_bounds, obstacles = build_obstacles_and_bounds(world_file_path, models_root)
    rng = random.Random()
    if seed_text:
        rng.seed(f'human::{seed_text}')

    poses = []
    for _ in range(human_count):
        pose = None
        for _trial in range(2000):
            x = rng.uniform(floor_bounds[0], floor_bounds[1])
            y = rng.uniform(floor_bounds[2], floor_bounds[3])
            yaw = rng.uniform(-math.pi, math.pi)

            if point_collides(x, y, obstacles, HUMAN_RADIUS):
                continue
            if any(math.dist((x, y), (px, py)) < HUMAN_HUMAN_CLEARANCE for px, py, _pz, _pyaw in poses):
                continue

            pose = (x, y, 0.0, yaw)
            break

        if pose is None:
            raise RuntimeError('Could not find enough free floor positions for the requested humans.')
        poses.append(pose)

    return poses


def generate_human_spawn_poses_near_room(world_file_path, models_root, room_name, human_count, seed_text):
    if human_count <= 0:
        return []

    includes = load_world_includes(world_file_path)
    room_centers = []
    for include in includes:
        name = include.get('name') or ''
        if name.startswith(f'{room_name}#') and include['pose'][2] <= FLOOR_OBJECT_Z_THRESHOLD:
            room_centers.append((include['pose'][0], include['pose'][1]))

    if not room_centers:
        raise RuntimeError(f'Could not find floor-level furniture in room {room_name!r}.')

    center_x = sum(x for x, _ in room_centers) / len(room_centers)
    center_y = sum(y for _, y in room_centers) / len(room_centers)

    floor_bounds, obstacles = build_obstacles_and_bounds(world_file_path, models_root)
    rng = random.Random()
    if seed_text:
        rng.seed(f'human-room::{room_name}::{seed_text}')

    poses = []
    for _ in range(human_count):
        pose = None
        for _trial in range(2000):
            radius = rng.uniform(0.3, 1.8)
            angle = rng.uniform(-math.pi, math.pi)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            yaw = rng.uniform(-math.pi, math.pi)

            if not (floor_bounds[0] <= x <= floor_bounds[1] and floor_bounds[2] <= y <= floor_bounds[3]):
                continue
            if point_collides(x, y, obstacles, HUMAN_RADIUS):
                continue
            if any(math.dist((x, y), (px, py)) < HUMAN_HUMAN_CLEARANCE for px, py, _pz, _pyaw in poses):
                continue

            pose = (x, y, 0.0, yaw)
            break

        if pose is None:
            raise RuntimeError(f'Could not find enough free floor positions near room {room_name!r}.')
        poses.append(pose)

    return poses
