#!/usr/bin/env python3
"""Upload export/ (USD, MJCF, SDF) to a Hugging Face dataset repo.

Writes export/MANIFEST.json first. Token: env HF_TOKEN or the hf cache.
Example:
  python3 scripts/publish_sim_assets.py --tag v1 --dry-run
"""
import argparse
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

from huggingface_hub import HfApi, get_token
from huggingface_hub.utils import filter_repo_objects

PKG = Path(__file__).resolve().parent.parent
CARD = PKG / 'docs' / 'hf_dataset_card.md'
IGNORE = ['*_renders/*', '*.log', '*/__pycache__/*', '.cache/*']


def git(repo, *cmd):
    try:
        return subprocess.run(
            ['git', '-C', str(repo), *cmd], capture_output=True, text=True,
            check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def driver_command(export):
    """First 'command:' line of the newest export*.log, else 'unknown'."""
    logs = sorted(export.glob('export*.log'), key=lambda p: p.stat().st_mtime)
    for log in reversed(logs):
        for line in log.read_text(errors='replace').splitlines()[:3]:
            if line.startswith('command:'):
                return line[len('command:'):].strip()
    return 'unknown'


def select_files(export, formats):
    allow = (['%s/*' % f for f in formats]
             + ['sdf/*', 'MANIFEST.json', 'README.md'])
    files = [p.relative_to(export).as_posix()
             for p in export.rglob('*') if p.is_file()]
    return sorted(filter_repo_objects(
        files, allow_patterns=allow, ignore_patterns=IGNORE))


def build_manifest(export, files):
    models = {Path(f).parts[2] for f in files
              if f.split('/')[1:2] == ['models'] and len(Path(f).parts) > 3}
    return {
        'date': datetime.datetime.now().astimezone().isoformat(
            timespec='seconds'),
        'sobits_gazebo_worlds': {
            'describe': git(PKG, 'describe', '--always', '--dirty'),
            'sha': git(PKG, 'rev-parse', 'HEAD')},
        'gz-usd': git(PKG.parent / 'gz-usd', 'rev-parse', 'HEAD'),
        'gz-mujoco': git(PKG.parent / 'gz-mujoco', 'rev-parse', 'HEAD'),
        'command': driver_command(export),
        'worlds': len([f for f in files if f.startswith('sdf/')]),
        'models': len(models),
        'files': len(files),
        'total_bytes': sum((export / f).stat().st_size for f in files
                           if (export / f).exists()),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo-id', default='team-sobits/sobits_sim_assets')
    ap.add_argument('--export-dir', type=Path, default=PKG / 'export')
    ap.add_argument('--tag', '--revision', dest='tag',
                    help='create this tag after the upload')
    ap.add_argument('--private', action='store_true')
    ap.add_argument('--dry-run', action='store_true',
                    help='list files and sizes; no manifest, no upload')
    ap.add_argument('--formats', default='usd,mjcf')
    args = ap.parse_args(argv)
    export = args.export_dir.resolve()
    formats = [f for f in args.formats.split(',') if f]
    if not export.is_dir():
        sys.exit('error: %s does not exist' % export)

    if CARD.is_file() and not args.dry_run:
        shutil.copyfile(CARD, export / 'README.md')
    files = select_files(export, formats)
    if CARD.is_file() and 'README.md' not in files:
        files.append('README.md')  # dry-run: card is copied at upload
    manifest = build_manifest(export, files)
    for f in files:
        src = export / f if (export / f).exists() else CARD
        print('%10d  %s' % (src.stat().st_size, f))
    print('%d files, %.1f MB -> %s' % (
        len(files), manifest['total_bytes'] / 1e6, args.repo_id))
    print(json.dumps(manifest, indent=2))
    if args.dry_run:
        return 0

    token = get_token()
    if not token:
        sys.exit('error: no Hugging Face token; set HF_TOKEN or run '
                 '`hf auth login`')
    (export / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2))
    api = HfApi(token=token)
    api.create_repo(args.repo_id, repo_type='dataset', exist_ok=True,
                    private=args.private)
    api.upload_large_folder(
        repo_id=args.repo_id, repo_type='dataset', folder_path=export,
        allow_patterns=['%s/*' % f for f in formats + ['sdf']]
        + ['MANIFEST.json', 'README.md'], ignore_patterns=IGNORE)
    if args.tag:
        api.create_tag(args.repo_id, tag=args.tag, repo_type='dataset')
    print('uploaded: https://huggingface.co/datasets/%s' % args.repo_id)
    return 0


if __name__ == '__main__':
    sys.exit(main())
