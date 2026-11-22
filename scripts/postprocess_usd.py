#!/usr/bin/env python3
"""Author Isaac Sim (PhysX) settings the SDF converter cannot express.

- physxArticulation:sleepThreshold = 0 on every articulation root. PhysX 110.3 (Isaac Sim 6.1) spins a GPU
  articulation kernel forever when an articulation falls asleep while a tensor-API view is active
  (ros2_control, IMU, Isaac Lab); see urdf2usd_ros/docs/isaac_gpu_articulation_sleep_stall.md.
- floor_plane* tiles and ground_plane are visual only; one infinite collision plane at their top carries the
  robots. A 100 m box (empty world) lifts cylinder wheels 2 cm off its surface; Isaac Lab trains on a plane.
- a sky DomeLight on worlds (stages with a DistantLight sun, none yet): without one the background renders black
  and shadowed sides go dark; Gazebo draws its own sky.
Idempotent; run with a pxr python (IsaacLab venv) after export_sim_formats.py:
  python3 scripts/postprocess_usd.py export/usd
"""
import argparse
import sys
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

SLEEP_ATTR = 'physxArticulation:sleepThreshold'
FLOOR_PREFIXES = ('floor_plane', 'ground_plane')
FLOOR_COLLIDER = 'floor_collision'
SKY = 'sky'
SKY_COLOR = (0.62, 0.75, 0.92)  # clear daytime blue; untextured, so no asset download
SKY_INTENSITY = 600.0


def find_usd(paths):
    out = []
    for p in map(Path, paths):
        out += sorted(p.rglob('*.usd[ac]')) + sorted(p.rglob('*.usd')) if p.is_dir() else [p]
    return sorted(set(out))


def disable_articulation_sleep(stage):
    """Apply PhysxArticulationAPI + sleepThreshold 0 on articulation roots; return changed prim paths."""
    changed = []
    for prim in stage.Traverse():
        if not prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            continue
        attr = prim.GetAttribute(SLEEP_ATTR)
        lo = prim.GetMetadata('apiSchemas')  # unregistered tokens are dropped by GetAppliedSchemas()
        if attr and attr.Get() == 0.0 and lo and 'PhysxArticulationAPI' in lo.GetAddedOrExplicitItems():
            continue
        # The schema is not registered outside Kit, so author the token and the attribute by name.
        prim.AddAppliedSchema('PhysxArticulationAPI')
        prim.CreateAttribute(SLEEP_ATTR, Sdf.ValueTypeNames.Float).Set(0.0)
        changed.append(prim.GetPath().pathString)
    return changed


def visual_only_floor(stage):
    """Disable the floor prims' collisions and add one collision plane at their top; return changed paths."""
    root = stage.GetDefaultPrim()
    if not root:
        return []
    tiles = [p for p in root.GetChildren() if p.GetName().startswith(FLOOR_PREFIXES)]
    colliders = [p for t in tiles for p in Usd.PrimRange(t) if p.HasAPI(UsdPhysics.CollisionAPI)]
    plane_path = root.GetPath().AppendChild(FLOOR_COLLIDER)
    if not colliders or stage.GetPrimAtPath(plane_path):
        return []
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.guide])
    top = max(cache.ComputeWorldBound(p).ComputeAlignedRange().GetMax()[2] for p in colliders)
    binding = UsdShade.MaterialBindingAPI(colliders[0])
    # gz-usd binds the physics material without a purpose
    material = binding.GetDirectBinding('physics').GetMaterial() or binding.GetDirectBinding().GetMaterial()
    for p in colliders:
        UsdPhysics.CollisionAPI(p).CreateCollisionEnabledAttr().Set(False)
    plane = UsdGeom.Plane.Define(stage, plane_path)
    plane.CreateAxisAttr(UsdGeom.Tokens.z)
    plane.CreatePurposeAttr(UsdGeom.Tokens.guide)
    UsdGeom.XformCommonAPI(plane).SetTranslate((0.0, 0.0, top))
    UsdPhysics.CollisionAPI.Apply(plane.GetPrim())
    if material:
        UsdShade.MaterialBindingAPI.Apply(plane.GetPrim()).Bind(
            material, UsdShade.Tokens.weakerThanDescendants, 'physics')
    return [p.GetPath().pathString for p in colliders] + [plane_path.pathString]


def add_sky(stage):
    """Define <defaultPrim>/sky DomeLight on a world with a sun and no dome; return its path or None."""
    lights = [p for p in stage.Traverse() if p.IsA(UsdLux.DistantLight) or p.IsA(UsdLux.DomeLight)]
    if not any(p.IsA(UsdLux.DistantLight) for p in lights) or any(p.IsA(UsdLux.DomeLight) for p in lights):
        return None
    root = stage.GetDefaultPrim()
    dome = UsdLux.DomeLight.Define(stage, root.GetPath().AppendChild(SKY))
    dome.CreateColorAttr(Gf.Vec3f(*SKY_COLOR))
    dome.CreateIntensityAttr(SKY_INTENSITY)
    return dome.GetPath().pathString


def process(path, dry_run=False):
    stage = Usd.Stage.Open(str(path))
    if not stage:
        print('error: cannot open %s' % path, file=sys.stderr)
        return None
    changed = disable_articulation_sleep(stage)
    floor = visual_only_floor(stage)
    sky = add_sky(stage)
    if (changed or floor or sky) and not dry_run:
        stage.GetRootLayer().Save()
    return changed, floor, sky


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='+', help='usd files or directories')
    ap.add_argument('--dry-run', action='store_true', help='report only, do not save')
    a = ap.parse_args(argv)
    failed = 0
    for f in find_usd(a.paths):
        result = process(f, a.dry_run)
        if result is None:
            failed += 1
            continue
        changed, floor, sky = result
        if changed:
            print('%s: sleep disabled on %d articulation(s)' % (f, len(changed)))
        if floor:
            print('%s: floor visual only, %d tile collider(s) off, plane %s' % (f, len(floor) - 1, floor[-1]))
        if sky:
            print('%s: sky dome %s' % (f, sky))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
