#!/usr/bin/env python3
"""Validate exported MJCF files: load, static checks, stepping, renders."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import mujoco


def collect_xmls(paths):
    """Expand dirs into xml files, skipping _renders and person_walking."""
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(x for x in p.rglob('*.xml')
                          if '_renders' not in x.parts
                          and x.stem == x.parent.name)
        else:
            out.append(p)
    return [x for x in out if x.stem != 'person_walking']


def static_checks(path):
    """Return a list of text/asset problems found in the XML."""
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    issues = []
    text = Path(path).read_text()
    if re.search(r'\beuler=', text):
        issues.append('euler attribute present')
    for c in root.iter('compiler'):
        if 'eulerseq' in c.attrib:
            issues.append('compiler eulerseq present')
    comp = next(root.iter('compiler'), None)
    mdir = comp.get('meshdir', '') if comp is not None else ''
    tdir = comp.get('texturedir', '') if comp is not None else ''
    base = Path(path).parent
    for el in root.iter():
        f = el.get('file')
        if not f or el.tag in ('include', 'mujoco'):
            continue
        d = {'mesh': mdir, 'texture': tdir}.get(el.tag, '')
        if not (base / d / f).exists() and not (base / f).exists():
            issues.append(f'missing {el.tag} file {f}')
    return issues


def check(path, steps):
    """Load, step and inspect one model; return result dict."""
    r = {'file': str(path), 'ok': False, 'issues': static_checks(path)}
    try:
        m = mujoco.MjModel.from_xml_path(str(path))
    except Exception as e:  # noqa: BLE001
        r['error'] = str(e)[:300]
        return r
    d = mujoco.MjData(m)
    r.update(nbody=m.nbody, ngeom=m.ngeom, nmesh=m.nmesh, ntex=m.ntex,
             njnt=m.njnt, nq=m.nq)
    for _ in range(steps):
        mujoco.mj_step(m, d)
    warns = {mujoco.mjtWarning(i).name: int(d.warning[i].number)
             for i in range(len(d.warning)) if d.warning[i].number > 0}
    r['warnings'] = warns
    planes = [m.geom_pos[g][2] for g in range(m.ngeom)
              if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE]
    zthr = (min(planes) - 1.0) if planes else -1.0
    zthr = min(zthr, -1.0)
    r['fell'] = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b)
                 for b in range(1, m.nbody) if d.xpos[b][2] < zthr]
    bad = []
    for g in range(m.ngeom):
        if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
            a = m.geom_aabb[g]
            if not np.all(np.isfinite(a)) or np.any(a[3:] <= 0):
                bad.append(g)
    r['bad_aabb'] = len(bad)
    r['ok'] = not (r['issues'] or warns or r['fell'] or bad)
    return r


def render(path, out_dir):
    """Render a 640x480 PNG from above-front at ~8 m."""
    import imageio.v3 as iio
    m = mujoco.MjModel.from_xml_path(str(path))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    rend = mujoco.Renderer(m, 480, 640)
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    geoms = [g for g in range(m.ngeom)
             if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_PLANE]
    pts = d.geom_xpos[geoms] if geoms else np.zeros((1, 3))
    lo, hi = pts.min(0), pts.max(0)
    cam.lookat[:] = (lo + hi) / 2
    ext = float(np.linalg.norm(hi - lo))
    cam.distance = 8.0 if ext > 4 else max(2.5, ext * 2.0)
    cam.azimuth, cam.elevation = 90.0, -40.0
    rend.update_scene(d, cam)
    img = rend.render()
    rend.close()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    png = Path(out_dir) / (Path(path).stem + '.png')
    iio.imwrite(png, img)
    return str(png), float(img.std())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('paths', nargs='+', help='xml files or directories')
    ap.add_argument('--steps', type=int, default=1000)
    ap.add_argument('--render', metavar='DIR', help='write PNGs here')
    ap.add_argument('--render-only', nargs='*', default=None,
                    help='stems to render (default: all given)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    print('mujoco', mujoco.__version__, 'GL', os.environ.get('MUJOCO_GL'))
    rc = 0
    for x in collect_xmls(a.paths):
        r = check(x, a.steps)
        if a.render and (a.render_only is None or x.stem in a.render_only):
            try:
                r['png'], r['img_std'] = render(x, a.render)
            except Exception as e:  # noqa: BLE001
                r['render_error'] = str(e)[:200]
        print(json.dumps(r) if a.json else
              f"{'OK  ' if r['ok'] else 'FAIL'} {x.name} {r}")
        rc |= not r['ok']
    return rc


if __name__ == '__main__':
    sys.exit(main())
