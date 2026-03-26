<a name="readme-top"></a>

[JA](README.md) | [EN](README.en.md)

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
      </ul>
    </li>
    <li>
    <a href="#新しいWorld作成">新しいWorld作成</a>
      <ul>
        <li><a href="#配置エリアyamlを作成">配置エリアYAMLを作成</a></li>
        <li><a href="#ランダム生成launchを使う">ランダム生成launchを使う</a></li>
      </ul>
    </li>
    <li><a href="#対応家具リスト">対応家具リスト</a></li>
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
- 生成したWorldの保存

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
| Ubuntu | 24.04 (Focal Fossa) |
| ROS | Jazzy |
| Gazebo | ignition |

> [!NOTE]
> `Ubuntu`や`ROS`のインストール方法に関しては，[SOBIT Manual](https://github.com/TeamSOBITS/sobits_manual#%E9%96%8B%E7%99%BA%E7%92%B0%E5%A2%83%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)に参照してください．

<!-- - OS: Ubuntu 20.04 
- ROS distribution: noetic Kame -->

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


<!-- 対応家具リスト -->
## 対応家具リスト

このリポジトリが保有する家具のリスト．

主な対応家具・面:

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
