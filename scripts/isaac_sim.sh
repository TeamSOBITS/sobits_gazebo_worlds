#!/usr/bin/env bash
# Start the host-side Isaac Sim runner (see isaac_sim.py); the ROS 2 container then drives it.
# Usage: scripts/isaac_sim.sh [--headless | --viewer] [--domain 69]
#          [--world export/usd/rcw2026_arena.usda --robot export/usd/robots/sobit_home/sobit_home.usd --play]
# Env: ISAACSIM_PYTHON (python with isaacsim), else ISAACLAB_DIR (default ~/Documents/IsaacLab, uv venv).
set -euo pipefail
script="$(cd "$(dirname "$0")" && pwd)/isaac_sim.py"
export OMNI_KIT_ACCEPT_EULA=yes
if [[ -n "${ISAACSIM_PYTHON:-}" ]]; then
  exec "$ISAACSIM_PYTHON" "$script" "$@"
fi
ISAACLAB_DIR="${ISAACLAB_DIR:-$HOME/Documents/IsaacLab}"
if [[ ! -d "$ISAACLAB_DIR/.venv" ]]; then
  echo "error: no .venv in $ISAACLAB_DIR; set ISAACLAB_DIR or ISAACSIM_PYTHON" >&2; exit 1
fi
if ! command -v uv >/dev/null; then
  echo "error: uv not found; install it (curl -LsSf https://astral.sh/uv/install.sh | sh) or set ISAACSIM_PYTHON" >&2; exit 1
fi
exec uv run --no-sync --project "$ISAACLAB_DIR" python "$script" "$@"
