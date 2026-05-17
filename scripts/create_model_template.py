"""
.glb や .obj 形式のオブジェクトを追加する際のスクリプトです。
static is false
"""
import os
import argparse


def create_model_directory(model_name, file_type):
    """
    Create a model directory with the necessary files and folders.

    Args:
        model_name (str): Name of the model.
        file_type (str): File type (e.g., obj, glb).
    """
    base_path = os.path.join("models", model_name)

    if os.path.exists(base_path):
        print(f"モデルディレクトリ '{base_path}' は既に存在します。")
        exit(1)

    try:
        # Create the base directory
        os.makedirs(os.path.join(base_path, "meshes"), exist_ok=True)

        # Create model.config
        config_path = os.path.join(base_path, "model.config")
        with open(config_path, "w") as config_file:
            config_file.write(f"""
<?xml version="1.0"?>
<model>
    <name>{model_name}</name>
    <version>1.0</version>
    <sdf version="1.10">model.sdf</sdf>
    <author>
        <name>Author Name</name>
        <email>author@example.com</email>
    </author>
    <description>
        A description of the {model_name} model.
    </description>
</model>
""")

        # Create model.sdf
        sdf_path = os.path.join(base_path, "model.sdf")
        with open(sdf_path, "w") as sdf_file:
            sdf_file.write(f"""
<?xml version="1.0"?>
<sdf version="1.10">
    <model name="{model_name}">
        <static>false</static>
        <link name="link">
            <!-- 90度回転を防止 -->
            <pose>0 0 0 1.5708 0 0</pose>
            <visual name="visual">
                <geometry>
                    <mesh>
                        <uri>meshes/{model_name}.{file_type}</uri>
                    </mesh>
                </geometry>
            </visual>
        </link>
    </model>
</sdf>
""")

        print(f"'{base_path}' のテンプレートを作成しました。")
        print(f"'meshes' フォルダに {file_type} ファイルを配置し、colcon build を行ってください。")
        print(f"<uri>model://{model_name}</uri>")

    except Exception as e:
        print(f"Error creating model directory: {e}")


def main():
    parser = argparse.ArgumentParser(description="Create a Gazebo model directory structure.")
    parser.add_argument("model_name", type=str, help="Name of the model to create.")
    parser.add_argument("file_type", type=str, choices=["obj", "glb"], help="File type for the model (e.g., obj, glb).")

    args = parser.parse_args()

    create_model_directory(args.model_name, args.file_type)


if __name__ == "__main__":
    main()
