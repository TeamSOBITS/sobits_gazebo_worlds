import re
import subprocess
import math

from geometry_msgs.msg import Pose


def get_model_pose_raw(target: str) -> list[float]:
    """Run the Gazebo command and return the six raw values [x, y, z, r, p, y]."""
    # Build the Gazebo command to run.
    command = ["gz", "model", "-m", target, "-p"]

    # Run the command and capture standard output.
    result = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    output = result.stdout

    # Extract all lines in the form [number number number] using a regular expression.
    # [-?0-9.]+ matches a sequence of minus signs, digits, and periods (i.e., a real number).
    numbers = re.findall(r"\[\s*([-?0-9.]+)\s+([-?0-9.]+)\s+([-?0-9.]+)\s*\]", output)

    if len(numbers) < 2:
        raise RuntimeError(
            f"Could not parse position and orientation data for model '{target}'."
        )

    # The first match is XYZ; the second is RPY (in radians).
    xyz = [float(n) for n in numbers[0]]
    rpy = [float(n) for n in numbers[1]]

    return xyz + rpy


def get_model_pose(target: str) -> Pose:
    # Call the shared command execution and parsing routine.
    xyzrpy = get_model_pose_raw(target)

    # Create a Pose object.
    pose = Pose()

    # 1. Assign the position.
    pose.position.x = xyzrpy[0]
    pose.position.y = xyzrpy[1]
    pose.position.z = xyzrpy[2]

    # 2. Calculate and assign the orientation.
    # Convert the retrieved RPY angles (in radians) to a quaternion.

    roll, pitch, yaw = xyzrpy[3], xyzrpy[4], xyzrpy[5]

    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)

    pose.orientation.x = sr * cp * cy - cr * sp * sy
    pose.orientation.y = cr * sp * cy + sr * cp * sy
    pose.orientation.z = cr * cp * sy - sr * sp * cy
    pose.orientation.w = cr * cp * cy + sr * cp * sy

    return pose


if __name__ == "__main__":
    import argparse

    # Create the argument parser.
    parser = argparse.ArgumentParser(
        description="Get the current pose of a specified model in Gazebo."
    )

    # Define command-line arguments.
    parser.add_argument(
        "--model-name",
        "-m",
        required=True,
        type=str,
        help="Unique instance name of the model whose pose you want to retrieve (e.g., chair_left).",
    )

    # Parse the arguments.
    args = parser.parse_args()

    try:
        # Run the function.
        current_pose = get_model_pose(target=args.model_name)

        # Display the results in a readable format.
        print(f"--- Current pose of {args.model_name} ---")
        print(
            f"Position:    x={current_pose.position.x:.4f}, y={current_pose.position.y:.4f}, z={current_pose.position.z:.4f}"
        )
        print(
            f"Orientation: x={current_pose.orientation.x:.4f}, y={current_pose.orientation.y:.4f}, z={current_pose.orientation.z:.4f}, w={current_pose.orientation.w:.4f}"
        )

    except subprocess.CalledProcessError as e:
        print(f"Error executing Gazebo command: {e.stderr}")
    except RuntimeError as e:
        print(e)
