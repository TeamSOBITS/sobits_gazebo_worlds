#!/usr/bin/env python3
"""Author Isaac Sim (PhysX) settings the SDF converter cannot express.

Currently: physxArticulation:sleepThreshold = 0 on every articulation root. PhysX 110.3 (Isaac Sim 6.1)
spins a GPU articulation kernel forever when an articulation falls asleep while a tensor-API view is active
(ros2_control, IMU, Isaac Lab); see urdf2usd_ros/docs/isaac_gpu_articulation_sleep_stall.md.
Idempotent; run with a pxr python (IsaacLab venv) after export_sim_formats.py:
  python3 scripts/postprocess_usd.py export/usd
"""
import argparse
import sys
from pathlib import Path

from pxr import Sdf, Usd, UsdPhysics

SLEEP_ATTR = 'physxArticulation:sleepThreshold'


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


def process(path, dry_run=False):
    stage = Usd.Stage.Open(str(path))
    if not stage:
        print('error: cannot open %s' % path, file=sys.stderr)
        return None
    changed = disable_articulation_sleep(stage)
    if changed and not dry_run:
        stage.GetRootLayer().Save()
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='+', help='usd files or directories')
    ap.add_argument('--dry-run', action='store_true', help='report only, do not save')
    a = ap.parse_args(argv)
    failed = 0
    for f in find_usd(a.paths):
        changed = process(f, a.dry_run)
        if changed is None:
            failed += 1
        elif changed:
            print('%s: sleep disabled on %d articulation(s)' % (f, len(changed)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
