#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from sobits_interfaces.action import ChatLlmRecognition


SCRIPTS_DIR = os.path.dirname(__file__)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from generate_worlds import discover_ycb_uris, load_placement_areas, sample_pose
from human_spawn_utils import generate_human_spawn_poses_near_room, load_world_includes


PERSON_INTERACTION_KEYWORDS = (
    'ask',
    'answer',
    'follow',
    'find',
    'greet',
    'guide',
    'introduce',
    'lead',
    'meet',
    'person',
    'man',
    'woman',
    'someone',
    'name',
)
FOLLOW_TASK_KEYWORDS = (
    'follow',
)


def normalize_name(text):
    # Normalize by lowercasing and replacing spaces and hyphens with underscores
    return text.lower().translate(str.maketrans({'-': '_', ' ': '_'}))


def strip_json_fence(text):
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    return text


def build_object_aliases(ycb_uris):
    aliases = {}
    for uri in ycb_uris:
        parts = uri.removeprefix('model://').split('/')
        item = parts[-1]
        aliases[normalize_name(item)] = uri
        aliases[normalize_name(item.replace('_', ' '))] = uri
    return aliases


def build_room_names(placement_areas, world_path=None):
    room_names = []

    for area in placement_areas:
        if '#' in area['name']:
            room_name = area['name'].split('#', 1)[0]
            if room_name not in room_names:
                room_names.append(room_name)

    if world_path:
        for include in load_world_includes(world_path):
            name = include.get('name') or ''
            if '#' not in name:
                continue
            room_name = name.split('#', 1)[0]
            if room_name not in room_names:
                room_names.append(room_name)

    return room_names


def build_prompt(task_command, placement_areas, object_aliases, base_world_path):
    valid_locations = sorted({area['name'] for area in placement_areas})
    valid_rooms = build_room_names(placement_areas, base_world_path)
    valid_objects = sorted(set(object_aliases.keys()))

    return f"""
You are a planner for a Gazebo world generator used in RoboCup GPSR.
Extract only the entities that must exist at the beginning of the task.

Task command:
{task_command}

Valid object spawn locations:
{json.dumps(valid_locations, ensure_ascii=False)}

Valid human rooms:
{json.dumps(valid_rooms, ensure_ascii=False)}

Valid spawnable object names:
{json.dumps(valid_objects, ensure_ascii=False)}

Rules:
- Return JSON only. No markdown.
- Use only valid names from the lists above.
- For manipulation tasks, spawn the source object that must already exist at the beginning.
- Do not spawn destination objects or destination furniture.
- For any task involving talking to, guiding, finding, following, greeting, or asking a named person or any person in a room, add a human spawn in that room.
- If the command mentions a person name together with a room, you must add one human spawn for that room even if the command does not explicitly say "person".
- If no extra spawn is needed, return empty arrays.

Examples:
- "Guide Alex in the bedroom to the exit." -> {{"object_spawns": [], "human_spawns": [{{"target_room": "bedroom", "count": 1}}]}}
- "Ask the name of the person in the living room." -> {{"object_spawns": [], "human_spawns": [{{"target_room": "living_room", "count": 1}}]}}
- "Grasp an apple on the tall table in the living room and pass it to the person in the study room." -> {{"object_spawns": [{{"object_name": "apple", "target_location": "living_room#tall_table"}}], "human_spawns": [{{"target_room": "study_room", "count": 1}}]}}

Return this exact schema:
{{
  "object_spawns": [
    {{
      "object_name": "apple",
      "target_location": "living_room#tall_table"
    }}
  ],
  "human_spawns": [
    {{
      "target_room": "living_room",
      "count": 1
    }}
  ]
}}
""".strip()


class GroqPlannerClient(Node):
    def __init__(self):
        super().__init__('gpsr_world_spawn_planner')
        self.client = ActionClient(self, ChatLlmRecognition, 'groq_action')

    def plan(self, prompt, model_name):
        if not self.client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError('groq_action server is not available. Launch groq_ros first.')

        goal = ChatLlmRecognition.Goal()
        goal.room_name = 'gpsr_world_spawn_planner'
        goal.request = prompt
        goal.model_name = model_name
        goal.is_stack = False

        send_future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError('groq_action goal was not accepted.')

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()
        if result is None:
            raise RuntimeError('Failed to get result from groq_action.')
        return result.result.result


def request_spawn_plan(task_command, placement_areas, ycb_uris, model_name, base_world_path):
    prompt = build_prompt(task_command, placement_areas, build_object_aliases(ycb_uris), base_world_path)

    rclpy.init()
    node = GroqPlannerClient()
    try:
        response_text = node.plan(prompt, model_name)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    stripped_response = strip_json_fence(response_text)
    try:
        payload = json.loads(stripped_response)
    except json.JSONDecodeError as exc:
        response_preview = stripped_response[:500]
        if len(stripped_response) > 500:
            response_preview += '...'
        raise RuntimeError(
            f'Failed to parse JSON response from model "{model_name}". '
            f'Cleaned response preview: {response_preview!r}'
        ) from exc
    payload.setdefault('object_spawns', [])
    payload.setdefault('human_spawns', [])
    return payload


def infer_human_spawns_from_command(task_command, placement_areas, world_path):
    lowered = task_command.lower()
    valid_rooms = build_room_names(placement_areas, world_path)
    mentioned_rooms = []
    for room in valid_rooms:
        room_patterns = {room.lower(), room.lower().replace('_', ' ')}
        if any(pattern in lowered for pattern in room_patterns):
            mentioned_rooms.append(room)
    if not mentioned_rooms:
        return []

    has_person_keyword = any(keyword in lowered for keyword in PERSON_INTERACTION_KEYWORDS)
    has_named_person_pattern = bool(re.search(r'\b(?:guide|meet|find|follow|greet|ask|tell|lead)\s+[A-Z][a-z]+\b', task_command))

    if not has_person_keyword and not has_named_person_pattern:
        return []

    return [{'target_room': room, 'count': 1} for room in mentioned_rooms]


def merge_human_spawns(planned_human_spawns, inferred_human_spawns):
    merged = {(spawn['target_room'], int(spawn.get('count', 1))): spawn for spawn in planned_human_spawns}
    existing_rooms = {spawn['target_room'] for spawn in planned_human_spawns}
    for spawn in inferred_human_spawns:
        if spawn['target_room'] not in existing_rooms:
            merged[(spawn['target_room'], int(spawn.get('count', 1)))] = spawn
    return list(merged.values())


def is_follow_task(task_command):
    lowered = task_command.lower()
    return any(keyword in lowered for keyword in FOLLOW_TASK_KEYWORDS)


def resolve_object_uri(object_name, object_aliases):
    normalized = normalize_name(object_name)
    if normalized not in object_aliases:
        raise RuntimeError(f'Unknown object_name from GPSR planner: {object_name}')
    return object_aliases[normalized]


def parse_world_includes(world_path):
    root = ET.parse(world_path).getroot()
    world = root.find('world')
    if world is None:
        raise RuntimeError(f'World tag was not found in: {world_path}')
    return root, world, world.findall('include')


def area_existing_poses(area, includes):
    existing = []
    for include in includes:
        pose_text = include.findtext('pose')
        if not pose_text:
            continue
        pose = [float(value) for value in pose_text.split()]
        if len(pose) < 3:
            continue
        x, y, z = pose[:3]
        if area['x_range'][0] <= x <= area['x_range'][1] and area['y_range'][0] <= y <= area['y_range'][1]:
            if abs(z - area['z']) < 0.2:
                existing.append((x, y, z))
    return existing


def append_include(world, name, uri, pose_xyz_yaw, is_static=True):
    x, y, z, yaw = pose_xyz_yaw
    include = ET.SubElement(world, 'include')
    ET.SubElement(include, 'name').text = name
    ET.SubElement(include, 'uri').text = uri
    ET.SubElement(include, 'static').text = '1' if is_static else '0'
    ET.SubElement(include, 'pose', {'relative_to': ''}).text = f'{x:.3f} {y:.3f} {z:.3f} 0 0 {yaw:.3f}'


OBJECT_SPAWN_REQUIRED_FIELDS = {
    'object_name': str,
    'target_location': str,
}

HUMAN_SPAWN_REQUIRED_FIELDS = {
    'target_room': str,
}


def _validate_spawn_entry(entry, required_fields, entry_label):
    if not isinstance(entry, dict):
        raise RuntimeError(
            f'Invalid {entry_label} entry: expected a dict, got {type(entry).__name__!r}. Entry: {entry!r}'
        )
    for field, expected_type in required_fields.items():
        if field not in entry:
            raise RuntimeError(
                f'Invalid {entry_label} entry: missing required field {field!r}. Entry: {entry!r}'
            )
        if not isinstance(entry[field], expected_type):
            raise RuntimeError(
                f'Invalid {entry_label} entry: field {field!r} must be {expected_type.__name__}, '
                f'got {type(entry[field]).__name__!r}. Entry: {entry!r}'
            )


def apply_object_spawns(world, includes, placement_areas, object_spawns, ycb_uris):
    aliases = build_object_aliases(ycb_uris)
    area_lookup = {}
    for area in placement_areas:
        area_lookup.setdefault(area['name'], []).append(area)

    for index, spawn in enumerate(object_spawns, start=1):
        _validate_spawn_entry(spawn, OBJECT_SPAWN_REQUIRED_FIELDS, 'object_spawn')
        target_location = spawn['target_location']
        object_uri = resolve_object_uri(spawn['object_name'], aliases)
        if target_location not in area_lookup:
            raise RuntimeError(f'Unknown target_location from GPSR planner: {target_location}')

        area = area_lookup[target_location][0]
        existing_poses = area_existing_poses(area, includes)
        x, y, z, yaw = sample_pose(area, existing_poses)
        append_include(world, f'gpsr_object_{index:02d}', object_uri, (x, y, z, yaw))
        includes.append(world.findall('include')[-1])


def build_human_spawn_specs(world_path, models_root, human_spawns, seed_text, task_command):
    specs = []
    enable_teleop = is_follow_task(task_command)

    for spawn in human_spawns:
        _validate_spawn_entry(spawn, HUMAN_SPAWN_REQUIRED_FIELDS, 'human_spawn')
        target_room = spawn['target_room']
        count = int(spawn.get('count', 1))
        poses = generate_human_spawn_poses_near_room(world_path, models_root, target_room, count, seed_text)
        for x, y, z, yaw in poses:
            specs.append(
                {
                    'target_room': target_room,
                    'x': x,
                    'y': y,
                    'z': z,
                    'yaw': yaw,
                    'enable_teleop': enable_teleop,
                }
            )

    return specs


def main():
    parser = argparse.ArgumentParser(description='Apply GPSR task-specific spawns on top of a generated world.')
    parser.add_argument('--world', required=True, help='Path to the generated world file to modify in-place.')
    parser.add_argument('--base-world', required=True, help='Base world used to infer furniture geometry.')
    parser.add_argument('--placement-config', required=True, help='Placement YAML used by the world generator.')
    parser.add_argument('--models-root', required=True, help='Path to models/ycb.')
    parser.add_argument('--task-command', required=True, help='GPSR task command.')
    parser.add_argument('--groq-model-name', default='openai/gpt-oss-120b', help='Groq model name used via groq_ros.')
    parser.add_argument('--seed', default='', help='Optional seed text for deterministic spawn refinement.')
    parser.add_argument('--human-spawns-output', default='', help='Optional JSON file to write task human spawn specs.')
    args = parser.parse_args()

    placement_areas = load_placement_areas(args.placement_config, args.base_world)
    ycb_uris = discover_ycb_uris(args.models_root)
    plan = request_spawn_plan(args.task_command, placement_areas, ycb_uris, args.groq_model_name, args.base_world)
    inferred_human_spawns = infer_human_spawns_from_command(args.task_command, placement_areas, args.base_world)
    plan['human_spawns'] = merge_human_spawns(plan['human_spawns'], inferred_human_spawns)

    root, world, includes = parse_world_includes(args.world)
    apply_object_spawns(world, includes, placement_areas, plan['object_spawns'], ycb_uris)
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(args.world, encoding='utf-8', xml_declaration=True)

    if args.human_spawns_output:
        human_spawn_specs = build_human_spawn_specs(
            args.world,
            os.path.dirname(args.models_root),
            plan['human_spawns'],
            args.seed,
            args.task_command,
        )
        with open(args.human_spawns_output, 'w', encoding='utf-8') as file_obj:
            json.dump(human_spawn_specs, file_obj, indent=2)


if __name__ == '__main__':
    main()
