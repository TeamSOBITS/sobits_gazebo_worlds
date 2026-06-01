from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
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

    world_name_arg = DeclareLaunchArgument(
        'world_name',
        default_value='doing_laundry_arena',
        description='Gazebo world name (must match <world name=...> in SDF).',
    )

    open_entrance_arg = DeclareLaunchArgument(
        'open_entrance_door',
        default_value='false',
        description='If true, remove entrance_door_blocker after Gazebo starts.',
    )

    open_delay_arg = DeclareLaunchArgument(
        'open_delay_sec',
        default_value='2.0',
        description='Seconds to wait before opening entrance (removing blocker).',
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

    remove_blocker_cmd = ExecuteProcess(
        cmd=[
            'gz', 'service',
            '-s', ['/world/', LaunchConfiguration('world_name'), '/remove/blocking'],
            '--reqtype', 'gz.msgs.Entity',
            '--reptype', 'gz.msgs.Boolean',
            '--timeout', '3000',
            '--req', 'name: "entrance_door_blocker" type: MODEL'
        ],
        output='screen'
    )

    open_entrance_action = TimerAction(
        period=LaunchConfiguration('open_delay_sec'),
        actions=[remove_blocker_cmd],
        condition=IfCondition(LaunchConfiguration('open_entrance_door')),
    )

    return LaunchDescription([
        world_arg,
        world_name_arg,
        open_entrance_arg,
        open_delay_arg,
        gz_sim_launch,
        open_entrance_action,
    ])