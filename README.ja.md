<a name="readme-top"></a>

[EN](README.md) | [JA](README.ja.md)

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

![](img/RCJO2025_OPL.png)

# SOBITS Gazebo Worlds

<!--目次-->
<details>
   <summary>目次</summary>
   <ol>
    <li>
      <a href="#概要">概要</a>
    </li>
    <li>
      <a href="#セットアップ">セットアップ</a>
      <ul>
        <li><a href="#環境条件">環境条件</a></li>
        <li><a href="#インストール方法">インストール方法</a></li>
      </ul>
    </li>
    <li>
    <a href="#実行・操作方法">実行・操作方法</a>
      <ul>
        <li><a href="#固定worldを起動">固定Worldを起動</a></li>
        <li><a href="#ランダムworldを起動">ランダムWorldを起動</a></li>
        <li><a href="#ランタイムでランダムworldを再生成">ランタイムでランダムWorldを再生成</a></li>
      </ul>
    </li>
    <li>
    <a href="#新しいWorld作成">新しいWorld作成</a>
      <ul>
        <li><a href="#配置エリアyamlを作成">配置エリアYAMLを作成</a></li>
        <li><a href="#ランダム生成launchを使う">ランダム生成launchを使う</a></li>
      </ul>
    </li>
    <li>
    <a href="#worldと家具モデル">Worldと家具モデル</a>
      <ul>
        <li><a href="#対応家具リスト">対応家具リスト</a></li>
        <li><a href="#新しいglb家具モデルの追加">新しいGLB家具モデルの追加</a></li>
      </ul>
    </li>
    <li><a href="#マイルストーン">マイルストーン</a></li>
    <li><a href="#参考文献">参考文献</a></li>
   </ol>
</details>


<!--レポジトリの概要-->
## 概要

ignition Gazeboのファイルを複数含んだリポジトリ．
特に，家具を自由にカスタマイズできるような構成となっている．

現在は以下の機能に対応している．

- 固定の家具レイアウトを持つWorldの起動
- YCB物体のランダム配置
- YAMLによる配置面設定
- 家具モデルの`model.sdf`からの配置面サイズ・高さ推定
- 棚の`plate1` / `plate2` / `plate3`のような複数面指定
- `allowed_categories`による物体カテゴリ制限
- `human_count`による`gz_human_sim`人モデルの自動スポーン
- GPSRコマンドに応じた物体・人の追加スポーン
- follow系GPSRタスクに応じた人テレオペ起動
- 生成したWorldの保存
- ROS 2サービスによるランダム物体のランタイム再生成

> [!TODO]
> GUIで家具を配置したり色を着せ替えたりしながら家具を配置できるようにする予定．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- セットアップ -->
## セットアップ

ここで，本レポジトリのセットアップ方法について説明します．

### 環境条件

まず，以下の環境を整えてから，次のインストール段階に進んでください．

| System  | Version |
| ------------- | ------------- |
| Ubuntu | 24.04 (Noble Numbat) |
| ROS | Jazzy |
| Gazebo | ignition |

> [!NOTE]
> `Ubuntu`や`ROS`のインストール方法に関しては，[SOBIT Manual](https://github.com/TeamSOBITS/sobits_manual#%E9%96%8B%E7%99%BA%E7%92%B0%E5%A2%83%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)に参照してください．

### インストール方法

1. ROSの`src`フォルダに移動します．
   ```sh
   $ cd ~/colcon_ws/src/
   ```
2. 本レポジトリをcloneします．
   ```sh
   $ git clone -b humble-devel https://github.com/TeamSOBITS/sobits_gazebo_worlds.git
   ```
3. レポジトリの中へ移動します．
   ```sh
   $ cd sobits_gazebo_worlds/
   ```
4. 依存パッケージをインストールします．
   ```sh
   $ bash install.sh
   ```
5. パッケージをコンパイルします．
   ```sh
   $ cd ~/colcon_ws/
   $ colcon build --symlink-install
   ```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- 実行・操作方法 -->
## 実行・操作方法

### 固定Worldを起動

1. worldファイルを指定\
   [world.launch.py](launch/world.launch.py)の`world_file_path`を指定する．\
   worldファイルは[このフォルダ](worlds/)に存在する．

2. [world.launch.py](launch/world.launch.py)というlaunchファイルを起動
   ```sh
   $ ros2 launch sobits_gazebo_worlds world.launch.py
   ```
   これによってGazeboを起動することができます．

3. [任意] ロボットをGazebo環境内で動かしてみよう\
   Gazebo対応しているロボットのリポジトリから，Gazeboのworldファイルを指定．\
   また，ロボットの初期位置も設定することもできるので注意．

### ランダムWorldを起動

[random_world.launch.py](launch/random_world.launch.py)を用いることで，固定家具をベースにYCB物体と人をランダム配置したWorldを生成して起動できる．

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py
```

主な引数は以下の通り．

| Argument | Description |
| --- | --- |
| `base_world` | ベースとなるworldファイル |
| `placement_config` | 配置面YAML |
| `models_root` | YCBモデルのルートディレクトリ |
| `seed` | ランダムシード |
| `object_count` | ランダム配置するYCB物体数 |
| `human_count` | 生成する人モデル数 |
| `human_model` | `person_standing` などの人モデル名 |
| `task_command` | GPSRタスク文に基づいて追加スポーンを行うコマンド文字列 |
| `gpsr_groq_model` | `groq_ros`経由で使用するモデル名 |
| `save_world` | 生成worldを保存するかどうか |
| `output_world_name` | 保存するworld名．拡張子省略時は`.world.xacro`が自動付与される |

例:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    object_count:=15 \
    human_count:=3 \
    seed:=42
```

生成worldを保存する例:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    save_world:=true \
    output_world_name:=rcjo2025_version_1
```

この場合，`worlds/rcjo2025_version_1.world.xacro`に保存される．

GPSRコマンドに基づいて追加スポーンする例:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    task_command:="Grasp an apple on the tall table in the living room and place it on the shelf in study_room." \
    object_count:=15 \
    human_count:=2
```

この機能を使うときは，事前に`groq_ros`の`groq_action`サーバを起動しておく必要がある．
物体は配置エリアYAMLに定義された`room_name#furniture_name`に従って追加され，人は対象の部屋の家具近傍に`gz_human_sim`で追加される．

follow系タスクの例:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    task_command:="Follow Alex in the bedroom." \
    object_count:=15
```

この場合，対象の人は`enable_teleop:=true`で起動され，`sobits_teleop`経由で操作できる．

### ランタイムでランダムWorldを再生成

`random_world.launch.py`では，起動後にランダム配置されたYCB物体だけを削除・再生成するROS 2サービスが利用できる．
Gazeboやロボットを再起動せずに，ランダムレイアウトを更新できる．

利用可能なサービス:

| Service | Type | Description |
| --- | --- | --- |
| `/random_world/regenerate` | `std_srvs/srv/Trigger` | 現在のランダム物体を削除して再生成する |
| `/sobits_gazebo_worlds/change_world` | `std_srvs/srv/Trigger` | `/random_world/regenerate`と同じ動作 |
| `/random_world/clear` | `std_srvs/srv/Trigger` | 現在のランダム物体だけを削除する |

基本的な使い方:

1. まずランダムWorldを起動する．

   ```sh
   $ ros2 launch sobits_gazebo_worlds random_world.launch.py
   ```

2. ランダム物体をすべて削除する．

   ```sh
   $ ros2 service call /random_world/clear std_srvs/srv/Trigger {}
   ```

3. 新しいランダム配置を生成する．

   ```sh
   $ ros2 service call /random_world/regenerate std_srvs/srv/Trigger {}
   ```

`/random_world/regenerate`は，ランダム配置されたYCB物体のみを対象とする．
ロボット本体や固定家具，ベースWorldは削除されない．

決定的に再生成したい場合は，サービス呼び出し前に`random_world_manager`のパラメータを変更する．

```sh
$ ros2 param set /random_world_manager seed "123"
$ ros2 param set /random_world_manager object_count 20
$ ros2 service call /random_world/regenerate std_srvs/srv/Trigger {}
```

非決定的な再生成に戻す場合:

```sh
$ ros2 param set /random_world_manager seed ""
```

主なランタイムパラメータ:

| Parameter | Description |
| --- | --- |
| `seed` | 空文字なら非決定的，再現したいときは整数文字列を指定 |
| `object_count` | 再生成時に配置するYCB物体数 |
| `pause_physics_during_reconfigure` | 削除・再スポーン中に物理演算を停止するか |

> [!IMPORTANT]
> このランタイム再生成機能は`random_world.launch.py`の起動を前提としている．
> `ros2 launch sobit_home_bringup gz_minimal.launch.py`と`ros2 launch sobits_gazebo_worlds random_world.launch.py`は，どちらもGazeboを起動するため，同じシミュレーションに対して同時に使わないこと．

> [!NOTE]
> `gz_minimal.launch.py`側で同じ機能を使いたい場合は，既存のGazeboに対して`/world/<world_name>/create`，`/remove`，`/control`のbridgeと`random_world_manager.py`を追加する構成にする必要がある．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- 新しいWorld作成 -->
## 新しいWorld作成

新しいWorldの作り方．

[TODO] GUIによって簡単に家具を配置できるようにする．

### 配置エリアYAMLを作成

配置エリアは[config/placement](config/placement/)以下のYAMLで指定する．

例:

```yaml
placement_areas:
  - name: living_room#long_table
    edge_margin: 0.08
    min_object_spacing: 0.13

  - name: study_room#shelf
    surface_name: plate1
    # allowed_categories: [kitchen_item]
    edge_margin: 0.05
    min_object_spacing: 0.10
```

主なキーは以下の通り．

| Key | Description |
| --- | --- |
| `name` | world内の家具include名 |
| `surface_name` | 棚などで使用する面名．未指定時は`top` |
| `edge_margin` | 家具の端から除外する安全マージン[m] |
| `min_object_spacing` | 同一面上の物体間最小距離[m] |
| `allowed_categories` | 許可するYCBカテゴリ．未指定時は全カテゴリ |
| `selection_weight` | その面が選ばれやすくなる重み |
| `max_objects` | その面に置ける最大物体数 |

`size`や`z`は通常書く必要がない．\
家具の`model.sdf`とworld中のposeから自動で推定される．

### ランダム生成launchを使う

作成したYAMLを指定して起動する．

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    base_world:=/home/rg-station-03/colcon_ws/src/sobits_gazebo_worlds/worlds/rcjo2025_arena.world.xacro \
    placement_config:=/home/rg-station-03/colcon_ws/src/sobits_gazebo_worlds/config/placement/rcjo2025_arena.yaml \
    object_count:=20 \
    human_count:=2
```

人モデルは`floor_plane`上の空き領域から自動サンプリングされ，家具と重ならないように配置される．
GPSRタスクで追加される人モデルも，同様に対象の部屋の周辺で衝突回避しながら配置される．


<!-- Worldと家具モデル -->
## Worldと家具モデル

WorldファイルはXacro（`.world.xacro`）として[worlds/](worlds/)に，家具モデルは
[models/](models/)に格納されている．Worldは直接（固定レイアウト）起動することも，
ランダム配置launchのベースWorldとして渡すこともできる．モデルは2系統に分かれる．

- **レガシー/共有モデル**（接頭辞なし）：`long_table`・`tall_table`・`dining_table`・
  `shelf`・`sofa`・`bed`・`kachaka_shelf`など．従来のアリーナやランダム配置システムで使用．
- **実物家具GLBモデル**（`rcw26_*`）：実寸にスケールした埋め込みテクスチャのGLBメッシュ．
  下記参照．

### 対応家具リスト

配置面が定義された家具（ランダム配置システムで使用）:

- `long_table`
- `tall_table`
- `dining_table`
- `counter`
- `shelf`
  - `top`
  - `plate1`
  - `plate2`
  - `plate3`

補足:

- 家具面が`box`形状として定義されている場合は，自動でサイズ推定される
- `sofa` / `bed` / `kachaka_shelf`のような一部mesh家具は，人スポーン用に保守的なfootprintを内部で使用している

### 新しいGLB家具モデルの追加

元のGLBは`real_furniture/`（gitトラック外）にある．追加するには:

1. **Gazebo（ogre2）で描画されるようGLBを修正する．** 元のGLBは3つの問題を抱えており，
   すべて修正が必要（`trimesh`はジオメトリを立方体にリスケールするので使わず，`pygltflib`で
   インプレース編集する）:
   - 頂点**`NORMAL`**を追加 — 法線がないとライティングされず**黒**く表示される．
   - **`metallicFactor = 0`**に設定 — 完全金属＋環境マップなしでは**黒**く表示される．
   - テクスチャ**サンプラー**を追加（`baseColorFactor` / `emissiveFactor` / `alphaMode`を
     除去し`doubleSided=true`に）— サンプラーがないとテクスチャがバインドされず**白**く
     表示される．
2. `models/rcw26_<name>/`として`model.config`・`model.sdf`・`meshes/<name>.glb`で
   パッケージ化する．GLBは**Y-up**かつ単位正規化されているため，`model.sdf`で
   `roll=1.5708`（Y-up→Z-up）と一様な`<scale> = 目標高さ / GLBのY方向寸法`を適用し，
   コリジョン/ビジュアルを`高さ/2`だけ持ち上げて床に接地させる．
3. Worldから`<uri>model://rcw26_<name></uri>`で参照する．

> [!NOTE]
> 床にはカスタムのplaneを自作せず，既存の`wrc_ground_plane`モデルをincludeすること．
> そのマテリアルには木目テクスチャを描画させる`<diffuse>`項が含まれている（素の`<plane>`＋
> `albedo_map`は黒く表示される）．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- マイルストーン -->
## マイルストーン

- [x] 固定家具をベースにしたランダムYCB配置
- [x] `gz_human_sim`による人モデルスポーン
- [ ] GUIベースの家具配置編集

現時点のバッグや新規機能の依頼を確認するために[Issueページ][issues-url] をご覧ください．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>



<!-- 参考文献 -->
## 参考文献

* [ROS Jazzy](http://wiki.ros.org/jazzy)
* [WRS Gazebo](---)
* [AWS Gazebo](---)


[contributors-shield]: https://img.shields.io/github/contributors/TeamSOBITS/sobits_gazebo_worlds.svg?style=for-the-badge
[contributors-url]: https://github.com/TeamSOBITS/sobits_gazebo_worlds/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/TeamSOBITS/sobits_gazebo_worlds.svg?style=for-the-badge
[forks-url]: https://github.com/TeamSOBITS/sobits_gazebo_worlds/network/members
[stars-shield]: https://img.shields.io/github/stars/TeamSOBITS/sobits_gazebo_worlds.svg?style=for-the-badge
[stars-url]: https://github.com/TeamSOBITS/sobits_gazebo_worlds/stargazers
[issues-shield]: https://img.shields.io/github/issues/TeamSOBITS/sobits_gazebo_worlds.svg?style=for-the-badge
[issues-url]: https://github.com/TeamSOBITS/sobits_gazebo_worlds/issues
[license-shield]: https://img.shields.io/github/license/TeamSOBITS/sobits_gazebo_worlds.svg?style=for-the-badge
[license-url]: LICENSE
