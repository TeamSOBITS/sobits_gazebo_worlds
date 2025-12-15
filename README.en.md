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
   <summary>Table of Contents</summary>
   <ol>
    <li>
      <a href="#introduction">Introduction</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
    <a href="#launch-and-usage">Launch and Usage</a>
    </li>
    <li>
      <a href="#Create-New-World">Create a new world</a>
      <ul>
        <li><a href="#１">１</a></li>
        <li><a href="#２">２</a></li>
      </ul>
    </li>
    <li><a href="#furniture-list">Furniture List</a></li>
    <li><a href="#milestones">Milestones</a></li>
    <li><a href="#contributing">Contributing</a></li>
   </ol>
</details>


<!--レポジトリの概要-->
## Introduction

A repository containing multiple Gazebo files.
Specifically, it is structured to allow free customization of furniture.

> [!TODO]
> We plan to enable furniture placement via a GUI, allowing users to arrange furniture and change its colors.

<p align="right">(<a href="#readme-top">Back to the Top</a>)</p>



<!-- セットアップ -->
## Getting Started

This section describes how to set up this repository.

### Prerequisites

First, ensure the following environment is configured before proceeding with the installation steps:

| System  | Version |
| ------------- | ------------- |
| Ubuntu | 22.04 (Jammy Jellyfish) |
| ROS | Humble |
| Gazebo | ignition |

<p align="right">(<a href="#readme-top">Back to the Top</a>)</p>


### Installation

1. Change directory commands for sorce packages
   ```sh
   $ cd ~/colcon_ws/src/
   ```
2. Clone the sobits_gazebo_worlds package using the following commands
   ```sh
   $ git clone -b humble-devel https://github.com/TeamSOBITS/sobits_gazebo_worlds.git
   ```
3. Change directory commands in this repository
   ```sh
   $ cd sobits_gazebo_worlds/
   ```
4. Install the dependencies using install.sh
   ```sh
   $ bash install.sh
   ```
5. Then, build the colcon workspace
   ```sh
   $ cd ~/colcon_ws/
   $ colcon build --symlink-install
   ```

<p align="right">(<a href="#readme-top">Back to the Top</a>)</p>



<!-- 実行・操作方法 -->
## Launch and Usage

1. Specify the world file \
   Specify the `world_file_path` in [sobits_gazebo_worlds/launch/world.launch.py](launch/world.launch.py).\
   The world file can be any file, but for example, within this repository, it exists in [this folder(sobits_gazebo_worlds/worlds/)](worlds/).

2. Execute the [world.launch.py](launch/world.launch.py)
   ```sh
   $ ros2 launch sobits_gazebo_worlds world.launch.py
   ```
   Maybe launch the Gazebo of only world. 

3. [Optional] Let's try running the robot in the Gazebo environment \
   Please specify the world file from the robot repository supporting Gazebo.\
   You can also set the robot's initial position.

<p align="right">(<a href="#readme-top">Back to the Top</a>)</p>



<!-- 新しいWorld作成 -->
## Create a new world

How to Create a new world.

[TODO] Easy to create using GUI...

### １
### ２


<!-- 対応家具リスト -->
## Furniture List

Furniture List of this repository．

[TODO] No Listup...

<!-- マイルストーン -->
## Milestones

- [ ] TODO
- [x] TODO

Please check the [Issue page][issues-url] to view current bugs and requests for new features.

<p align="right">(<a href="#readme-top">Back to the Top</a>)</p>



<!-- 参考文献 -->
## Contributing

* [ROS Humble](http://wiki.ros.org/humble)
* [WRS Gazebo](https://github.com/TeamSOBITS/tmc_wrs_gz.git)
* [AWS Gazebo](https://github.com/TeamSOBITS/aws_small_house_world.git)


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
