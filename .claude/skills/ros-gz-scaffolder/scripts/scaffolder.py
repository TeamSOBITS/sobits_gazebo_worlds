#!/usr/bin/env python3
import os
import sys
import argparse
import textwrap

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(textwrap.dedent(content).lstrip())
    print(f"Created: {path}")

def generate_package(name, dest):
    pkg_path = os.path.join(dest, name)
    
    if os.path.exists(pkg_path):
        print(f"Error: {pkg_path} already exists.")
        sys.exit(1)

    # 1. package.xml
    create_file(os.path.join(pkg_path, "package.xml"), f"""\
        <?xml version="1.0"?>
        <package format="3">
          <name>{name}</name>
          <version>0.0.1</version>
          <description>Scaffolded package for Gazebo Harmonic and ROS 2 Jazzy</description>
          <maintainer email="user@todo.todo">User</maintainer>
          <license>Apache-2.0</license>
          <buildtool_depend>ament_cmake</buildtool_depend>
          <depend>rclcpp</depend>
          <depend>ros_gz_sim</depend>
          <depend>ros_gz_bridge</depend>
          <depend>ros_gz_interfaces</depend>
          <export>
            <build_type>ament_cmake</build_type>
          </export>
        </package>
    """)

    # 2. CMakeLists.txt
    create_file(os.path.join(pkg_path, "CMakeLists.txt"), f"""\
        cmake_minimum_required(VERSION 3.16)
        project({name})
        find_package(ament_cmake REQUIRED)
        find_package(ros_gz_bridge REQUIRED)
        install(DIRECTORY launch worlds config models DESTINATION share/${{PROJECT_NAME}})
        ament_package()
    """)

    # 3. launch/sim.launch.py
    create_file(os.path.join(pkg_path, "launch/sim.launch.py"), f"""\
        import os
        from ament_index_python.packages import get_package_share_directory
        from launch import LaunchDescription
        from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
        from launch.launch_description_sources import PythonLaunchDescriptionSource
        from launch_ros.actions import Node

        def generate_launch_description():
            pkg_name = '{name}'
            world_file = os.path.join(get_package_share_directory(pkg_name), 'worlds', 'empty.sdf')
            bridge_config = os.path.join(get_package_share_directory(pkg_name), 'config', 'bridge.yaml')

            gz_sim = IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
                launch_arguments={{'gz_args': f"-r {{world_file}}"}}.items(),
            )

            bridge = Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                parameters=[{{'config_file': bridge_config}}],
                output='screen'
            )

            return LaunchDescription([gz_sim, bridge])
    """)

    # 4. worlds/empty.sdf
    create_file(os.path.join(pkg_path, "worlds/empty.sdf"), """\
        <?xml version="1.0" ?>
        <sdf version="1.10">
          <world name="default_world">
            <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
            <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
            <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
            <include><uri>https://fuel.gazebosim.org/1.0/openrobotics/models/sun</uri></include>
            <include><uri>https://fuel.gazebosim.org/1.0/openrobotics/models/ground_plane</uri></include>
          </world>
        </sdf>
    """)

    # 5. config/bridge.yaml
    create_file(os.path.join(pkg_path, "config/bridge.yaml"), """\
        ---
        - ros_topic_name: "/clock"
          gz_topic_name: "/clock"
          ros_type_name: "rosgraph_msgs/msg/Clock"
          gz_type_name: "gz.msgs.Clock"
          direction: GZ_TO_ROS
    """)

    print(f"Successfully scaffolded {name} in {dest}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--dest", default=".")
    args = parser.parse_args()
    generate_package(args.name, args.dest)
