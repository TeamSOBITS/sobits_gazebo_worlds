import subprocess

from scripts.get_model_pose import get_model_pose_raw


def get_model_pose_tag(model_name: str) -> str:
    """モデル名から姿勢情報を取得して `<pose>` タグとして返す。

    Args:
        model_name: Gazebo のモデル名。
    """
    x, y, z, roll, pitch, yaw = get_model_pose_raw(model_name)
    tag = f"<pose>{x} {y} {z} {roll} {pitch} {yaw}</pose>"

    return tag


def copy_model_pose_tag(model_name: str) -> None:
    """モデル名から姿勢情報を取得して `<pose>` タグとしてクリップボードにコピーする。

    Args:
        model_name: Gazebo のモデル名。

    Memo:
        今後，何かをコピーする機能として utils とかにしてもいいかも．
    """
    tag = get_model_pose_tag(model_name)

    try:
        # Linuxで最も一般的な xsel コマンドでのコピーを試みる
        subprocess.run(["xsel", "-bi"], input=tag, text=True, check=True)
    except FileNotFoundError:
        # もし xsel が入っていなかったら、不親切にクラッシュせず、案内を出す
        print("\n" + "="*50)
        print(" [エラー] クリップボードへのコピーに失敗しました。")
        print(" 原因: 'xsel' コマンドがシステムにインストールされていない可能性があります。")
        print(" 対策: 以下のコマンドを実行してから、再度スクリプトを動かしてください。")
        print("       sudo apt update && sudo apt install -y xsel")
        print("="*50 + "\n")

        # 代わりにターミナルに文字列を表示して、最悪手動でコピペできるようにしておく
        print(f"今回のポーズデータ: {tag}\n")
    else:
        print(f"<pose> タグをクリップボードにコピーしました: {tag}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Gazebo モデルの pose を取得し、<pose> タグをクリップボードにコピーします。"
    )
    parser.add_argument(
        "--model-name",
        "-n",
        required=True,
        help="Gazebo のモデル名を指定します。",
    )
    args = parser.parse_args()

    copy_model_pose_tag(args.model_name)


if __name__ == "__main__":
    main()
