import re
import subprocess
import math

from geometry_msgs.msg import Pose


def get_model_pose_raw(target: str) -> list[float]:
    """Gazeboコマンドを実行して、生の6つの数値 [x, y, z, r, p, y] を取得する関数"""
    # 実行するGazeboコマンドの構築
    command = ["gz", "model", "-m", target, "-p"]

    # コマンドを実行し、標準出力を取得
    result = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    output = result.stdout

    # 正規表現を使って、[数値 数値 数値] の形式の行をすべて抽出する
    # [-?0-9.]+ は「マイナス記号、数字、ドット」の連続（つまり実数）にマッチします
    numbers = re.findall(r"\[\s*([-?0-9.]+)\s+([-?0-9.]+)\s+([-?0-9.]+)\s*\]", output)

    if len(numbers) < 2:
        raise RuntimeError(
            f"モデル '{target}' の位置・姿勢データをパースできませんでした。"
        )

    # 1つ目のマッチが XYZ、2つ目のマッチが RPY (ラジアン)
    xyz = [float(n) for n in numbers[0]]
    rpy = [float(n) for n in numbers[1]]

    return xyz + rpy


def get_model_pose(target: str) -> Pose:
    # 共通の共通処理（コマンド実行とパース）を呼び出す
    xyzrpy = get_model_pose_raw(target)

    # Poseオブジェクトの作成
    pose = Pose()

    # 1. 位置 (position) の代入
    pose.position.x = xyzrpy[0]
    pose.position.y = xyzrpy[1]
    pose.position.z = xyzrpy[2]

    # 2. 姿勢 (orientation) の計算と代入
    # 取得した RPY（ラジアン）をクォータニオンに変換

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

    # パーサーの作成
    parser = argparse.ArgumentParser(
        description="Gazebo内の指定したモデルの現在のPoseを取得するスクリプト"
    )

    # コマンドライン引数の定義
    parser.add_argument(
        "--model-name",
        "-m",
        required=True,
        type=str,
        help="座標を取得したいモデルの固有インスタンス名 (例: chair_left)",
    )

    # 引数の解析
    args = parser.parse_args()

    try:
        # 関数の実行
        current_pose = get_model_pose(target=args.target)

        # 結果を分かりやすく表示
        print(f"--- {args.target} の現在のPose ---")
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
