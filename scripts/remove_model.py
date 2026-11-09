import subprocess


def remove_model(target: str) -> None:
    req_string = f'name: "{target}" ' f"type: MODEL"

    command = [
        "gz",
        "service",
        "-s",
        "/world/rcw2026_arena/remove",
        "--reqtype",
        "gz.msgs.Entity",
        "--reptype",
        "gz.msgs.Boolean",
        "--timeout",
        "2000",
        "--req",
        req_string,
    ]

    result = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    print(f"Successfully removed model: {target}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove a model from the Gazebo simulation environment."
    )

    parser.add_argument(
        "--model-name",
        "-n",
        required=True,
        type=str,
        help="Name of the model to remove from the Gazebo simulation.",
    )

    args = parser.parse_args()

    try:
        remove_model(target=args.model_name)
    except subprocess.CalledProcessError as e:
        print(f"Error executing Gazebo service: {e.stderr}")
