from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import launch.logging

import os
import subprocess
import sys
import tempfile

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from human_spawn_utils import get_world_name
from launch_utils import build_gz_resource_path


def generate_launch_description():
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='restaurant.world.xacro',
        description=(
            'World filename under sobits_gazebo_worlds/worlds. '
            'Options: precomp2025_arena.world.xacro, '
            'rcjo2025_arena.world.xacro, '
            'rcjo2026_arena.world.xacro'
        ),
    )

    placement_config_arg = DeclareLaunchArgument(
        'placement_config',
        default_value=PathJoinSubstitution([
            get_package_share_directory('sobits_gazebo_worlds'),
            'config',
            'placement',
            'restaurant.yaml',
        ]),
        description='YAML file describing placement areas.',
    )

    models_root_arg = DeclareLaunchArgument(
        'models_root',
        default_value=PathJoinSubstitution([
            get_package_share_directory('tmc_wrs_gz_worlds'),
            'models',
            'ycb',
        ]),
        description='Root directory of YCB models.',
    )

    seed_arg = DeclareLaunchArgument(
        'seed',
        default_value='',
        description='Optional seed for deterministic placement.',
    )

    object_count_arg = DeclareLaunchArgument(
        'object_count',
        default_value='6',
        description='Number of random YCB objects to place.',
    )

    save_world_arg = DeclareLaunchArgument(
        'save_world',
        default_value='false',
        description='If true, keep the generated world at output_world_name instead of only using a temporary file.',
    )

    output_world_name_arg = DeclareLaunchArgument(
        'output_world_name',
        default_value='restaurant_version_1',
        description='Optional output world filename saved under sobits_gazebo_worlds/worlds.',
    )

    return LaunchDescription([
        world_arg,
        placement_config_arg,
        models_root_arg,
        seed_arg,
        object_count_arg,
        save_world_arg,
        output_world_name_arg,
        OpaqueFunction(function=_launch_setup),
    ])


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
    generator = os.path.join(package_share, 'scripts', 'generate_worlds.py')

    # --- 引数の解決 ---
    world_filename    = LaunchConfiguration('world').perform(context)
    base_world        = os.path.join(package_share, 'worlds', world_filename)
    placement_config  = LaunchConfiguration('placement_config').perform(context)
    models_root       = LaunchConfiguration('models_root').perform(context)
    seed              = LaunchConfiguration('seed').perform(context)
    object_count      = LaunchConfiguration('object_count').perform(context)
    save_world        = LaunchConfiguration('save_world').perform(context)
    output_world_name = LaunchConfiguration('output_world_name').perform(context)

    # --- ワールド生成 ---
    worlds_dir = _resolve_worlds_output_dir(package_share)
    normalized_output_world_name = _normalize_world_filename(output_world_name)

    if save_world.lower() == 'true':
        if not output_world_name:
            raise RuntimeError('save_world was enabled, but output_world_name was not provided.')
        generated_world = os.path.join(worlds_dir, normalized_output_world_name)
        temp_world_path = None
    else:
        fd, generated_world = tempfile.mkstemp(prefix='generated_random_', suffix='.world')
        os.close(fd)
        temp_world_path = generated_world

    command = [
        sys.executable,
        generator,
        '--base-world',        base_world,
        '--placement-config',  placement_config,
        '--models-root',       models_root,
        '--output',            generated_world,
        '--object-count',      object_count,
    ]
    if seed:
        command.extend(['--seed', seed])

    subprocess.check_call(command)

    world_name = get_world_name(generated_world)

    # --- アクション構築 ---
    actions = [
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=build_gz_resource_path(package_share),
        ),
        # Gazebo 起動（生成済みワールドを使用）
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                os.path.join(get_package_share_directory('ros_gz_sim'), 'launch'),
                '/gz_sim.launch.py',
            ]),
            launch_arguments=[('gz_args', generated_world)],
        ),
        # ros_gz_bridge（ワールド制御サービス）
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            output='screen',
            arguments=[
                f'/world/{world_name}/create@ros_gz_interfaces/srv/SpawnEntity',
                f'/world/{world_name}/remove@ros_gz_interfaces/srv/DeleteEntity',
                f'/world/{world_name}/control@ros_gz_interfaces/srv/ControlWorld',
            ],
        ),
        # ランダム配置マネージャ
        Node(
            package='sobits_gazebo_worlds',
            executable='random_world_manager.py',
            output='screen',
            parameters=[{
                'world_name':                    world_name,
                'base_world':                    base_world,
                'placement_config':              placement_config,
                'models_root':                   models_root,
                'initial_layout_world_path':     generated_world,
                'seed':                          seed,
                'object_count':                  int(object_count),
                'object_prefix':                 'random_ycb',
                'pause_physics_during_reconfigure': True,
                'spawn_on_start':                False,
            }],
        ),
        # --- 固定ヒューマンスポーン（元のlaunchファイルより） ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('gz_human_sim'), 'launch', 'spawn_human.launch.py')]),
            launch_arguments={
                'namespace':    'human_3',
                'world_name':   world_name,
                'enable_teleop': 'false',
                'model_name':   'human_3',
                'human_model':  'custom_human',
                'human_pose':   'sit_and_raise_right_hand_2',
                'x':   '2.8',
                'y':   '3.5',
                'z':  '-0.30',
                'yaw': '3.14',
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('gz_human_sim'), 'launch', 'spawn_human.launch.py')]),
            launch_arguments={
                'namespace':    'human_4',
                'world_name':   world_name,
                'enable_teleop': 'false',
                'model_name':   'human_4',
                'human_model':  'custom_human',
                'human_pose':   'sit_and_raise_right_hand_2',
                'x':   '2.2',
                'y':   '4.1',
                'z':  '-0.30',
                'yaw': '-1.57',
            }.items(),
        ),
    ]

    # --- 一時ファイルのクリーンアップ（shutdown時） ---
    if temp_world_path:
        def _cleanup_temp_world(context):
            try:
                if os.path.exists(temp_world_path):
                    os.unlink(temp_world_path)
            except OSError as exc:
                launch.logging.get_logger('launch').warning(
                    f'Failed to remove temporary world file {temp_world_path!r}: {exc}'
                )
            return []

        actions.append(RegisterEventHandler(
            event_handler=OnShutdown(
                on_shutdown=[OpaqueFunction(function=_cleanup_temp_world)],
            )
        ))

    return actions