from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory

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
    save_world = LaunchConfiguration('save_world').perform(context)
    output_world_name = LaunchConfiguration('output_world_name').perform(context)

    worlds_dir = _resolve_worlds_output_dir(package_share)

    if save_world.lower() == 'true':
        if not output_world_name:
            raise RuntimeError('save_world was enabled, but output_world_name was not provided.')
        generated_world = os.path.join(worlds_dir, output_world_name + '.world.xacro')
    elif output_world_name:
        generated_world = os.path.join(worlds_dir, output_world_name + '.world.xacro')
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

    world_name = get_world_name(generated_world)
    human_spawn_poses = generate_human_spawn_poses(generated_world, models_package_root, human_count, seed)

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

    return actions
