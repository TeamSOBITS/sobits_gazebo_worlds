from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='doing_laundry.world.xacro',
        description='World filename under sobits_gazebo_worlds/worlds.',
    )

    world_file_path = PathJoinSubstitution([
        get_package_share_directory('sobits_gazebo_worlds'),
        'worlds',
        LaunchConfiguration('world')
    ])

    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch'),
            '/gz_sim.launch.py'
        ]),
        launch_arguments=[('gz_args', world_file_path)],
    )


    return LaunchDescription([
        world_arg,
        gz_sim_launch,
    ])