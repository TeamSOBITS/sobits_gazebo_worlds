from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import os


def gazebo_resource_path():
    model_paths = [
        os.path.join(get_package_share_directory('sobits_gazebo_worlds'), 'models'),
    ]
    for package_name in ('tmc_wrs_gz_worlds',):
        try:
            model_paths.append(os.path.join(get_package_share_directory(package_name), 'models'))
        except PackageNotFoundError:
            pass

    current_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    if current_path:
        model_paths.append(current_path)
    return os.pathsep.join(model_paths)


def generate_launch_description():
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='rcjo2025_arena.world.xacro',
        description=(
            'World filename under sobits_gazebo_worlds/worlds. '
            'Options: precomp2025_arena.world.xacro, '
            'rcjo2025_arena.world.xacro, '
            'rcjo2026_arena.world.xacro'
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
            value=gazebo_resource_path(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch'), '/gz_sim.launch.py']),
            launch_arguments=[
                ('gz_args', world_file_path)]
        )
    ])
