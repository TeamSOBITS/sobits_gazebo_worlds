#!/usr/bin/env python3
"""Copy urdf2usd_ros robot USD / MJCF into export/ and write provenance.

Layout: export/usd/robots/<robot>/<robot>.usd + <robot>/ (package dir)
+ <robot>_ros2_control.yaml (controller_manager config the USD's ROS2_Control graph loads),
export/mjcf/robots/<robot>/<robot>.xml, export/robots/<robot>.json.
Example (IsaacLab venv python gives pxr for the reference check):
  python3 scripts/import_robot_assets.py --robot sobit_home
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

PKG = Path(__file__).resolve().parent.parent
SRC = PKG.parent


def git(repo, *cmd):
    try:
        return subprocess.run(
            ['git', '-C', str(repo), *cmd], capture_output=True, text=True,
            check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def find_descriptor(robot, description_dir):
    """Path of <robot>.robot.yaml (sobits_robot_descriptor, else glob)."""
    if description_dir:
        hits = sorted(Path(description_dir).rglob('%s.robot.yaml' % robot))
        return hits[0] if hits else None
    try:
        sys.path.append(str(SRC / 'sobits_robot_descriptor'))
        from sobits_robot_descriptor import resolve_path
        return Path(resolve_path(robot))
    except Exception:  # not importable / not installed: scan src/
        hits = sorted(SRC.glob('*/*_description/config/%s.robot.yaml' % robot))
        return hits[0] if hits else None


def isaac_version(usd):
    """Isaac Sim version from a content URL in the layer, else None."""
    try:
        from pxr import Sdf, Usd  # noqa: F401 (registers formats)
        text = Sdf.Layer.FindOrOpen(str(usd)).ExportToString()
    except Exception:
        return None
    m = re.search(r'Assets/Isaac/(\d+\.\d+(?:\.\d+)?)/', text)
    return m.group(1) if m else None


def get_mjcf_refs(mjcf):
    """Parse MJCF file, extract referenced asset file paths."""
    refs = set()
    try:
        tree = ET.parse(mjcf)
        root = tree.getroot()
        # meshdir, texturedir, assetdir attributes
        for attr in ('meshdir', 'texturedir', 'assetdir'):
            v = root.get(attr)
            if v:
                refs.add(v)
        # file="..." attributes in mesh, texture, hfield, skin, include
        for elem in root.iter():
            f = elem.get('file')
            if f:
                refs.add(f)
    except Exception as e:
        print(f'warning: failed to parse MJCF {mjcf}: {e}')
    return refs


def copy_mjcf_with_refs(mjcf, dest, robot):
    """Copy MJCF and only the files it references."""
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    shutil.copyfile(mjcf, dest / ('%s.xml' % robot))
    refs = get_mjcf_refs(mjcf)
    if not refs:
        return  # all meshes inlined, just the XML
    # Copy each referenced file preserving relative path
    for ref in refs:
        ref_path = mjcf.parent / ref
        if not ref_path.exists():
            sys.exit(f'error: referenced file missing: {ref} (from {mjcf})')
        dest_ref = dest / ref
        dest_ref.parent.mkdir(parents=True, exist_ok=True)
        if ref_path.is_dir():
            shutil.copytree(ref_path, dest_ref)
        else:
            shutil.copyfile(ref_path, dest_ref)


def copy_usd(usd, pkg_dir, dest, robot):
    """Copy wrapper + package dir; keep references resolvable."""
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    shutil.copyfile(usd, dest / usd.name)
    if pkg_dir.is_dir():
        shutil.copytree(pkg_dir, dest / pkg_dir.name)
    try:
        from pxr import Sdf, Usd  # noqa: F401 (registers formats)
    except ImportError:
        print('warning: pxr missing, reference check skipped')
        return
    layer = Sdf.Layer.FindOrOpen(str(dest / usd.name))
    bad = []

    def walk(spec):
        for child in spec.nameChildren:
            walk(child)
        for lst in (spec.referenceList, spec.payloadList):
            for item in lst.GetAddedOrExplicitItems():
                p = item.assetPath
                if p and '://' not in p and not (dest / p).exists():
                    bad.append((spec.path, p))
    walk(layer.pseudoRoot)
    if bad:
        sys.exit('error: unresolvable references after copy: %s' % bad[:3])


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--robot', required=True)
    ap.add_argument('--usd', type=Path,
                    help='wrapper .usd (default <source-dir>/<robot>.usd)')
    ap.add_argument('--mjcf', type=Path,
                    help='MJCF .xml (default <source-dir>/<robot>.xml)')
    ap.add_argument('--source-dir', type=Path,
                    default=SRC / 'urdf2usd_ros' / 'output')
    ap.add_argument('--description-dir', type=Path,
                    help='robot description package (default: descriptor)')
    ap.add_argument('--export-dir', type=Path, default=PKG / 'export')
    args = ap.parse_args(argv)
    robot, export = args.robot, args.export_dir.resolve()
    usd = (args.usd or args.source_dir / ('%s.usd' % robot)).resolve()
    mjcf = (args.mjcf or args.source_dir / ('%s.xml' % robot)).resolve()
    if not usd.is_file() and not mjcf.is_file():
        sys.exit('error: neither %s nor %s exists' % (usd, mjcf))

    prov = {'robot_id': robot}
    if usd.is_file():
        copy_usd(usd, usd.parent / usd.stem,
                 export / 'usd' / 'robots' / robot, robot)
        prov['usd'] = 'usd/robots/%s/%s' % (robot, usd.name)
        prov['isaac_sim'] = isaac_version(usd)
        print('usd:  %s' % prov['usd'])
        yaml = usd.parent / ('%s_ros2_control.yaml' % robot)
        if yaml.is_file():
            shutil.copyfile(yaml, export / 'usd' / 'robots' / robot / yaml.name)
            prov['ros2_control'] = 'usd/robots/%s/%s' % (robot, yaml.name)
            print('ros2_control: %s (the USD bakes the absolute source path; '
                  'retarget ControlManager.inputs:controllerConfig on other machines)' % prov['ros2_control'])
    else:
        print('warning: %s missing, USD skipped' % usd)
    if mjcf.is_file():
        d = export / 'mjcf' / 'robots' / robot
        copy_mjcf_with_refs(mjcf, d, robot)
        prov['mjcf'] = 'mjcf/robots/%s/%s.xml' % (robot, robot)
        print('mjcf: %s' % prov['mjcf'])
    else:
        print('warning: %s missing, MJCF skipped' % mjcf)

    desc = find_descriptor(robot, args.description_dir)
    if desc and desc.is_file():
        pkg = desc.parent.parent
        prov['description'] = {
            'package': pkg.name,
            'repo': git(pkg, 'remote', 'get-url', 'origin'),
            'sha': git(pkg, 'rev-parse', 'HEAD'),
            'describe': git(pkg, 'describe', '--always', '--dirty'),
            'descriptor': desc.name,
            'descriptor_sha256': hashlib.sha256(
                desc.read_bytes()).hexdigest()}
    else:
        print('warning: descriptor for %s not found (--description-dir)'
              % robot)
    u2u = SRC / 'urdf2usd_ros'
    prov['urdf2usd_ros'] = {'sha': git(u2u, 'rev-parse', 'HEAD'),
                            'describe': git(u2u, 'describe', '--always',
                                            '--dirty')}
    prov['date'] = datetime.datetime.now().astimezone().isoformat(
        timespec='seconds')
    out = export / 'robots' / ('%s.json' % robot)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(prov, indent=2) + '\n')
    print('provenance: %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
