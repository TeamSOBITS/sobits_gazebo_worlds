#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseArray, Pose

import yaml
import os
import math
import time


class MultiWaypointPublisher(Node):

    def __init__(self):
        super().__init__('multi_waypoint_publisher')


        # YAML指定
        self.declare_parameter(
            'waypoint_file',
            'human_waypoints.yaml'
        )

        waypoint_file = self.get_parameter(
            'waypoint_file'
        ).value


        yaml_path = os.path.expanduser(
            f'~/colcon_ws/src/sobits_gazebo_worlds/config/{waypoint_file}'
        )


        # YAML読み込み
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)


        self.human_publishers = []


        # humanごとにpublisher作成
        for human_name, human_data in data["humans"].items():

            topic = human_data["topic"]


            pub = self.create_publisher(
                PoseArray,
                topic,
                10
            )

            self.human_publishers.append(
                (
                    human_name,
                    pub,
                    human_data["waypoints"]
                )
            )


            self.get_logger().info(
                f'{human_name}: {topic}'
            )


        # subscriber接続待ち
        time.sleep(1.0)


        # 全員分publish
        self.publish_all()



    def publish_all(self):

        for human_name, pub, waypoints in self.human_publishers:


            msg = PoseArray()

            msg.header.frame_id = "world"


            for wp in waypoints:

                pose = Pose()

                pose.position.x = wp["x"]
                pose.position.y = wp["y"]
                pose.position.z = 0.0


                yaw = wp.get(
                    "yaw",
                    0.0
                )


                pose.orientation.z = math.sin(
                    yaw / 2.0
                )

                pose.orientation.w = math.cos(
                    yaw / 2.0
                )


                msg.poses.append(pose)


            pub.publish(msg)


            self.get_logger().info(
                f'{human_name}: '
                f'{len(msg.poses)} waypoints published'
            )



def main(args=None):

    rclpy.init(args=args)

    node = MultiWaypointPublisher()


    rclpy.spin_once(
        node,
        timeout_sec=1.0
    )


    node.destroy_node()

    rclpy.shutdown()



if __name__ == '__main__':
    main()