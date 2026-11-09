import subprocess

from geometry_msgs.msg import Pose


def spawn_model(model_type: str, new_model_name: str, pose: Pose) -> None:
    req_string = (
        f'name: "{new_model_name}" '
        f'sdf_filename: "model://{model_type}" '
        f"pose {{ "
        f"  position {{ "
        f"    x: {pose.position.x} "
        f"    y: {pose.position.y} "
        f"    z: {pose.position.z} "
        f"  }} "
        f"  orientation {{ "
        f"    x: {pose.orientation.x} "
        f"    y: {pose.orientation.y} "
        f"    z: {pose.orientation.z} "
        f"    w: {pose.orientation.w} "
        f"  }} "
        f"}}"
    )

    command = [
        "gz",        "service",
        "-s",        "/world/rcw2026_arena/create",
        "--reqtype", "gz.msgs.EntityFactory",
        "--reptype", "gz.msgs.Boolean",
        "--timeout", "2000",
        "--req",     req_string,
    ]

    subprocess.run(command, capture_output=True, text=True, check=True)


if __name__ == "__main__":
    import argparse
    import math

    def quaternion_from_euler(roll, pitch, yaw):
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)

        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy
        qw = cr * cp * cy + sr * sp * sy
        return qx, qy, qz, qw

    parser = argparse.ArgumentParser(
        description="Spawn a model in the specified Gazebo world (supports 3-axis rotation)"
    )

    parser.add_argument(
        "--model-id",
        "-i",
        required=True,
        type=str,
        help="SDF model ID (e.g., person_sitting)",
    )
    parser.add_argument(
        "--model-name",
        "-n",
        required=True,
        type=str,
        help="Unique instance name for the spawned model (e.g., customer_1)",
    )
    parser.add_argument(
        "--x", type=float, default=0.0, help="X coordinate of the spawn position (default: 0.0)"
    )
    parser.add_argument(
        "--y", type=float, default=0.0, help="Y coordinate of the spawn position (default: 0.0)"
    )
    parser.add_argument(
        "--z", type=float, default=0.0, help="Z coordinate of the spawn position (default: 0.0)"
    )

    parser.add_argument(
        "--roll",
        "-R",
        type=float,
        default=0.0,
        help="Rotation around the X axis in degrees (default: 0.0)",
    )
    parser.add_argument(
        "--pitch",
        "-P",
        type=float,
        default=0.0,
        help="Rotation around the Y axis in degrees (default: 0.0)",
    )
    parser.add_argument(
        "--yaw",
        "-Y",
        type=float,
        default=0.0,
        help="Rotation around the Z axis in degrees (default: 0.0)",
    )

    args = parser.parse_args()

    target_pose = Pose()

    target_pose.position.x = args.x
    target_pose.position.y = args.y
    target_pose.position.z = args.z

    roll_rad = math.radians(args.roll)
    pitch_rad = math.radians(args.pitch)
    yaw_rad = math.radians(args.yaw)

    qx, qy, qz, qw = quaternion_from_euler(roll_rad, pitch_rad, yaw_rad)

    target_pose.orientation.x = qx
    target_pose.orientation.y = qy
    target_pose.orientation.z = qz
    target_pose.orientation.w = qw

    try:
        spawn_model(
            model_type=args.model_id,
            new_model_name=args.model_name,
            pose=target_pose,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error executing Gazebo service: {e.stderr}")
