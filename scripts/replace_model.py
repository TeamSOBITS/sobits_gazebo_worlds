from scripts.get_model_pose import get_model_pose
from scripts.remove_model import remove_model
from scripts.spawn_model import spawn_model


def replace_model(
    target_model_name: str, new_model_id: str, new_model_name: str
) -> None:
    # 1. 既存のモデルの現在のPose（位置と姿勢）を取得
    pose = get_model_pose(target_model_name)

    # 2. 古いモデルをワールドから削除
    remove_model(target_model_name)

    # 3. 同じPoseに、新しいモデルIDと名前で生成
    spawn_model(new_model_id, new_model_name, pose)

    print(
        f"Successfully replaced '{target_model_name}' with '{new_model_name}' ({new_model_id})"
    )


if __name__ == "__main__":
    import argparse
    import subprocess

    # パーサーの作成
    parser = argparse.ArgumentParser(
        description="Gazebo内の既存モデルの座標を引き継いで、別のモデルに置き換えるスクリプト"
    )

    # コマンドライン引数の定義
    parser.add_argument(
        "--target",
        "-t",
        required=True,
        type=str,
        help="消去・置き換え対象となる、現在ワールドにいるモデル名 (例: chair_left)",
    )
    parser.add_argument(
        "--new-id",
        "-i",
        required=True,
        type=str,
        help="新しく配置するSDFモデルのID (例: chair_right)",
    )
    parser.add_argument(
        "--new-name",
        "-n",
        required=True,
        type=str,
        help="新しく配置するモデルの固有インスタンス名 (例: chair_left_v2)",
    )

    # 引数の解析
    args = parser.parse_args()

    # 関数の実行
    try:
        replace_model(
            target_model_name=args.target,
            new_model_id=args.new_id,
            new_model_name=args.new_name,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error during model replacement (Gazebo Service Failed): {e.stderr}")
    except RuntimeError as e:
        print(f"Error during model replacement (Parsing Failed): {e}")
