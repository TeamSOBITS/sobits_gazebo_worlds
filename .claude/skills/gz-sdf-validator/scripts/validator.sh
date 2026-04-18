#!/bin/bash
# Skill: gz-sdf-validator
# Purpose: Validates simulation files for Gazebo Harmonic

# Colors for clear reporting to the Agent
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' 

if [ -z "$1" ]; then
    echo -e "${RED}Error: No file provided for validation.${NC}"
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo -e "${RED}Error: File '$FILE' not found.${NC}"
    exit 1
fi

TARGET_FILE="$FILE"
TMP_FILE=""

# Handle Xacro files
if [[ "$FILE" == *.xacro ]]; then
    if ! command -v xacro &> /dev/null; then
        echo -e "${RED}Error: 'xacro' command not found. Is ROS 2 sourced?${NC}"
        exit 1
    fi
    
    TMP_FILE=$(mktemp /tmp/gz_val_XXXXXX.urdf)
    echo -e "${YELLOW}Expanding Xacro to temporary URDF...${NC}"
    if ! xacro "$FILE" > "$TMP_FILE"; then
        echo -e "${RED}Xacro expansion failed.${NC}"
        rm -f "$TMP_FILE"
        exit 1
    fi
    TARGET_FILE="$TMP_FILE"
fi

echo -e "${YELLOW}Validating with Gazebo Harmonic (gz sdf -k)...${NC}"

# Run Gazebo Harmonic Validator
# -k stands for 'check' (standard validation)
OUTPUT=$(gz sdf -k "$TARGET_FILE" 2>&1)
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ Success: The file is valid for Gazebo Harmonic!${NC}"
    echo "$OUTPUT"
else
    echo -e "${RED}❌ Validation Failed:${NC}"
    echo "--------------------------------------"
    echo "$OUTPUT"
    echo "--------------------------------------"
fi

# Cleanup
if [ -n "$TMP_FILE" ]; then
    rm -f "$TMP_FILE"
fi

exit $RESULT
