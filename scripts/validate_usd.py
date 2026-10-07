#!/usr/bin/env python3
"""Validate exported USD worlds/models (pxr checks, optional Newton load).

Run with the IsaacLab venv python (pxr + newton), e.g.
  validate_usd.py export/usd --newton --json
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade, UsdUtils

TYPES = ('Xform', 'Mesh', 'Cube', 'Cylinder', 'Sphere', 'Material',
         'Shader', 'DistantLight', 'SphereLight', 'DiskLight',
         'PhysicsScene')
REVOLUTE_NEED_NO_DRIVE = ('rcw26_door', 'door_open')


def find_usd(paths):
    """Expand files/dirs into a sorted list of .usda/.usd/.usdc files."""
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(p.rglob('*.usd[ac]')) + sorted(p.rglob('*.usd'))
        else:
            out.append(p)
    return sorted(set(out))


def sdf_for(path, sdf_dir):
    """Matching expanded SDF for a world usda, or None."""
    if sdf_dir is None or 'models' in path.parts:
        return None
    cand = Path(sdf_dir) / (path.stem + '.sdf')
    return cand if cand.exists() else None


def _is_static(elem):
    return (elem.findtext('static') or '').strip().lower() in ('true', '1')


def model_static(uri, search_dirs):
    """Static flag of a model:// uri from its model.sdf, None if unknown."""
    name = uri.replace('model://', '').strip('/')
    for d in search_dirs:
        f = Path(d) / name / 'model.sdf'
        if f.exists():
            m = ET.parse(f).getroot().find('model')
            return _is_static(m) if m is not None else None
    return None


def sdf_stats(sdf, search_dirs):
    """Return ({name: is_static}, names containing '#')."""
    world = ET.parse(sdf).getroot().find('world')
    stat = {}
    for m in world.findall('model'):
        stat[m.get('name')] = _is_static(m)
    for inc in world.findall('include'):
        if inc.find('static') is not None:
            st = _is_static(inc)
        else:
            st = model_static(inc.findtext('uri') or '', search_dirs)
            st = bool(st)
        stat[inc.findtext('name')] = st
    return stat, [n for n in stat if n and '#' in n]


def has_ancestor_api(prim, api):
    p = prim.GetParent()
    while p and p.IsValid() and not p.IsPseudoRoot():
        if p.HasAPI(api):
            return True
        p = p.GetParent()
    return False


def sdf_name(prim):
    cd = prim.GetCustomData()
    return cd.get('sdf', {}).get('name') if cd else None


def check_file(path, sdf_dir=None):
    res = {'file': str(path), 'ok': True, 'counts': {}, 'failures': [],
           'info': {}}

    def fail(msg):
        res['ok'] = False
        res['failures'].append(msg)

    stage = Usd.Stage.Open(str(path))
    if not stage:
        fail('stage does not open')
        return res
    dp = stage.GetDefaultPrim()
    if not dp or not dp.IsValid():
        fail('no valid defaultPrim')
    if not stage.HasAuthoredMetadata('upAxis'):
        fail('upAxis not authored (defaults to Y)')
    elif UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        fail('upAxis != Z')
    if not stage.HasAuthoredMetadata('metersPerUnit'):
        fail('metersPerUnit not authored (defaults to 0.01)')
    elif UsdGeom.GetStageMetersPerUnit(stage) != 1:
        fail('metersPerUnit != 1 (%s)' % UsdGeom.GetStageMetersPerUnit(stage))

    counts = dict.fromkeys(TYPES, 0)
    counts.update(RigidBody=0, Joint=0, Collision=0)
    prims = [p for p in stage.Traverse()]
    layer_dir = Path(stage.GetRootLayer().realPath).parent
    collision_bad, mesh_bad, tex_bad, mat_bad, joint_bad = [], [], [], [], []
    rb_models = set()
    rb_top = rb_models
    for p in prims:
        t = p.GetTypeName()
        if t in counts:
            counts[t] += 1
        if p.IsA(UsdPhysics.Joint):
            counts['Joint'] += 1
        if p.HasAPI(UsdPhysics.RigidBodyAPI):
            counts['RigidBody'] += 1
            parts = p.GetPath().pathString.split('/')
            rb_models.add(parts[2] if len(parts) > 2 else p.GetName())
            rb_top.add(parts[2] if len(parts) > 2 else p.GetName())
        if p.HasAPI(UsdPhysics.CollisionAPI):
            counts['Collision'] += 1
            if not _is_collision_scope(p):
                collision_bad.append(str(p.GetPath()))
            if p.IsA(UsdGeom.Mesh):
                if not p.HasAPI(UsdPhysics.MeshCollisionAPI):
                    mesh_bad.append('%s: no MeshCollisionAPI' % p.GetPath())
                else:
                    a = p.GetAttribute('physics:approximation')
                    ap = a.Get() if a and a.HasValue() else 'none'
                    if ap not in ('none', 'convexDecomposition'):
                        mesh_bad.append('%s: approximation=%s'
                                        % (p.GetPath(), ap))
                    if ap == 'none' and has_ancestor_api(
                            p, UsdPhysics.RigidBodyAPI):
                        mesh_bad.append('%s: none under rigid body'
                                        % p.GetPath())
        if p.IsA(UsdShade.Shader):
            sh = UsdShade.Shader(p)
            sid = sh.GetIdAttr().Get()
            if sid == 'UsdUVTexture':
                inp = sh.GetInput('file')
                v = inp.Get() if inp else None
                if v is None:
                    tex_bad.append('%s: no inputs:file' % p.GetPath())
                else:
                    rp = Path(v.path)
                    if not rp.is_absolute():
                        rp = layer_dir / rp
                    if not rp.exists():
                        tex_bad.append('%s: missing %s'
                                       % (p.GetPath(), v.path))
        if p.IsA(UsdShade.Material):
            if p.GetName().startswith('MaterialPhysics_'):
                continue
            m = UsdShade.Material(p)
            out = m.GetSurfaceOutput()
            if not out or not out.HasConnectedSource():
                mat_bad.append(str(p.GetPath()))
        if p.IsA(UsdPhysics.RevoluteJoint):
            j = UsdPhysics.RevoluteJoint(p)
            lo, up = j.GetLowerLimitAttr(), j.GetUpperLimitAttr()
            if not (lo.HasAuthoredValue() and up.HasAuthoredValue()):
                joint_bad.append('%s: missing limits' % p.GetPath())
            d = UsdPhysics.DriveAPI.Get(p, 'angular')
            if d:
                st = d.GetStiffnessAttr().Get()
                if st:
                    joint_bad.append('%s: drive stiffness %s'
                                     % (p.GetPath(), st))
    res['counts'] = counts
    res['info']['rigid_body_models'] = len(rb_models)
    for name, lst in (('collision not under collision prim', collision_bad),
                      ('mesh collision', mesh_bad),
                      ('texture', tex_bad),
                      ('material without surface', mat_bad),
                      ('revolute joint', joint_bad)):
        if lst:
            fail('%s: %d (e.g. %s)' % (name, len(lst), lst[0]))
    res['info']['lists'] = {k: v[:20] for k, v in (
        ('collision_bad', collision_bad), ('mesh_bad', mesh_bad),
        ('tex_bad', tex_bad), ('mat_bad', mat_bad),
        ('joint_bad', joint_bad)) if v}

    # SDF comparison for worlds
    sdf = sdf_for(path, sdf_dir)
    if sdf:
        pkg = Path(sdf_dir).resolve().parent.parent
        dirs = [pkg / 'models'] + list(pkg.parent.glob('*/*/models'))
        stat, hashed = sdf_stats(sdf, dirs)
        top = {}
        for c in (dp.GetChildren() if dp and dp.IsValid() else []):
            top[sdf_name(c) or c.GetName()] = c.GetName()
        exp = sorted(n for n, st in stat.items() if not st)
        got = sorted(n for n in stat if n in top and top[n] in rb_models)
        res['info']['sdf_nonstatic_models'] = len(exp)
        if exp != got:
            fail('non-static models without RigidBodyAPI: %s; '
                 'RigidBodyAPI on SDF-static: %s' % (
                     sorted(set(exp) - set(got)),
                     sorted(set(got) - set(exp))))
        for n in stat:
            if n not in top:
                fail('SDF model %s has no USD prim' % n)
        for h in hashed:
            if not any(sdf_name(c) == h for c in (dp.GetChildren() or [])):
                fail('customData sdf:name missing for %s' % h)

    # bbox
    try:
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                                  [UsdGeom.Tokens.default_,
                                   UsdGeom.Tokens.render])
        root = dp if dp and dp.IsValid() else stage.GetPseudoRoot()
        r = cache.ComputeWorldBound(root).ComputeAlignedRange()
        if not r.IsEmpty():
            res['info']['bbox_min'] = [round(x, 3) for x in r.GetMin()]
            res['info']['bbox_max'] = [round(x, 3) for x in r.GetMax()]
            res['info']['bbox_size'] = [round(x, 3) for x in r.GetSize()]
    except Exception as e:  # pragma: no cover
        res['info']['bbox_error'] = str(e)

    # compliance
    try:
        chk = UsdUtils.ComplianceChecker(
            arkit=False, skipARKitRootLayerCheck=True, rootPackageOnly=False,
            skipVariants=False, verbose=False)
        chk.CheckCompliance(str(path))
        failed = chk.GetFailedChecks() + chk.GetErrors()
        res['info']['compliance_failed'] = sorted(set(map(_rule, failed)))
        res['info']['compliance_warnings'] = len(chk.GetWarnings())
    except Exception as e:
        # pip pxr lacks the Ndr shader parser plugins; checker aborts.
        res['info']['compliance_crash'] = str(e).strip().splitlines()[0][:80]
    return res


def _is_collision_scope(prim):
    """Collision geometry sits under a guide-purpose / collision-named xform.

    The converter marks SDF <collision> xforms purpose=guide.
    """
    for a in _chain(prim):
        if a == prim:
            continue
        pa = UsdGeom.Imageable(a).GetPurposeAttr()
        if pa and pa.HasAuthoredValue() and pa.Get() == 'guide':
            return True
        if re.search(r'col', a.GetName().lower()):
            return True
    return False


def _rule(msg):
    return re.sub(r'<[^>]*>|@[^@]*@|\d+(\.\d+)?', '#', str(msg))[:140]


def _chain(prim):
    p = prim
    while p and p.IsValid() and not p.IsPseudoRoot():
        yield p
        p = p.GetParent()


def shelf_bbox(path):
    """World bbox of visual meshes (excludes collision) in a stage."""
    stage = Usd.Stage.Open(str(path))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                              [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    box = Gf.Range3d()
    for p in stage.Traverse():
        if p.IsA(UsdGeom.Mesh) and not p.HasAPI(UsdPhysics.CollisionAPI) \
                and not any('collision' in a.GetName().lower()
                            for a in _chain(p)):
            box.UnionWith(cache.ComputeWorldBound(p).ComputeAlignedRange())
    return {'min': [round(x, 3) for x in box.GetMin()],
            'max': [round(x, 3) for x in box.GetMax()],
            'size': [round(x, 3) for x in box.GetSize()]}


def newton_check(path, steps=0):
    """Load into newton.ModelBuilder; optionally step and report angles."""
    import warnings
    import newton
    out = {'file': str(path)}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        try:
            b = newton.ModelBuilder()
            b.add_usd(str(path))
            out.update(bodies=b.body_count, shapes=b.shape_count,
                       joints=b.joint_count)
            if steps:
                out['step'] = newton_step(b, steps)
        except Exception as e:
            out['exception'] = '%s: %s' % (type(e).__name__, e)
        out['warnings'] = sorted({str(x.message)[:160] for x in w})[:10]
    return out


def newton_step(builder, steps):
    import newton
    import warp as wp
    model = builder.finalize()
    solver = newton.solvers.SolverXPBD(model)
    s0, s1 = model.state(), model.state()
    ctrl = model.control()
    contacts = model.collide(s0)
    q0 = s0.joint_q.numpy().copy()
    dt = 1.0 / 240.0
    for _ in range(steps):
        s0.clear_forces()
        solver.step(s0, s1, ctrl, contacts, dt)
        s0, s1 = s1, s0
    wp.synchronize()
    q1 = s0.joint_q.numpy()
    return {'q_before': q0.tolist(), 'q_after': q1.tolist()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('paths', nargs='+', help='usd files or directories')
    ap.add_argument('--sdf-dir', default=None,
                    help='expanded SDF dir (default: <usd dir>/../sdf)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--newton', action='store_true',
                    help='also load each file with newton.ModelBuilder')
    ap.add_argument('--newton-steps', type=int, default=0)
    ap.add_argument('--shelf', action='store_true',
                    help='print visual bbox of rcw26_shelf')
    a = ap.parse_args(argv)
    files = find_usd(a.paths)
    sdf_dir = a.sdf_dir
    if sdf_dir is None:
        for p in map(Path, a.paths):
            c = (p if p.is_dir() else p.parent).parent / 'sdf'
            if c.is_dir():
                sdf_dir = c
                break
            c = (p if p.is_dir() else p.parent) / 'sdf'
            if c.is_dir():
                sdf_dir = c
                break
    results = []
    for f in files:
        r = check_file(f, sdf_dir)
        if a.newton:
            r['newton'] = newton_check(f, a.newton_steps)
        if a.shelf and f.stem == 'rcw26_shelf':
            r['shelf_bbox'] = shelf_bbox(f)
        results.append(r)
    if a.json:
        print(json.dumps(results, indent=1, default=str))
    else:
        for r in results:
            c = r['counts']
            print('%s %s' % ('OK  ' if r['ok'] else 'FAIL', r['file']))
            print('     ' + ' '.join(
                '%s=%s' % kv for kv in c.items() if kv[1]))
            for f in r['failures']:
                print('     ! ' + f)
            if 'newton' in r:
                print('     newton: %s' % r['newton'])
    return 0 if all(r['ok'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
