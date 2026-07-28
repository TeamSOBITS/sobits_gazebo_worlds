import subprocess

from geometry_msgs.msg import Pose


def spawn_model(model_type: str, new_model_name: str, pose: Pose) -> None:
    """gz コマンドをラッパーして出現コマンドを実行"""
    req_string = (
        f'name: "{new_model_name}" '
        f'sdf_filename: "model://{model_type}" '
        f"pose {{ "
        f"  position {{ "
        f"    x: {pose.position.x} "
        f"    y: {pose.position.y} "
        f"    z: {pose.position.z} "
        f"  }} "
        f"  orientation {{ "
        f"    x: {pose.orientation.x} "
        f"    y: {pose.orientation.y} "
        f"    z: {pose.orientation.z} "
        f"    w: {pose.orientation.w} "
        f"  }} "
        f"}}"
    )

    command = [
        "gz",        "service",
        "-s",        "/world/rcw2026_arena/create",
        "--reqtype", "gz.msgs.EntityFactory",
        "--reptype", "gz.msgs.Boolean",
        "--timeout", "2000",
        "--req",     req_string,
    ]

    subprocess.run(command, capture_output=True, text=True, check=True)


if __name__ == "__main__":
    import argparse
    import math

    # クォータニオン変換関数のセットアップ
    def quaternion_from_euler(roll, pitch, yaw):
        # 各角度（ラジアン）の半分を計算
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)

        # クォータニオンの各成分を計算
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy
        qw = cr * cp * cy + sr * sp * sy
        return qx, qy, qz, qw

    # パーサーの作成
    parser = argparse.ArgumentParser(
        description="Gazeboの指定ワールドにモデルを生成するスクリプト（3軸回転対応）"
    )

    # コマンドライン引数の定義（位置情報）
    parser.add_argument(
        "--model-id",
        "-i",
        required=True,
        type=str,
        help="SDFモデルのID (例: person_sitting)",
    )
    parser.add_argument(
        "--model-name",
        "-n",
        required=True,
        type=str,
        help="生成するモデルの固有インスタンス名 (例: customer_1)",
    )
    parser.add_argument(
        "--x", type=float, default=0.0, help="生成位置のX座標（デフォルト: 0.0）"
    )
    parser.add_argument(
        "--y", type=float, default=0.0, help="生成位置のY座標（デフォルト: 0.0）"
    )
    parser.add_argument(
        "--z", type=float, default=0.0, help="生成位置のZ座標（デフォルト: 0.0）"
    )

    # コマンドライン引数の定義（姿勢・回転情報）
    parser.add_argument(
        "--roll",
        "-R",
        type=float,
        default=0.0,
        help="X軸まわりの回転角度 [度単位]（デフォルト: 0.0）",
    )
    parser.add_argument(
        "--pitch",
        "-P",
        type=float,
        default=0.0,
        help="Y軸まわりの回転角度 [度単位]（デフォルト: 0.0）",
    )
    parser.add_argument(
        "--yaw",
        "-Y",
        type=float,
        default=0.0,
        help="Z軸まわりの回転角度 [度単位]（デフォルト: 0.0）",
    )

    # 引数の解析
    args = parser.parse_args()

    # 引数から受け取った値を使って Pose 型のオブジェクトを作成
    target_pose = Pose()

    # 1. 位置 (position) の代入
    target_pose.position.x = args.x
    target_pose.position.y = args.y
    target_pose.position.z = args.z

    # 2. 姿勢 (orientation) の計算と代入
    # 度数法（度）からラジアンに変換
    roll_rad = math.radians(args.roll)
    pitch_rad = math.radians(args.pitch)
    yaw_rad = math.radians(args.yaw)

    # ロール、ピッチ、ヨーからクォータニオンに変換
    qx, qy, qz, qw = quaternion_from_euler(roll_rad, pitch_rad, yaw_rad)

    target_pose.orientation.x = qx
    target_pose.orientation.y = qy
    target_pose.orientation.z = qz
    target_pose.orientation.w = qw

    # 関数の実行
    try:
        spawn_model(
            model_type=args.model_type,
            new_model_name=args.new_model_name,
            pose=target_pose,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error executing Gazebo service: {e.stderr}")
