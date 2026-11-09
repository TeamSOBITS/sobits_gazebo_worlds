import subprocess

from scripts.get_model_pose import get_model_pose_raw


def get_model_pose_tag(target: str) -> str:
    """Get a model's pose and return it as a `<pose>` tag.

    Args:
        target: The Gazebo model name.
    """
    x, y, z, roll, pitch, yaw = get_model_pose_raw(target)
    tag = f"<pose>{x} {y} {z} {roll} {pitch} {yaw}</pose>"

    return tag


def copy_model_pose_tag(target: str) -> None:
    """Get a model's pose and copy it to the clipboard as a `<pose>` tag.

    Args:
        target: The Gazebo model name.

    Memo:
        This may be moved to a utility module if more copy-related features are added.
    """
    tag = get_model_pose_tag(target)

    try:
        # Try copying with xsel, a commonly used clipboard command on Linux.
        subprocess.run(["xsel", "-bi"], input=tag, text=True, check=True)
    except FileNotFoundError:
        # If xsel is unavailable, show instructions instead of crashing without guidance.
        print("\n" + "="*50)
        print(" [Error] Failed to copy to the clipboard.")
        print(" Cause: The 'xsel' command may not be installed on your system.")
        print(" Fix: Run the following command, then run the script again.")
        print("       sudo apt update && sudo apt install -y xsel")
        print("="*50 + "\n")

        # Print the string in the terminal so it can be copied manually if needed.
        print(f"Pose data: {tag}\n")
    else:
        print(f"Copied the <pose> tag to the clipboard: {tag}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Get a Gazebo model's pose and copy it to the clipboard as a <pose> tag."
    )
    parser.add_argument(
        "--model-name",
        "-n",
        required=True,
        help="Name of the Gazebo model.",
    )
    args = parser.parse_args()

    copy_model_pose_tag(args.model_name)


if __name__ == "__main__":
    main()
