from scripts.get_model_pose import get_model_pose
from scripts.remove_model import remove_model
from scripts.spawn_model import spawn_model


def replace_model(
    target: str, model_type: str, model_name: str
) -> None:
    """TODO: Currently, this function does not check if the new model ID exists in Gazebo. It will just delete the old model if the model ID is invalid."""
    # 1. Get the current pose (position and orientation) of the existing model.
    pose = get_model_pose(target)

    # 2. Remove the old model from the world.
    remove_model(target)

    # 3. Spawn a new model with the specified model ID and name at the same pose.
    spawn_model(model_type, model_name, pose)

    print(
        f"Successfully replaced '{target}' with '{model_name}' ({model_type})"
    )


if __name__ == "__main__":
    import argparse
    import subprocess

    # Create the argument parser.
    parser = argparse.ArgumentParser(
        description="Replace an existing Gazebo model with another model, preserving its pose."
    )

    # Define command-line arguments.
    parser.add_argument(
        "--target",
        "-t",
        required=True,
        type=str,
        help="Name of the model currently in the world to remove and replace (e.g., chair_left).",
    )
    parser.add_argument(
        "--new-id",
        "-i",
        required=True,
        type=str,
        help="SDF model ID of the model to spawn (e.g., chair_right).",
    )
    parser.add_argument(
        "--new-name",
        "-n",
        required=True,
        type=str,
        help="Unique instance name for the model to spawn (e.g., chair_left_v2).",
    )

    # Parse the arguments.
    args = parser.parse_args()

    # Run the function.
    try:
        replace_model(
            target=args.target,
            model_type=args.new_id,
            model_name=args.new_name,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error during model replacement (Gazebo Service Failed): {e.stderr}")
    except RuntimeError as e:
        print(f"Error during model replacement (Parsing Failed): {e}")
