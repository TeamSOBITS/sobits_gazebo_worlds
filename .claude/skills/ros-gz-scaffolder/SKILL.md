---
name: ros-gz-scaffolder
description: Scaffolds a complete, production-ready ROS 2 Jazzy and Gazebo Harmonic package. Use this skill when starting a new robot simulation project or when creating a new simulation environment from scratch. Trigger phrases include "create a new gazebo package", "scaffold a simulation project", or "new ros2 jazzy package for harmonic".
---

# ROS 2 Jazzy + Gazebo Harmonic Scaffolder

This skill automates the creation of the boilerplate directory structure, CMake configuration, and launch files required for modern Gazebo Harmonic simulations integrated with ROS 2 Jazzy.

## Instructions

When the user requests a new project or package, follow these steps:

### Step 1: Gather Information
Ask the user for the desired package name and the destination path (defaulting to the current `src` directory if inside a colcon workspace).

### Step 2: Generate the Package
Run the bundled Python script to generate the files.

Example:
```bash
python3 scripts/scaffolder.py my_sim_pkg --dest ./src
```

### Step 3: Verification
Once the files are created, inform the user of the generated structure:
- `package.xml`: Standard dependencies (ros_gz_sim, ros_gz_bridge).
- `CMakeLists.txt`: Configured for gz-sim8 and gz-transport13.
- `launch/sim.launch.py`: A modern Python launch file.
- `config/bridge.yaml`: YAML-based bridge configuration.
- `worlds/empty.sdf`: A template world using SDF 1.10.

### Step 4: Next Steps
Advise the user to run `colcon build --packages-select <pkg_name>` to verify the setup.

## Examples

### Example 1: New Mobile Robot Project
User says: "Set up a new project for my differential drive robot named 'diff_bot_sim'."
Claude runs: `python3 scripts/scaffolder.py diff_bot_sim`
Result: A clean, building package is created with the bridge pre-configured for the clock topic.

## Troubleshooting

Error: `Permission denied`
Cause: Claude does not have write access to the target directory.
Solution: Ask the user to check directory permissions or provide a different path.

Error: `ModuleNotFoundError: No module named 'gz'`
Note: The scaffolder script itself uses standard Python libraries and does not require the Gazebo bindings to generate the text files.
```
