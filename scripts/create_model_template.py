"""
Script for adding objects in .glb or .obj format.
Note: To spawn the object in a world, add it to the xacro file.
Note: This script only creates a template in models/.
Note: If you get a "model not found" error, you may need to run colcon build.

Usage:

Change to the package root.

```sh
cd ~/colcon_ws/src/sobits_gazebo_world
```

Run the following script for the 3D model format you want to use.

```sh
python3 scripts/create_model_template.py <model-name> <obj | glb>
```

Examples

```
# To use chair in .obj format
python3 scripts/create_model_template.py chair obj

# To use chair in .glb format
python3 scripts/create_model_template.py chair glb
```

Note: This usage guide may be moved to the README in the future.
Note: Comments and printed messages are also in English.
"""
import os
import argparse


def create_model_directory(new_model_type, file_type):
    """
    Create a model directory with the necessary files and folders.

    Args:
        new_model_type (str): Name of the model.
        file_type (str): File type (e.g., obj, glb).
    """
    base_path = os.path.join("models", new_model_type)

    if os.path.exists(base_path):
        raise FileExistsError(f"Model directory '{base_path}' already exists.")

    if "models" not in os.listdir():
        raise FileNotFoundError("No 'model' directory found. Your pwd might be wrong.")

    try:
        # Create the base directory
        os.makedirs(os.path.join(base_path, "meshes"), exist_ok=False)

        # Create model.config
        config_path = os.path.join(base_path, "model.config")
        with open(config_path, "w") as config_file:
            config_file.write(f"""
<?xml version="1.0"?>
<model>
  <name>{new_model_type}</name>
  <version>1.0</version>
  <sdf version="1.10">model.sdf</sdf>
  <author>
    <name>Author Name</name>
    <email>author@example.com</email>
  </author>
  <description>
    A description of the {new_model_type} model.
  </description>
</model>
""")

        # Create model.sdf
        sdf_path = os.path.join(base_path, "model.sdf")
        with open(sdf_path, "w") as sdf_file:
            sdf_file.write(f"""
<?xml version="1.0"?>
<sdf version="1.10">
  <model name="{new_model_type}">
    <static>false</static>
    <link name="link">
      <!-- Prevent a 90-degree rotation -->
      <pose>0 0 0 1.5708 0 0</pose>
      <visual name="visual">
        <geometry>
          <mesh>
            <uri>model://{new_model_type}/meshes/{new_model_type}.{file_type}</uri>
          </mesh>
        </geometry>
      </visual>
      <collision name="collision">
        <geometry>
          <mesh>
            <uri>model://{new_model_type}/meshes/{new_model_type}.{file_type}</uri>
          </mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>
""")

        print(f"Created the template in '{base_path}'. Complete the following steps:")
        print(f"1. Place {new_model_type}.{file_type} in 'models/{new_model_type}/meshes' (check the filename).")
        print("2. Run colcon build.")
        print(f"Use <uri>model://{new_model_type}</uri> as the URI in the xacro file.")

    except Exception as e:
        print(f"Error creating model directory: {e}")


def main():
    parser = argparse.ArgumentParser(description="Create a Gazebo model directory structure.")
    parser.add_argument("new_model_type", type=str, help="Name of the model to create.")
    parser.add_argument("file_type", type=str, choices=["obj", "glb", "stl"], help="File type for the model (e.g., obj, glb, stl).")

    args = parser.parse_args()

    create_model_directory(args.new_model_type, args.file_type)


if __name__ == "__main__":
    main()
