---
name: gz-sdf-validator
description: Validates Gazebo Harmonic SDF, URDF, and Xacro files for syntax errors and schema compliance. Use this skill whenever a robot model or world file is generated, modified, or failing to load in simulation. Trigger phrases include "validate this sdf", "check my robot model", or "is this xacro correct".
---

# Gazebo SDF Validator

This skill allows Claude to verify the structural integrity of Gazebo Harmonic simulation files. It automatically handles the conversion of `.xacro` files into a temporary URDF format before validation.

## Instructions

When the user asks to validate a file, follow these steps:

### Step 1: Identify the File Type
Determine if the target file is a raw SDF (`.sdf`), a URDF (`.urdf`), or a Xacro (`.xacro`) file.

### Step 2: Run the Validator
Execute the bundled shell script using the current workspace path.

Example:
```bash
./scripts/validator.sh path/to/your_model.sdf
```

### Step 3: Interpret Results
- **Success:** If the script returns "Success," inform the user that the file is valid.
- **Failure:** If the script returns errors, analyze the XML line numbers and tags provided in the output. Propose a fix to the user and offer to run the validator again.

## Examples

### Example 1: Validating a Xacro Robot
User says: "Check if my robot.urdf.xacro is valid."
Claude runs: `./scripts/validator.sh robot.urdf.xacro`
Result: Script expands xacro and runs `gz sdf -k`. Claude reports any macro errors or missing tags.

## Troubleshooting

Error: `'xacro' command not found`
Cause: The ROS 2 environment is not sourced or xacro package is missing.
Solution: Ensure the user has run `source /opt/ros/jazzy/setup.bash`.

Error: `Invalid Tag <legacy_tag>`
Cause: Use of Ignition or Gazebo Classic tags in a Harmonic environment.
Solution: Convert the tag to the modern `gz` equivalent (e.g., `<gz:gui>` or updated system plugins).
