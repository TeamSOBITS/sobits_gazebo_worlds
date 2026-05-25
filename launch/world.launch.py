from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory
import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from launch_utils import build_gz_resource_path


def generate_launch_description():
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='rcw2026_arena.world.xacro',
        description=(
            'World filename under sobits_gazebo_worlds/worlds. '
            'Options: precomp2025_arena.world.xacro, '
            'rcjo2025_arena.world.xacro, '
            'rcjo2026_arena.world.xacro, '
            'rcw2026_arena.world.xacro'
        ),
    )

    world_file_path = PathJoinSubstitution([
        get_package_share_directory('sobits_gazebo_worlds'),
        'worlds',
        LaunchConfiguration('world')
    ])

    return LaunchDescription([
        world_arg,
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=build_gz_resource_path(get_package_share_directory('sobits_gazebo_worlds')),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch'), '/gz_sim.launch.py']),
            launch_arguments=[
                ('gz_args', world_file_path)]
        )
    ])
