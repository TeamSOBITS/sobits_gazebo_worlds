---
license: bsd-3-clause
pretty_name: SOBITS Simulation Assets (USD / MJCF)
tags:
  - robotics
  - simulation
  - isaac-sim
  - mujoco
  - usd
  - mjcf
  - robocup-at-home
---

# SOBITS Simulation Assets

RoboCup@Home arena worlds and furniture models from
[sobits_gazebo_worlds](https://github.com/TeamSOBITS/sobits_gazebo_worlds), exported from SDF to
**USD** (NVIDIA Isaac Sim 5.0–6.1) and **MJCF** (MuJoCo 3.x, lerobot/gym-hil range `<3.9`).
Generated files only; the SDF sources live in the GitHub repository.

## Layout

```
usd/<world>.usda                 13 world variants (<world>_closed = 2.5 m walls + roof + room lights)
usd/materials/textures/          textures shared by the world stages (relative paths)
usd/models/<model>/<model>.usda  45 standalone furniture / object models
mjcf/<world>/<world>.xml         one MJCF per world, assets in mjcf/<world>/assets/
mjcf/models/<model>/<model>.xml  standalone models
sdf/<world>.sdf                  xacro-expanded SDF the exports were generated from
usd/robots/<robot>/<robot>.usd   robot wrapper stage (+ <robot>/ package dir: payloads/, Textures/)
usd/robots/<robot>/<robot>_ros2_control.yaml   controller_manager config of the USD's ROS2_Control graph
mjcf/robots/<robot>/<robot>.xml  robot MJCF
robots/<robot>.json              robot provenance (see Robots)
MANIFEST.json                    date, source commits (sobits_gazebo_worlds, gz-usd, gz-mujoco), counts, robots
```

Worlds: `precomp2025_arena`, `rcjo2025_arena`, `rcjo2026_arena`, `rcjo2026_data_collection`,
`rcw2026_arena`, `rcw2026_data_collection`, `empty` (+ `_closed` variants except `empty`).

## Download

```bash
pip install huggingface_hub
# everything
hf download team-sobits/sobits_sim_assets --repo-type dataset --local-dir export
# one world, one model, USD only (script from sobits_gazebo_worlds/scripts)
python3 download_sim_assets.py --worlds rcw2026_arena --models rcw26_shelf --formats usd --dest export
```

Pin a version with `--revision v0.1.0`. Private repos need `hf auth login` or `HF_TOKEN`.

## Use in Isaac Sim

```python
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
import omni.usd
omni.usd.get_context().open_stage("export/usd/rcw2026_arena.usda")   # has /<world>/physics
```

Each stage is Z-up, 1 m units, has a `defaultPrim` and a `UsdPhysicsScene`, so it can also be
referenced or payloaded under another prim (`/World/arena`) together with a robot USD.
Static furniture uses exact triangle-mesh colliders; dynamic objects use convex decomposition.
Lights are scaled for RTX (sun ×1000, room lights ×30000). In Isaac Lab, point `UsdFileCfg` at the `.usda`.
Articulation roots (doors) carry `physxArticulation:sleepThreshold = 0` since v0.3.0: PhysX 110.3 (Isaac Sim 6.1)
freezes the GPU articulation solver when an articulation falls asleep while a tensor-API view (ros2_control,
IMU, Isaac Lab) is active. Keep it when you edit the worlds, or use CPU dynamics.

## Use in MuJoCo

```python
import mujoco
m = mujoco.MjModel.from_xml_path("export/mjcf/rcw2026_arena/rcw2026_arena.xml")
```

Files use quaternions (no `compiler eulerseq`), so they compose with robot MJCFs via `<include>`;
`meshdir`/`texturedir` are relative to the including file, keep `assets/` next to it. Collision
meshes are CoACD convex pieces, so shelf plates are usable for placement. Plugins are not exported:
the door hinge is a plain `hinge` joint without an actuator.

## Robots

Per-robot assets (`sobit_home`, `sobit_light`) live under `usd/robots/`, `mjcf/robots/` and `robots/`:

```
usd/robots/<robot>/<robot>.usd      wrapper; references ./<robot>/<robot>_robot_*.usda (keep the folder next to it)
usd/robots/<robot>/<robot>/         package dir: payloads/ (physics variants, geometry), Textures/
mjcf/robots/<robot>/<robot>.xml     MuJoCo model, keyframe `home`
robots/<robot>.json                 provenance
```

Isaac Sim (the robot is a Z-up articulation with `defaultPrim` `/<robot>`):

```python
from isaacsim.core.utils.stage import add_reference_to_stage
add_reference_to_stage("export/usd/robots/sobit_home/sobit_home.usd", "/World/sobit_home")
```

MuJoCo:

```python
import mujoco
m = mujoco.MjModel.from_xml_path("export/mjcf/robots/sobit_home/sobit_home.xml")
d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "home"))
```

`robots/<robot>.json` records `robot_id`, the description repo (`repo`, `sha`, `describe`), the sha256 of the
`<robot>.robot.yaml` descriptor, the `urdf2usd_ros` commit, the Isaac Sim version the USD was built with (if
known), the `ros2_control` YAML path and the export date; the same blocks are collected in `MANIFEST.json` under `robots`.
The robot USD's `ROS2_Control/ControlManager.inputs:controllerConfig` holds the absolute path of that YAML on the
machine that converted it; point it at your copy (`usd/robots/<robot>/<robot>_ros2_control.yaml`) before Play.

Sources: the robot description repos ([sobit_home](https://github.com/TeamSOBITS/sobit_home),
[sobit_light](https://github.com/TeamSOBITS/sobit_light)) converted with
[urdf2usd_ros](https://github.com/TeamSOBITS/urdf2usd_ros) (USD) and `scripts/usd2mjcf.py` (MJCF).
Download only a robot: `python3 download_sim_assets.py --formats usd,mjcf --robots sobit_home`.

## Regenerate

```bash
python3 scripts/export_sim_formats.py --closed both --models   # in sobits_gazebo_worlds
python3 scripts/postprocess_usd.py export/usd                    # pxr python; PhysX-only settings (sleep)
python3 scripts/import_robot_assets.py --robot sobit_home        # robots, from urdf2usd_ros/output
python3 scripts/publish_sim_assets.py --tag vX.Y.Z
```

Converters: [gz-usd](https://github.com/MrKeith99/gz-usd/tree/feat/sobits-export) (`sdf2usd`,
OpenUSD 24.08/25.05) and [gz-mujoco](https://github.com/MrKeith99/gz-mujoco/tree/feat/sobits-export)
(`sdf2mjcf`). `MANIFEST.json` records the exact commits used.

## Known limitations

- Only diffuse (and normal, USD) textures are carried over; walls are untextured boxes by design.
- `person_walking` (Gazebo actor) is not exported.
- Legacy box models without `<inertia>` in their SDF inherit the identity tensor (see the repo README).

## License

BSD-3-Clause, same as `sobits_gazebo_worlds`. YCB and `wrc_*` models originate from
[tmc_wrs_gz](https://github.com/TeamSOBITS/tmc_wrs_gz) (Clear BSD, Toyota Motor Corporation).
Furniture meshes (`rcw26_*`) were sourced for RoboCup@Home 2026; verify their original terms before
redistributing publicly.
