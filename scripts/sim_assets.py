"""Layout of export/ and of the Hugging Face dataset that mirrors it (standard library only).

One place for the paths the export, import, publish and download scripts agree on, so it works in the ROS
python, the IsaacLab venv and the sdf2mjcf venv alike. All paths are relative to the export root:

  sdf/<world>.sdf                     expanded world SDF
  usd/<world>.usda                    world USD; textures shared by all worlds in usd/materials/
  usd/models/<model>/<model>.usda     single-model USD
  usd/robots/<robot>/<robot>.usd      robot wrapper + its package dir (import_robot_assets.py)
  mjcf/<world>/<world>.xml            world MJCF with its assets/
  mjcf/models/<model>/<model>.xml     single-model MJCF
  mjcf/robots/<robot>/<robot>.xml     robot MJCF
  robots/<robot>.json                 robot provenance
  MANIFEST.json, README.md            dataset manifest and card
"""
import subprocess
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
EXPORT_DIR = PKG / 'export'
REPO_ID = 'team-sobits/sobits_sim_assets'
CONVERTED = ('usd', 'mjcf')
FORMATS = CONVERTED + ('sdf',)
MATERIALS = 'usd/materials'
MANIFEST = 'MANIFEST.json'


def world_dir(fmt, world):
    """Directory a world's file of fmt is written to."""
    return {'usd': Path('usd'), 'mjcf': Path('mjcf') / world, 'sdf': Path('sdf')}[fmt]


def world_file(fmt, world):
    ext = {'usd': '.usda', 'mjcf': '.xml', 'sdf': '.sdf'}[fmt]
    return world_dir(fmt, world) / (world + ext)


def model_file(fmt, model):
    ext = {'usd': '.usda', 'mjcf': '.xml'}[fmt]
    return Path(fmt) / 'models' / model / (model + ext)


def robot_dir(fmt, robot):
    return Path(fmt) / 'robots' / robot


def robot_json(robot):
    return Path('robots') / ('%s.json' % robot)


def robot_patterns(robot, formats=CONVERTED):
    """Dataset patterns of one robot: its usd/mjcf dirs (per formats) and its provenance json."""
    return ['%s/*' % robot_dir(f, robot).as_posix() for f in CONVERTED if f in formats] \
        + [robot_json(robot).as_posix()]


def world_patterns(fmt, world):
    """Dataset patterns of one world in fmt, including its closed variant."""
    return {'usd': ['usd/%s*' % world],
            'mjcf': ['mjcf/%s/*' % world, 'mjcf/%s_closed/*' % world],
            'sdf': ['sdf/%s*' % world]}[fmt]


def model_patterns(fmt, model):
    return ['%s/*' % model_file(fmt, model).parent.as_posix()] if fmt in CONVERTED else []


def git(repo, *cmd):
    """stdout of `git -C repo cmd...`, None if git or the repo is missing."""
    try:
        return subprocess.run(
            ['git', '-C', str(repo), *cmd], capture_output=True, text=True,
            check=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None
