import launch.logging
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory

import json
import os
import subprocess
import sys
import tempfile
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from human_spawn_utils import generate_human_spawn_poses, get_world_name


def generate_launch_description():

    base_world_arg = DeclareLaunchArgument(
        'base_world',
        default_value=PathJoinSubstitution([
            get_package_share_directory('sobits_gazebo_worlds'),
            'worlds',
            'rcjo2025_arena.world.xacro',
        ]),
        description='Base world template to populate.',
    )

    placement_config_arg = DeclareLaunchArgument(
        'placement_config',
        default_value=PathJoinSubstitution([
            get_package_share_directory('sobits_gazebo_worlds'),
            'config',
            'placement',
            'rcjo2025_arena.yaml',
        ]),
        description='YAML file describing placement areas.',
    )

    models_root_arg = DeclareLaunchArgument(
        'models_root',
        default_value=PathJoinSubstitution([
            get_package_share_directory('sobits_gazebo_worlds'),
            'models',
            'ycb',
        ]),
        description='Root directory of YCB models.',
    )

    seed_arg = DeclareLaunchArgument(
        'seed', 
        default_value='', 
        description='Optional seed for deterministic placement.'
    )

    object_count_arg = DeclareLaunchArgument(
        'object_count', 
        default_value='15', 
        description='Number of random YCB objects to place.'
    )

    human_count_arg = DeclareLaunchArgument(
        'human_count',
        default_value='0',
        description='Number of humans to spawn using gz_human_sim.',
    )

    human_model_arg = DeclareLaunchArgument(
        'human_model',
        default_value='person_standing',
        description='Human model preset passed to gz_human_sim.',
    )

    task_command_arg = DeclareLaunchArgument(
        'task_command',
        default_value='',
        description='Optional GPSR task command used to add task-specific object/human spawns.',
    )

    gpsr_groq_model_arg = DeclareLaunchArgument(
        'gpsr_groq_model',
        default_value='openai/gpt-oss-120b',
        description='Groq model name used via groq_ros for task spawn planning.',
    )
    
    save_world_arg = DeclareLaunchArgument(
        'save_world',
        default_value='false',
        description='If true, keep the generated world at output_world_name instead of only using a temporary file.',
    )

    output_world_name_arg = DeclareLaunchArgument(
        'output_world_name',
        default_value='rcjo2025_version_1',
        description='Optional output world filename saved under sobits_gazebo_worlds/worlds.',
    )

    return LaunchDescription(
        [
            base_world_arg,
            placement_config_arg,
            models_root_arg,
            seed_arg,
            object_count_arg,
            human_count_arg,
            human_model_arg,
            task_command_arg,
            gpsr_groq_model_arg,
            save_world_arg,
            output_world_name_arg,
            OpaqueFunction(function=_launch_setup),
        ]
    )

def _resolve_worlds_output_dir(package_share):
    source_worlds_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(package_share)))),
        'src',
        'sobits_gazebo_worlds',
        'worlds',
    )
    if os.path.isdir(source_worlds_dir):
        return source_worlds_dir
    return os.path.join(package_share, 'worlds')


def _normalize_world_filename(output_world_name):
    if not output_world_name:
        return ''
    if output_world_name.endswith('.world.xacro') or output_world_name.endswith('.world'):
        return output_world_name
    return output_world_name + '.world.xacro'

def _launch_setup(context, *args, **kwargs):
    package_share = get_package_share_directory('sobits_gazebo_worlds')
    models_package_root = os.path.join(package_share, 'models')
    generator = os.path.join(package_share, 'scripts', 'generate_worlds.py')
    base_world = LaunchConfiguration('base_world').perform(context)
    placement_config = LaunchConfiguration('placement_config').perform(context)
    models_root = LaunchConfiguration('models_root').perform(context)

    seed = LaunchConfiguration('seed').perform(context)
    object_count = LaunchConfiguration('object_count').perform(context)
    human_count = int(LaunchConfiguration('human_count').perform(context))
    human_model = LaunchConfiguration('human_model').perform(context)
    task_command = LaunchConfiguration('task_command').perform(context)
    gpsr_groq_model = LaunchConfiguration('gpsr_groq_model').perform(context)
    save_world = LaunchConfiguration('save_world').perform(context)
    output_world_name = LaunchConfiguration('output_world_name').perform(context)

    worlds_dir = _resolve_worlds_output_dir(package_share)

    normalized_output_world_name = _normalize_world_filename(output_world_name)

    if save_world.lower() == 'true':
        if not output_world_name:
            raise RuntimeError('save_world was enabled, but output_world_name was not provided.')
        generated_world = os.path.join(worlds_dir, normalized_output_world_name)
    elif output_world_name:
        generated_world = os.path.join(worlds_dir, normalized_output_world_name)
    else:
        fd, generated_world = tempfile.mkstemp(prefix='generated_random_', suffix='.world')
        os.close(fd)

    command = [
        sys.executable,
        generator,
        '--base-world',
        base_world,
        '--placement-config',
        placement_config,
        '--models-root',
        models_root,
        '--output',
        generated_world,
        '--object-count',
        object_count,
    ]

    if seed:
        command.extend(['--seed', seed])

    subprocess.check_call(command)

    task_human_spawn_specs = []
    if task_command:
        gpsr_spawner = os.path.join(package_share, 'scripts', 'generate_gpsr_task_entities.py')
        task_human_specs_fd, task_human_specs_path = tempfile.mkstemp(prefix='gpsr_task_humans_', suffix='.json')
        os.close(task_human_specs_fd)
        gpsr_command = [
            sys.executable,
            gpsr_spawner,
            '--world',
            generated_world,
            '--base-world',
            base_world,
            '--placement-config',
            placement_config,
            '--models-root',
            models_root,
            '--task-command',
            task_command,
            '--groq-model-name',
            gpsr_groq_model,
            '--seed',
            seed,
            '--human-spawns-output',
            task_human_specs_path,
        ]
        subprocess.check_call(gpsr_command)
        if os.path.exists(task_human_specs_path):
            with open(task_human_specs_path, 'r', encoding='utf-8') as file_obj:
                task_human_spawn_specs = json.load(file_obj) or []
            os.unlink(task_human_specs_path)

    world_name = get_world_name(generated_world)
    reserved_human_poses = []
    for spec in task_human_spawn_specs:
        missing = [field for field in ('x', 'y', 'z', 'yaw') if field not in spec]
        if missing:
            raise RuntimeError(
                f'task_human_spawn_spec is missing required field(s) {missing}. Entry: {spec!r}'
            )
        reserved_human_poses.append((spec['x'], spec['y'], spec['z'], spec['yaw']))
    human_spawn_poses = generate_human_spawn_poses(
        generated_world, models_package_root, human_count, seed, reserved_human_poses
    )

    actions = [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')]
            ),
            launch_arguments=[('gz_args', generated_world)],
        )
    ]

    for index, (x, y, z, yaw) in enumerate(human_spawn_poses):
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [os.path.join(get_package_share_directory('gz_human_sim'), 'launch', 'spawn_human.launch.py')]
                ),
                launch_arguments={
                    'namespace': f'human_{index + 1}',
                    'world_name': world_name,
                    'enable_teleop': 'false',
                    'model_name': f'gz_human_{index + 1}',
                    'human_model': human_model,
                    'x': str(x),
                    'y': str(y),
                    'z': str(z),
                    'yaw': str(yaw),
                }.items(),
            )
        )

    for index, spawn_spec in enumerate(task_human_spawn_specs, start=1):
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [os.path.join(get_package_share_directory('gz_human_sim'), 'launch', 'spawn_human.launch.py')]
                ),
                launch_arguments={
                    'namespace': f'gpsr_human_{index}',
                    'world_name': world_name,
                    'enable_teleop': 'true' if spawn_spec.get('enable_teleop', False) else 'false',
                    'model_name': f'gpsr_human_{index}',
                    'human_model': human_model,
                    'x': str(spawn_spec['x']),
                    'y': str(spawn_spec['y']),
                    'z': str(spawn_spec['z']),
                    'yaw': str(spawn_spec['yaw']),
                }.items(),
            )
        )

        launch.logging.get_logger('launch').info(
            f"Added GPSR task human spawn: {spawn_spec}"
        )

    launch.logging.get_logger('launch').info(
        f"Total task human spawns added: {len(task_human_spawn_specs)}"
    )
    launch.logging.get_logger('launch').info(f"GPSR task command: {task_command}")
    launch.logging.get_logger('launch').info(f"Generated world: {generated_world}")

    return actions
