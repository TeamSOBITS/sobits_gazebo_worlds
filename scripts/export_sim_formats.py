#!/usr/bin/env python3
"""Export sobits_gazebo_worlds worlds/models to USD (Isaac Sim) and MJCF.

Expands each world xacro to SDF, then runs sdf2usd / sdf2mjcf as
subprocesses (binaries from env SDF2USD_BIN / SDF2MJCF_BIN). If env
USD_PATH is set, $USD_PATH/lib is prepended to LD_LIBRARY_PATH for sdf2usd
(e.g. USD_PATH=/opt/openusd-24.08). sdf2mjcf gets --use-quat,
--plane-as-box and --convex-decomposition (CoACD) unless disabled.

Usage:
  USD_PATH=/opt/openusd-24.08 \\
  SDF2USD_BIN=<colcon_ws>/src/gz-usd/build/bin/sdf2usd \\
  SDF2MJCF_BIN=~/venvs/sdf2mjcf/bin/sdf2mjcf \\
  python3 scripts/export_sim_formats.py --closed both --models --out export

Selection examples:
  --formats usd                         only USD
  --formats mjcf                        only MJCF
  --no-worlds --models rcw26_shelf rcw26_door    two models only
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_utils import (  # noqa: E402
    EXTERNAL_WORLDS, build_gz_resource_path, expand_world, resolve_world_path)

PKG = Path(__file__).resolve().parent.parent
FORMATS = ('usd', 'mjcf')
LINTED = set()  # (model, link) pairs already reported


def resource_dirs():
    """Model dirs: this package, tmc_wrs_gz_worlds, gz_human_sim."""
    dirs = [Path(p) for p in build_gz_resource_path(str(PKG)).split(os.pathsep)
            if p and Path(p).is_dir()]
    human = PKG.parent / 'gz_human_sim' / 'models'
    if human.is_dir():
        dirs.append(human)
    # Dedupe in order; GZ_SIM_RESOURCE_PATH entries are already included.
    return list(dict.fromkeys(d.resolve() for d in dirs))


def default_worlds():
    names = sorted(p.name[:-len('.world.xacro')]
                   for p in (PKG / 'worlds').glob('*.world.xacro'))
    return names + ['empty']


def world_file(name):
    if name in EXTERNAL_WORLDS or os.path.isabs(name):
        return Path(resolve_world_path(name))
    for ext in ('.world.xacro', '.world', '.sdf'):
        cand = PKG / 'worlds' / (name if name.endswith(ext) else name + ext)
        if cand.exists():
            return cand
    sys.exit('error: world not found: %s' % name)


def model_sdf(model_dir):
    """SDF file declared in model.config, else model.sdf."""
    try:
        for tag in ET.parse(model_dir / 'model.config').getroot().iter('sdf'):
            if tag.text and (model_dir / tag.text.strip()).is_file():
                return model_dir / tag.text.strip()
    except (ET.ParseError, OSError):
        pass
    cand = model_dir / 'model.sdf'
    return cand if cand.is_file() else None


def is_static(model, inherited=False):
    tag = model.find('static')
    if tag is None or not (tag.text or '').strip():
        return inherited
    return tag.text.strip().lower() in ('true', '1')


def lint_inertia(sdf, paths):
    """Warn about non-static links with a missing or partial <inertial>.

    Includes resolve to their own model file; LINTED dedupes across runs.
    """
    try:
        root = ET.parse(sdf).getroot()
    except (ET.ParseError, OSError):
        return

    def check(model, static):
        static = is_static(model, static)
        name = model.get('name', '?')
        for link in model.findall('link'):
            inertial = link.find('inertial')
            key = (name, link.get('name'))
            if static or key in LINTED:
                continue
            LINTED.add(key)
            if inertial is None:
                why = 'no <inertial>; mass 1 kg, identity tensor assumed'
            elif (inertial.find('mass') is not None
                  and inertial.find('inertia') is None):
                why = 'mass without <inertia>; identity tensor assumed'
            else:
                continue
            print('WARNING: %s link %s: %s (unrealistic dynamics)'
                  % (name, link.get('name'), why))
        for child in model.findall('model'):
            check(child, static)

    for parent in [root] + list(root.iter('world')):
        for model in parent.findall('model'):
            check(model, False)
    for inc in root.iter('include'):
        uri = (inc.findtext('uri') or '').strip()
        if not uri.startswith('model://'):
            continue
        for d in paths:
            inc_sdf = model_sdf(d / uri[len('model://'):])
            if inc_sdf is None:
                continue
            if inc.find('static') is not None and is_static(inc):
                break
            lint_inertia(inc_sdf, paths)
            break


def converter_cmd(fmt, paths, src, dst, args):
    if fmt == 'usd':
        cmd = [os.environ.get('SDF2USD_BIN', 'sdf2usd')]
    else:
        cmd = [os.environ.get('SDF2MJCF_BIN', 'sdf2mjcf'), '--use-quat']
        if not args.no_plane_as_box:
            cmd.append('--plane-as-box')
        if not args.no_convex_decomposition:
            cmd.append('--convex-decomposition')
        if args.coacd_threshold is not None:
            cmd += ['--coacd-threshold', str(args.coacd_threshold)]
        if args.mesh_inertia_shell:
            cmd.append('--mesh-inertia-shell')
    for p in paths:
        cmd += ['--model-path', str(p)]
    return cmd + [str(src), str(dst)]


def run(cmd, cwd, env, dry):
    """Run one conversion; return (ok, seconds)."""
    print('$ (cd %s && %s)' % (cwd, ' '.join(cmd)), flush=True)
    if dry:
        return True, 0.0
    cwd.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    try:
        ok = subprocess.run(cmd, cwd=cwd, env=env).returncode == 0
    except OSError as err:
        print('error: %s' % err, file=sys.stderr)
        ok = False
    return ok, time.monotonic() - start


def convert(name, src, args, out, paths, env, results, model=False):
    """Convert src SDF into each format under out; append result rows."""
    for fmt in args.formats:
        if model:
            usd_dir = out / 'usd' / 'models' / name
            mjcf_dir = out / 'mjcf' / 'models' / name
        else:
            usd_dir = out / 'usd'
            mjcf_dir = out / 'mjcf' / name
        dst = (usd_dir / (name + '.usda') if fmt == 'usd'
               else mjcf_dir / (name + '.xml'))
        cmd = converter_cmd(fmt, paths, src, dst, args)
        cenv = env
        if fmt == 'usd' and os.environ.get('USD_PATH'):
            lib = os.path.join(os.environ['USD_PATH'], 'lib')
            cenv = dict(env, LD_LIBRARY_PATH=os.pathsep.join(
                filter(None, [lib, env.get('LD_LIBRARY_PATH', '')])))
        ok, secs = run(cmd, dst.parent, cenv, args.dry_run)
        results.append((name, fmt, ok, secs))


def export_world(name, closed, args, out, paths, env, results):
    path = world_file(name)
    tag = name + ('_closed' if closed else '')
    start = time.monotonic()
    xacro_args = {'closed': 'true'} if closed else {}
    expanded = Path(expand_world(str(path), xacro_args))
    if str(path).endswith('.xacro') and expanded == path:
        print('error: xacro expansion failed for %s' % path, file=sys.stderr)
        results.append((tag, 'sdf', False, time.monotonic() - start))
        return
    sdf = out / 'sdf' / (tag + '.sdf')
    sdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(expanded, sdf)
    if expanded != path:
        os.unlink(expanded)
    results.append((tag, 'sdf', True, time.monotonic() - start))
    lint_inertia(sdf, paths)
    print('expanded %s -> %s' % (path.name, sdf), flush=True)
    convert(tag, sdf, args, out, paths, env, results)
    if args.keep_sdf:
        for fmt in args.formats:
            d = out / fmt / (tag if fmt == 'mjcf' else '')
            if not args.dry_run:
                shutil.copyfile(sdf, d / sdf.name)


def export_models(args, out, paths, env, results):
    for mdir in sorted(p for p in (PKG / 'models').iterdir() if p.is_dir()):
        if args.models and mdir.name not in args.models:
            continue
        sdf = model_sdf(mdir)
        if sdf is None:
            results.append((mdir.name, 'sdf', False, 0.0))
            continue
        lint_inertia(sdf, paths)
        convert(mdir.name, sdf, args, out, paths, env, results, model=True)


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--worlds', nargs='+', metavar='NAME',
                    help='worlds to export (default: all in worlds/)')
    ap.add_argument('--closed', choices=('false', 'true', 'both'),
                    default='false', help="xacro 'closed' arg")
    ap.add_argument('--formats', default='usd,mjcf',
                    help='comma list of usd,mjcf')
    ap.add_argument('--models', nargs='*', metavar='NAME',
                    help='also export models/ dirs: all if no NAME given')
    ap.add_argument('--no-worlds', action='store_true',
                    help='skip worlds (use with --models)')
    ap.add_argument('--mesh-inertia-shell', action='store_true',
                    help='pass --mesh-inertia-shell to sdf2mjcf; '
                    'needs MuJoCo >= 3.2.5')
    ap.add_argument('--no-plane-as-box', action='store_true',
                    help='do not pass --plane-as-box to sdf2mjcf')
    ap.add_argument('--no-convex-decomposition', action='store_true',
                    help='do not pass --convex-decomposition (CoACD) to '
                    'sdf2mjcf')
    ap.add_argument('--coacd-threshold', type=float, metavar='F',
                    help='forward --coacd-threshold F to sdf2mjcf')
    ap.add_argument('--out', type=Path, default=PKG / 'export')
    ap.add_argument('--dry-run', action='store_true',
                    help='print converter commands; only expand xacro')
    ap.add_argument('--keep-sdf', action='store_true',
                    help='also copy the expanded SDF next to the outputs')
    args = ap.parse_args(argv)
    unknown = [m for m in args.models or []
               if not (PKG / 'models' / m).is_dir()]
    if unknown:
        ap.error('unknown model(s): %s' % ', '.join(unknown))
    args.formats = [f for f in args.formats.split(',') if f]
    bad = [f for f in args.formats if f not in FORMATS]
    if bad:
        ap.error('unknown format(s): %s' % ', '.join(bad))
    return args


def main(argv=None):
    args = parse_args(argv)
    out = args.out.resolve()
    paths = resource_dirs()
    env = dict(os.environ)
    joined = os.pathsep.join(str(p) for p in paths)
    for var in ('SDF_PATH', 'GZ_SIM_RESOURCE_PATH'):
        env[var] = os.pathsep.join(filter(None, [joined, env.get(var, '')]))
    print('command: ' + ' '.join(['export_sim_formats.py'] + sys.argv[1:]))
    print('resource dirs:\n  ' + '\n  '.join(map(str, paths)))

    results = []
    states = {'false': [False], 'true': [True], 'both': [False, True]}
    for name in [] if args.no_worlds else args.worlds or default_worlds():
        has_arg = 'name="closed"' in world_file(name).read_text()
        for closed in states[args.closed]:
            if closed and not has_arg:  # e.g. empty.world: no closed variant
                continue
            export_world(name, closed, args, out, paths, env, results)
    if args.models is not None:
        export_models(args, out, paths, env, results)

    print('\n%-36s %-5s %-5s %8s' % ('target', 'fmt', 'ok', 'seconds'))
    for name, fmt, ok, secs in results:
        status = 'ok' if ok else 'FAIL'
        print('%-36s %-5s %-5s %8.1f' % (name, fmt, status, secs))
    return 0 if all(r[2] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
