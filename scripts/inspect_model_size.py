#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys


def get_bbox(model_path: str):
    result = subprocess.run(
        ["assimp", "info", model_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("assimp failed")

    output = result.stdout

    min_match = re.search(
        r"Minimum point\s+\(([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\)",
        output,
    )

    max_match = re.search(
        r"Maximum point\s+\(([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\)",
        output,
    )

    if not min_match or not max_match:
        raise RuntimeError("Failed to parse assimp output")

    bbox_min = tuple(map(float, min_match.groups()))
    bbox_max = tuple(map(float, max_match.groups()))

    return bbox_min, bbox_max


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("model_path")

    parser.add_argument(
        "--expected-height",
        type=float,
        help="Target height in meters (Gazebo height after pose rotation)",
    )

    parser.add_argument(
        "--height-axis",
        choices=["x", "y", "z", "auto"],
        default="auto",
        help="Axis to treat as height BEFORE Gazebo pose rotation",
    )

    args = parser.parse_args()

    bbox_min, bbox_max = get_bbox(args.model_path)

    dx = bbox_max[0] - bbox_min[0]
    dy = bbox_max[1] - bbox_min[1]
    dz = bbox_max[2] - bbox_min[2]

    print("Bounding Box (local GLB)")
    print("------------------------")
    print(f"X: {dx:.4f} m")
    print(f"Y: {dy:.4f} m")
    print(f"Z: {dz:.4f} m")

    # -----------------------------
    # HEIGHT AXIS SELECTION
    # -----------------------------

    if args.height_axis == "x":
        raw_height = dx
        axis = "X"

    elif args.height_axis == "y":
        raw_height = dy
        axis = "Y"

    elif args.height_axis == "z":
        raw_height = dz
        axis = "Z"

    else:
        # auto: choose largest axis
        vals = {"X": dx, "Y": dy, "Z": dz}
        axis = max(vals, key=lambda k: vals[k])
        raw_height = vals[axis]

    # -----------------------------
    # POSE CORRECTION
    # -----------------------------
    # <pose> roll = 90deg -> Y becomes vertical in Gazebo
    # so:
    # GLB Y-axis = Gazebo Z-axis (height)

    gazebo_height = raw_height if axis == "Z" else dy

    print()
    print("Height Estimation (Gazebo)")
    print("--------------------------")
    print(f"Selected axis (GLB): {axis}")
    print(f"Raw height          : {raw_height:.4f} m")
    print(f"Gazebo height (Z)   : {gazebo_height:.4f} m")

    if args.expected_height is not None:
        scale = args.expected_height / gazebo_height

        print()
        print("Recommended Uniform Scale")
        print("-------------------------")
        print(f"Target height : {args.expected_height:.4f} m")
        print(f"Current height: {gazebo_height:.4f} m")
        print(f"Scale factor  : {scale:.4f}")
        print()
        print(f"<scale>{scale:.4f} {scale:.4f} {scale:.4f}</scale>")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
