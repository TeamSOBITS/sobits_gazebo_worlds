#!/bin/bash
echo "╔══╣ Setup: SOBITS Gazebo Worlds (STARTING) ╠══╗"

sudo apt update

DIR=$(pwd)
cd ..

ros_packages=(
    "tmc_wrs_gz" \
    "aws_small_house_world"
)

# Clone all packages
for ((i = 0; i < ${#ros_packages[@]}; i++)) {
    echo "Clonning: ${ros_packages[i]}"
    git clone -b $ROS_DISTRO-devel https://github.com/TeamSOBITS/${ros_packages[i]}.git
}

cd ${DIR}

mkdir -p ~/.ignition/gazebo/6/
sudo cp -r config/gui.config ${HOME}/.ignition/gazebo/6/

echo "export GZ_SIM_RESOURCE_PATH=~/colcon_ws/install/sobits_gazebo_worlds/share/sobits_gazebo_worlds/models" >> ~/.bashrc
export "GZ_SIM_RESOURCE_PATH=~/colcon_ws/install/sobits_gazebo_worlds/share/sobits_gazebo_worlds/models"

echo "export GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH}:~/colcon_ws/install/tmc_wrs_gz_worlds/share/tmc_wrs_gz_worlds/models" >> ~/.bashrc
export "GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH}":~/colcon_ws/install/tmc_wrs_gz_worlds/share/tmc_wrs_gz_worlds/models"

echo "export GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH}:~/colcon_ws/install/aws_small_house_world/share/aws_small_house_world/models" >> ~/.bashrc
export "GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH}":~/colcon_ws/install/aws_small_house_world/share/aws_small_house_world/models"


echo "╚══╣ Setup: SOBITS Gazebo Worlds (FINISHED) ╠══╝"