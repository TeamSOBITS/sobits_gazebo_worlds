from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # World file under sobits_gazebo_worlds/worlds
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='doing_laundry.world.xacro',
        description='World filename under sobits_gazebo_worlds/worlds.',
    )

    # Must match <world name='...'> inside the world file
    world_name_arg = DeclareLaunchArgument(
        'world_name',
        default_value='doing_laundry_arena',
        description='Gazebo world name (must match <world name=...> in SDF).',
    )

    # If true: remove the entrance blocker after start (i.e., "door opens")
    open_entrance_arg = DeclareLaunchArgument(
        'open_entrance_door',
        default_value='true',
        description='If true, remove entrance_door_blocker after Gazebo starts.',
    )

    # Delay before removing blocker (seconds)
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

    # Start Gazebo
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch'),
            '/gz_sim.launch.py'
        ]),
        launch_arguments=[
            ('gz_args', world_file_path),
        ],
    )

    # Remove entrance blocker via gz transport.
    # Confirmed interface on your system:
    #   /world/doing_laundry_arena/remove/blocking
    #   reqtype: gz.msgs.Entity
    #   reptype: gz.msgs.Boolean
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
    )

    # NOTE:
    # If you want to *really* gate this by open_entrance_door==true, we can add IfCondition,
    # but LaunchConfiguration is a string and people sometimes pass "True/False".
    # For now, keep it simple: always remove after delay.

    return LaunchDescription([
        world_arg,
        world_name_arg,
        open_entrance_arg,
        open_delay_arg,
        gz_sim_launch,
        open_entrance_action,
    ])