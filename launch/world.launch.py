"""Load a Gazebo world: resolve the file, expand xacro, run gz sim.

Other packages should include this rather than re-deriving world paths and gz
arguments (see sobit_home_bringup/launch/include/gz_minimal.launch.py, the Gazebo backend of sim_minimal.launch.py).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import OpaqueFunction
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from launch_utils import (
    EXTERNAL_WORLDS,
    build_gz_resource_path,
    expand_world,
    gz_world_name,
    resolve_world_path,
)


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value='rcjo2025_arena.world.xacro',
            description=(
                'World to load. A filename or bare name under '
                'sobits_gazebo_worlds/worlds (empty, precomp2025_arena, '
                'rcjo2025_arena, rcjo2026_arena, rcw2026_arena), one of the '
                'external aliases '
                f'({", ".join(sorted(EXTERNAL_WORLDS))}), or an absolute path.'
            ),
        ),
        DeclareLaunchArgument(
            'closed',
            default_value='false',
            description=(
                'Closed environment: 2.5 m walls + solid ceiling + per-room '
                'lights. The sobits_gazebo_worlds arenas implement it; forwarded '
                'to xacro and ignored by every other world.'
            ),
        ),
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description=(
                'Run Gazebo headless (--headless-rendering -s): server only, '
                'no GUI window. Saves GPU memory when nothing needs to be '
                'displayed.'
            ),
        ),
        DeclareLaunchArgument(
            'gz_args_extra',
            default_value='-r -v 4',
            description=(
                'Extra gz sim flags, placed after the headless flags and '
                'before the world path in gz_args.'
            ),
        ),
        DeclareLaunchArgument(
            'bridge_world_services',
            default_value='true',
            description=(
                'Bridge /world/<name>/{control,create,remove,set_pose}. The '
                'world name is read from the world file, so callers need not '
                'resolve it themselves.'
            ),
        ),
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=build_gz_resource_path(
                get_package_share_directory('sobits_gazebo_worlds')),
        ),
        OpaqueFunction(function=_launch_setup),
    ])


def _launch_setup(context, *args, **kwargs):
    world = LaunchConfiguration('world').perform(context)
    closed = LaunchConfiguration('closed').perform(context)
    headless = LaunchConfiguration('headless').perform(context)
    gz_args_extra = LaunchConfiguration('gz_args_extra').perform(context)
    bridge_services = LaunchConfiguration(
        'bridge_world_services').perform(context)

    closed = 'true' if closed.lower() in ('true', '1', 'yes') else 'false'

    world_file = resolve_world_path(world)
    # Read the name from the original file: it is a literal, so expansion
    # cannot change it, and the original exists even if expansion fell back.
    world_name = gz_world_name(world_file)

    # Expand xacro so macro-generated models actually spawn. No-op for plain
    # .sdf/.world; falls back to world_file if xacro is unavailable.
    world_file = expand_world(world_file, {'closed': closed})

    # --headless-rendering needs -s (server only) alongside it, and both must
    # precede the world path.
    headless_flags = ('--headless-rendering -s'
                      if headless.lower() in ('true', '1', 'yes') else '')

    gz_args = ' '.join(
        part for part in (headless_flags, gz_args_extra, world_file) if part)

    actions = [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch', 'gz_sim.launch.py')]),
            launch_arguments=[('gz_args', gz_args)],
        )
    ]

    if bridge_services.lower() in ('true', '1', 'yes'):
        actions.append(Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='world_services_bridge',
            output='screen',
            arguments=[
                f'/world/{world_name}/control@ros_gz_interfaces/srv/ControlWorld',
                f'/world/{world_name}/create@ros_gz_interfaces/srv/SpawnEntity',
                f'/world/{world_name}/remove@ros_gz_interfaces/srv/DeleteEntity',
                f'/world/{world_name}/set_pose@ros_gz_interfaces/srv/SetEntityPose',
            ],
        ))

    return actions
