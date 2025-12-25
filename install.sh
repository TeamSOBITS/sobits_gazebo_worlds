#!/bin/bash
echo "╔══╣ Setup: SOBITS Gazebo Worlds (STARTING) ╠══╗"

echo "export GZ_SIM_RESOURCE_PATH=${HOME}/colcon_ws/install/sobits_gazebo_worlds/share/sobits_gazebo_worlds/models" >> ~/.bashrc

mkdir -p ~/.gz/sim/8/
sudo cp -r config/gui.config ${HOME}/.gz/sim/8/

sudo apt update

source ~/.bashrc


echo "╚══╣ Setup: SOBITS Gazebo Worlds (FINISHED) ╠══╝"