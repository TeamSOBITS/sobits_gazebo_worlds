#!/usr/bin/env python3
import subprocess
from std_srvs.srv import SetBool
import rclpy
from rclpy.node import Node

WORLD_NAME = "doing_laundry_arena"
MODEL_NAME = "entrance_door"


YAW_CLOSED = 0.0
YAW_OPEN = 1.5708

# setting position 
X = 0.02
Y = -3.01
Z = 0.87

class DoorOpenService(Node):
    def __init__(self):
        super().__init__("door_open_service")
        self.srv = self.create_service(SetBool, "door_open", self.on_call)
        self.get_logger().info("Service /door_open (std_srvs/SetBool) ready. true=open false=close")

    def on_call(self, request, response):
        yaw = YAW_OPEN if request.data else YAW_CLOSED
        ok, msg = self.set_model_pose(yaw)
        response.success = ok
        response.message = msg
        return response

    def set_model_pose(self, yaw: float):

        import math
        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)

        req = f"""
name: "{MODEL_NAME}"
position {{
    x: {X}
    y: {Y}
    z: {Z}
    }}
orientation {{
    x: 0
    y: 0
    z: {qz}
    w: {qw}
    }}
"""

        cmd = [
            "gz", "service",
            "-s", f"/world/{WORLD_NAME}/set_pose",
            "--reqtype", "gz.msgs.Pose",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "2000",
            "--req", req
        ]

        try:
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode != 0:
                return False, f"gz service failed: {p.stderr.strip()}"
            # stdout に "data: true" が出れば成功
            return True, p.stdout.strip()
        except Exception as e:
            return False, f"exception: {e}"

def main():
    rclpy.init()
    node = DoorOpenService()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()