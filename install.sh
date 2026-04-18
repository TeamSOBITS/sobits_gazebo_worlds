#!/bin/bash
echo "╔══╣ Setup: SOBITS Gazebo Worlds (STARTING) ╠══╗"


# Add Gazebo models to GZ_SIM_RESOURCE_PATH
echo "export GZ_SIM_RESOURCE_PATH=\$\{GZ_SIM_RESOURCE_PATH\}:${HOME}/colcon_ws/install/sobits_gazebo_worlds/share/sobits_gazebo_worlds/models" >> ~/.bashrc

# Install Gazebo Harmonic
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt-get update
sudo apt-get install -y \
    gz-harmonic

# Clone required packages
DIR=`pwd`
cd ..

# Clone required packages
ros_packages=(
    "gz_human_sim"
    "tmc_wrs_gz"
    "aws_small_house_world"
)

#Clone all packages
for ((i = 0; i < ${#ros_packages[@]}; i++)) {
    echo "Clonning: ${ros_packages[i]}"
    git clone --recurse-submodules -b $ROS_DISTRO-devel https://github.com/TeamSOBITS/${ros_packages[i]}.git

    # Check if install.sh exists in each package
    if [ -f ${ros_packages[i]}/install.sh ]; then
        echo "Running install.sh in ${ros_packages[i]}."
        cd ${ros_packages[i]}
        bash install.sh
        cd ..
    fi
}

echo "╚══╣ Setup: SOBITS Gazebo Worlds (FINISHED) ╠══╝"
