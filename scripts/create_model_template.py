"""
.glb や .obj 形式のオブジェクトを追加する際のスクリプトです。
※ world に出現させるには、xacro ファイルに記述する必要があります。
※ このスクリプトはあくまで models/ にテンプレートを作成するものです。
※ モデルがないというエラーが出る場合は、colcon build をしていない場合が多いです。

使い方：

pkg のルートに移動します。

```sh
cd ~/colcon_ws/src/sobits_gazebo_world
```

3D モデルの形式によって以下のスクリプトを実行します。

```sh
python3 scripts/create_model_template.py <model-name> <obj | glb>
```

実行例

```
# chair を .obj 形式で使いたい場合
python3 scripts/create_model_template.py chair obj

# chair を .glb 形式で使いたい場合
python3 scripts/create_model_template.py chair glb
```

※ 今後 README に移行する予定です
※ また、コメントアウトやプリント文の英語化も予定しています
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
        raise FileExistsError(f"モデルディレクトリ '{base_path}' は既に存在します。")

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
            <uri>model://{model_name}/meshes/{model_name}.{file_type}</uri>
          </mesh>
        </geometry>
      </visual>
      <collision name="collision">
        <geometry>
          <mesh>
            <uri>model://{model_name}/meshes/{model_name}.{file_type}</uri>
          </mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>
""")

        print(f"'{base_path}' のテンプレートを作成しました。以下の作業を行ってください。")
        print(f"1. 'models/{model_name}/meshes' フォルダに {model_name}.{file_type} を配置（ファイル名注意）")
        print("2. colcon build を実行")
        print(f"xacro に記述する uri は <uri>model://{model_name}</uri> です")

    except Exception as e:
        print(f"Error creating model directory: {e}")


def main():
    parser = argparse.ArgumentParser(description="Create a Gazebo model directory structure.")
    parser.add_argument("model_name", type=str, help="Name of the model to create.")
    parser.add_argument("file_type", type=str, choices=["obj", "glb", "stl"], help="File type for the model (e.g., obj, glb, stl).")

    args = parser.parse_args()

    create_model_directory(args.model_name, args.file_type)


if __name__ == "__main__":
    main()
