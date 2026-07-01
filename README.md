<a name="readme-top"></a>

[EN](README.md) | [JA](README.ja.md)

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

![](img/RCJO2025_OPL.png)

# SOBITS Gazebo Worlds

<!-- Table of contents -->
<details>
   <summary>Table of Contents</summary>
   <ol>
    <li>
      <a href="#overview">Overview</a>
    </li>
    <li>
      <a href="#setup">Setup</a>
      <ul>
        <li><a href="#requirements">Requirements</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
    <a href="#usage">Usage</a>
      <ul>
        <li><a href="#launch-a-fixed-world">Launch a Fixed World</a></li>
        <li><a href="#launch-a-random-world">Launch a Random World</a></li>
        <li><a href="#regenerate-a-random-world-at-runtime">Regenerate a Random World at Runtime</a></li>
      </ul>
    </li>
    <li>
    <a href="#creating-a-new-world">Creating a New World</a>
      <ul>
        <li><a href="#create-a-placement-area-yaml">Create a Placement-Area YAML</a></li>
        <li><a href="#use-the-random-generation-launch">Use the Random-Generation Launch</a></li>
      </ul>
    </li>
    <li>
    <a href="#worlds-and-furniture-models">Worlds and Furniture Models</a>
      <ul>
        <li><a href="#supported-furniture-list">Supported Furniture List</a></li>
        <li><a href="#adding-a-new-glb-furniture-model">Adding a New GLB Furniture Model</a></li>
      </ul>
    </li>
    <li><a href="#milestones">Milestones</a></li>
    <li><a href="#references">References</a></li>
   </ol>
</details>


<!-- Repository overview -->
## Overview

A repository bundling multiple Gazebo (ignition) world files.
It is structured so that furniture can be freely customized.

The following features are currently supported:

- Launching worlds with fixed furniture layouts
- Random placement of YCB objects
- Placement-surface configuration via YAML
- Placement-surface size/height estimation from a furniture model's `model.sdf`
- Multi-surface specification for shelves (e.g. `plate1` / `plate2` / `plate3`)
- Object-category restriction via `allowed_categories`
- Automatic spawning of `gz_human_sim` human models via `human_count`
- Additional spawning of objects/people from GPSR commands
- Human teleop launch for follow-type GPSR tasks
- Saving generated worlds
- Runtime regeneration of random objects via ROS 2 services

> [!TODO]
> Planned: place and re-color furniture interactively through a GUI.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- Setup -->
## Setup

This section explains how to set up this repository.

### Requirements

First prepare the following environment, then proceed to the installation step.

| System  | Version |
| ------------- | ------------- |
| Ubuntu | 24.04 (Noble Numbat) |
| ROS | Jazzy |
| Gazebo | ignition |

> [!NOTE]
> For how to install `Ubuntu` and `ROS`, refer to the [SOBIT Manual](https://github.com/TeamSOBITS/sobits_manual#%E9%96%8B%E7%99%BA%E7%92%B0%E5%A2%83%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6).

### Installation

1. Move to the `src` folder of your ROS workspace.
   ```sh
   $ cd ~/colcon_ws/src/
   ```
2. Clone this repository.
   ```sh
   $ git clone -b humble-devel https://github.com/TeamSOBITS/sobits_gazebo_worlds.git
   ```
3. Move into the repository.
   ```sh
   $ cd sobits_gazebo_worlds/
   ```
4. Install the dependencies.
   ```sh
   $ bash install.sh
   ```
5. Build the package.
   ```sh
   $ cd ~/colcon_ws/
   $ colcon build --symlink-install
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- Usage -->
## Usage

### Launch a Fixed World

1. Specify the world file\
   Set `world_file_path` in [world.launch.py](launch/world.launch.py).\
   World files live in [this folder](worlds/).

2. Launch the [world.launch.py](launch/world.launch.py) launch file.
   ```sh
   $ ros2 launch sobits_gazebo_worlds world.launch.py
   ```
   This starts Gazebo.

3. [Optional] Try driving a robot inside the Gazebo environment\
   From a Gazebo-compatible robot repository, point it to the Gazebo world file.\
   Note that you can also set the robot's initial pose.

### Launch a Random World

Using [random_world.launch.py](launch/random_world.launch.py), you can generate and launch a world that randomly places YCB objects and people on top of the fixed furniture base.

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py
```

The main arguments are as follows.

| Argument | Description |
| --- | --- |
| `base_world` | Base world file |
| `placement_config` | Placement-surface YAML |
| `models_root` | Root directory of the YCB models |
| `seed` | Random seed |
| `object_count` | Number of YCB objects to place randomly |
| `human_count` | Number of human models to spawn |
| `human_model` | Human model name, e.g. `person_standing` |
| `task_command` | Command string that triggers extra spawns based on a GPSR task sentence |
| `gpsr_groq_model` | Model name used via `groq_ros` |
| `save_world` | Whether to save the generated world |
| `output_world_name` | Name of the saved world; if the extension is omitted, `.world.xacro` is appended automatically |

Example:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    object_count:=15 \
    human_count:=3 \
    seed:=42
```

Example that saves the generated world:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    save_world:=true \
    output_world_name:=rcjo2025_version_1
```

In this case it is saved to `worlds/rcjo2025_version_1.world.xacro`.

Example that spawns extra items from a GPSR command:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    task_command:="Grasp an apple on the tall table in the living room and place it on the shelf in study_room." \
    object_count:=15 \
    human_count:=2
```

To use this feature, the `groq_action` server of `groq_ros` must be running beforehand.
Objects are added according to the `room_name#furniture_name` defined in the placement-area YAML, and people are added near the furniture of the target room via `gz_human_sim`.

Example of a follow-type task:

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    task_command:="Follow Alex in the bedroom." \
    object_count:=15
```

In this case the target person is launched with `enable_teleop:=true` and can be operated via `sobits_teleop`.

### Regenerate a Random World at Runtime

With `random_world.launch.py`, ROS 2 services are available to delete and regenerate only the randomly placed YCB objects after launch.
You can update the random layout without restarting Gazebo or the robot.

Available services:

| Service | Type | Description |
| --- | --- | --- |
| `/random_world/regenerate` | `std_srvs/srv/Trigger` | Delete the current random objects and regenerate them |
| `/sobits_gazebo_worlds/change_world` | `std_srvs/srv/Trigger` | Same behavior as `/random_world/regenerate` |
| `/random_world/clear` | `std_srvs/srv/Trigger` | Delete only the current random objects |

Basic usage:

1. First launch a random world.

   ```sh
   $ ros2 launch sobits_gazebo_worlds random_world.launch.py
   ```

2. Delete all random objects.

   ```sh
   $ ros2 service call /random_world/clear std_srvs/srv/Trigger {}
   ```

3. Generate a new random layout.

   ```sh
   $ ros2 service call /random_world/regenerate std_srvs/srv/Trigger {}
   ```

`/random_world/regenerate` targets only the randomly placed YCB objects.
The robot itself, the fixed furniture, and the base world are not deleted.

To regenerate deterministically, change the `random_world_manager` parameters before calling the service.

```sh
$ ros2 param set /random_world_manager seed "123"
$ ros2 param set /random_world_manager object_count 20
$ ros2 service call /random_world/regenerate std_srvs/srv/Trigger {}
```

To return to non-deterministic regeneration:

```sh
$ ros2 param set /random_world_manager seed ""
```

Main runtime parameters:

| Parameter | Description |
| --- | --- |
| `seed` | Non-deterministic when empty; specify an integer string to reproduce a layout |
| `object_count` | Number of YCB objects placed on regeneration |
| `pause_physics_during_reconfigure` | Whether to pause physics during deletion/re-spawning |

> [!IMPORTANT]
> This runtime-regeneration feature assumes that `random_world.launch.py` is running.
> `ros2 launch sobit_home_bringup gz_minimal.launch.py` and `ros2 launch sobits_gazebo_worlds random_world.launch.py` both start Gazebo, so do not use them on the same simulation at the same time.

> [!NOTE]
> To use the same feature on the `gz_minimal.launch.py` side, you need to add bridges for `/world/<world_name>/create`, `/remove`, and `/control`, plus `random_world_manager.py`, against the existing Gazebo instance.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- Creating a new world -->
## Creating a New World

How to create a new world.

[TODO] Make it easy to place furniture through a GUI.

### Create a Placement-Area YAML

Placement areas are specified in YAML files under [config/placement](config/placement/).

Example:

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

The main keys are as follows.

| Key | Description |
| --- | --- |
| `name` | Furniture include name in the world |
| `surface_name` | Surface name used for shelves etc.; defaults to `top` if unspecified |
| `edge_margin` | Safety margin [m] excluded from the furniture edge |
| `min_object_spacing` | Minimum distance [m] between objects on the same surface |
| `allowed_categories` | Allowed YCB categories; all categories if unspecified |
| `selection_weight` | Weight that makes a surface more likely to be chosen |
| `max_objects` | Maximum number of objects that can be placed on the surface |

You usually do not need to write `size` or `z`.\
They are estimated automatically from the furniture's `model.sdf` and its pose in the world.

### Use the Random-Generation Launch

Launch with the YAML you created.

```sh
$ ros2 launch sobits_gazebo_worlds random_world.launch.py \
    base_world:=/home/rg-station-03/colcon_ws/src/sobits_gazebo_worlds/worlds/rcjo2025_arena.world.xacro \
    placement_config:=/home/rg-station-03/colcon_ws/src/sobits_gazebo_worlds/config/placement/rcjo2025_arena.yaml \
    object_count:=20 \
    human_count:=2
```

Human models are automatically sampled from the free area on the `floor_plane` and placed so they do not overlap furniture.
People added by GPSR tasks are likewise placed around the target room while avoiding collisions.


<!-- Worlds and furniture models -->
## Worlds and Furniture Models

World files live in [worlds/](worlds/) and furniture models in [models/](models/).
Worlds are written as `.world.xacro` and can be launched directly (fixed layout) or fed to
the random-placement launch as a base world. The models fall into two families:

- **Legacy / shared models** (unprefixed) such as `long_table`, `tall_table`,
  `dining_table`, `shelf`, `sofa`, `bed`, `kachaka_shelf` — used by the older arenas and by
  the random-placement system.
- **Real-furniture GLB models** (`rcw26_*`) — embedded-texture GLB meshes scaled to
  real-world dimensions, described below.

### Supported Furniture List

Furniture with defined placement surfaces (used by the random-placement system):

- `long_table`
- `tall_table`
- `dining_table`
- `counter`
- `shelf`
  - `top`
  - `plate1`
  - `plate2`
  - `plate3`

Notes:

- When a furniture surface is defined as a `box` shape, its size is estimated automatically.
- Some mesh furniture such as `sofa` / `bed` / `kachaka_shelf` uses a conservative internal footprint for human spawning.


### Adding a New GLB Furniture Model

The source GLBs live in `real_furniture/` (untracked). To add one:

1. **Fix the GLB so it renders in Gazebo ogre2.** Raw GLBs from the source set are broken
   three ways and must all be fixed (edit in place with `pygltflib`, **not** `trimesh`,
   which rescales the geometry to a cube):
   - Add per-vertex **`NORMAL`** — without normals there is no lighting and the mesh
     renders **black**.
   - Set **`metallicFactor = 0`** — a fully-metallic surface with no environment map
     renders **black**.
   - Add a texture **sampler** (and strip `baseColorFactor` / `emissiveFactor` /
     `alphaMode`, set `doubleSided=true`) — without a sampler the texture is not bound and
     the mesh renders **white**.
2. Package it as `models/rcw26_<name>/` with `model.config`, `model.sdf`, and
   `meshes/<name>.glb`. GLBs are **Y-up** and unit-normalized, so `model.sdf` applies
   `roll=1.5708` (Y-up -> Z-up) and a uniform `<scale> = target_height / GLB_Y_extent`,
   with the collision/visual raised by `height/2` to rest on the floor.
3. Reference it in a world with `<uri>model://rcw26_<name></uri>`.

> [!NOTE]
> For the floor, include the existing `wrc_ground_plane` model rather than authoring a
> custom plane — its material carries the `<diffuse>` term that makes the wood texture
> render (a bare `<plane>` + `albedo_map` renders black).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- Milestones -->
## Milestones

- [x] Random YCB placement on top of fixed furniture
- [x] Human-model spawning via `gz_human_sim`
- [ ] GUI-based furniture placement editing

See the [Issues page][issues-url] to check current bugs and feature requests.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- References -->
## References

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
