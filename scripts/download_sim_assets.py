#!/usr/bin/env python3
"""Download exported USD / MJCF / SDF assets from a Hugging Face dataset.

Public repos need no token; HF_TOKEN is used if set. Examples:
  python3 scripts/download_sim_assets.py --formats usd
  python3 scripts/download_sim_assets.py --worlds rcw2026_arena \\
      --models rcw26_shelf
"""
import argparse
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

PKG = Path(__file__).resolve().parent.parent
FORMATS = ('usd', 'mjcf', 'sdf')


def patterns(formats, worlds, models):
    """allow_patterns narrowing formats to the given worlds/models."""
    if not worlds and not models:
        return ['%s/*' % f for f in formats] + ['MANIFEST.json']
    pats = ['MANIFEST.json']
    for fmt in formats:
        if fmt == 'usd' and worlds:  # shared textures of all world USDs
            pats.append('usd/materials/*')
        for w in worlds:  # mjcf assets live in mjcf/<w>/assets/
            pats += {'usd': ['usd/%s*' % w],
                     'mjcf': ['mjcf/%s/*' % w, 'mjcf/%s_closed/*' % w],
                     'sdf': ['sdf/%s*' % w]}[fmt]
        if fmt != 'sdf':
            pats += ['%s/models/%s/*' % (fmt, m) for m in models]
    return pats


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo-id', default='team-sobits/sobits_sim_assets')
    ap.add_argument('--revision', default='main')
    ap.add_argument('--dest', type=Path, default=PKG / 'export')
    ap.add_argument('--formats', default='usd,mjcf,sdf',
                    help='comma list of usd,mjcf,sdf')
    ap.add_argument('--worlds', nargs='+', default=[], metavar='NAME')
    ap.add_argument('--models', nargs='+', default=[], metavar='NAME')
    ap.add_argument('--show-patterns', action='store_true',
                    help='print the allow_patterns and exit')
    ap.add_argument('--force', action='store_true',
                    help='overwrite existing files')
    args = ap.parse_args(argv)
    formats = [f for f in args.formats.split(',') if f]
    bad = [f for f in formats if f not in FORMATS]
    if bad:
        ap.error('unknown format(s): %s' % ', '.join(bad))

    pats = patterns(formats, args.worlds, args.models)
    if args.show_patterns:
        print('\n'.join(pats))
        return 0
    dest = snapshot_download(
        repo_id=args.repo_id, repo_type='dataset', revision=args.revision,
        local_dir=args.dest, force_download=args.force,
        allow_patterns=pats)
    root = Path(dest)
    files = [p for p in root.rglob('*')
             if p.is_file() and '.cache' not in p.parts]
    print('downloaded to %s' % root)
    for fmt in formats:
        sub = [p for p in files if p.relative_to(root).parts[0] == fmt]
        print('  %-5s %4d files, %7.1f MB' % (
            fmt, len(sub), sum(p.stat().st_size for p in sub) / 1e6))
    return 0


if __name__ == '__main__':
    sys.exit(main())
