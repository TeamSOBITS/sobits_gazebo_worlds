import subprocess


def remove_model(model_name: str) -> None:
    # 削除用リクエスト文を綺麗に改行して構築
    req_string = f'name: "{model_name}" ' f"type: MODEL"

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

    # コマンドの実行
    result = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    print(f"Successfully removed model: {model_name}")


if __name__ == "__main__":
    import argparse

    # パーサーの作成
    parser = argparse.ArgumentParser(
        description="Gazeboの指定ワールドからモデルを削除するスクリプト"
    )

    # コマンドライン引数の定義
    parser.add_argument(
        "--model-name",
        "-n",
        required=True,
        type=str,
        help="削除したいモデルの固有インスタンス名 (例: customer_1)",
    )

    # 引数の解析
    args = parser.parse_args()

    # 関数の実行
    try:
        remove_model(model_name=args.model_name)
    except subprocess.CalledProcessError as e:
        print(f"Error executing Gazebo service: {e.stderr}")
