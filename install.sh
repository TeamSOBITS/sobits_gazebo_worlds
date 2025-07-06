#!/bin/bash
echo "╔══╣ Setup: SOBITS Gazebo Worlds (STARTING) ╠══╗"

echo "export GZ_SIM_RESOURCE_PATH=${HOME}/colcon_ws/install/sobits_gazebo_worlds/share/sobits_gazebo_worlds/models" >> ~/.bashrc

mkdir -p ~/.ignition/gazebo/6/
sudo cp -r config/gui.config ${HOME}/.ignition/gazebo/6/

sudo apt-get update

source ~/.bashrc


echo "╚══╣ Setup: SOBITS Gazebo Worlds (FINISHED) ╠══╝"