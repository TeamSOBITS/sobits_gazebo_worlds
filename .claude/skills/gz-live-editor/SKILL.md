---
name: gz-live-editor
description: Interacts with a running Gazebo Harmonic simulation in real-time. Use this skill to teleport entities, spawn new models, delete objects, pause/play physics, or query the XYZ/RPY state of a robot. Trigger phrases include "move the robot to 0 0 0", "pause simulation", "where is the model [name]", or "spawn a box".
---

# Gazebo Live Editor

This skill provides a bridge between Claude and the active Gazebo Harmonic ECS (Entity Component System) using Python transport bindings.

## Instructions

When interacting with a live simulation, use the bundled `live_editor.py` script.

### Step 1: Detect World Name
The skill automatically attempts to detect the world name. If multiple worlds are running, you may need to ask the user to specify.

### Step 2: Select Action
Choose the correct command for the script based on the user's request:
- **Teleport:** `set_pose <name> <x> <y> <z> <R> <P> <Y>`
- **Query:** `get_pose <name>`
- **Control:** `pause`, `play`, or `step`
- **Spawn:** `spawn <name> <sdf_string>`
- **Delete:** `delete <name>`

### Step 3: Execute in Terminal
Run the script using `python3`. Example to teleport a robot:
```bash
python3 scripts/live_editor.py set_pose my_robot 1.0 2.0 0.5 0 0 1.57
Examples
Example 1: Resetting a Robot

User says: "My robot flipped over, put it back at the start."
Claude runs: python3 scripts/live_editor.py set_pose my_robot 0 0 0.1 0 0 0
Result: Robot is teleported 10cm above the origin in an upright position.

Example 2: Pausing for Debugging

User says: "Pause the sim so I can see the sensor data."
Claude runs: python3 scripts/live_editor.py pause

Troubleshooting

Error: Could not import gz.transport13
Cause: python3-gz-transport13 is not installed or the environment is not sourced.
Solution: Ensure the user has run sudo apt install python3-gz-transport13 and sourced their workspace.

Error: Service call timed out
Cause: Gazebo is not running or the world name is incorrect.
Solution: Check if Gazebo is open and active with gz topic -l.
```
