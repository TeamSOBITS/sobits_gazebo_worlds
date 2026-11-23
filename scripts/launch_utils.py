import os
import re
import subprocess
import tempfile

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


# Short aliases for worlds that do NOT live in sobits_gazebo_worlds/worlds.
# Each maps to (package_name, relative_path_under_share).
EXTERNAL_WORLDS = {
    'wrs':         ('tmc_wrs_gz_worlds',      'worlds/wrs2020.world.xacro'),
    'small_house': ('aws_small_house_world',  'worlds/small_house.world'),
}


def resolve_world_path(world):
    """Turn a `world` argument into an absolute world-file path.

    Accepts an absolute path, an EXTERNAL_WORLDS alias, or a bare name /
    filename under sobits_gazebo_worlds/worlds (bare names try '.world.xacro',
    then '.world', then '.sdf'). Unknown names fall back to 'empty', as
    sobit_home_bringup's world_model did before this moved here.
    """
    if os.path.isabs(world):
        return world

    if world in EXTERNAL_WORLDS:
        package, relative = EXTERNAL_WORLDS[world]
        return os.path.join(get_package_share_directory(package), relative)

    worlds_dir = os.path.join(
        get_package_share_directory('sobits_gazebo_worlds'), 'worlds')

    if world.endswith(('.world.xacro', '.world', '.sdf')):
        filenames = [world]
    else:
        filenames = [world + ext for ext in ('.world.xacro', '.world', '.sdf')]

    for filename in filenames:
        candidate = os.path.join(worlds_dir, filename)
        if os.path.exists(candidate):
            return candidate

    return os.path.join(worlds_dir, 'empty.world')


def gz_world_name(path):
    """Read the <world name='...'> attribute from an SDF/xacro world file.

    Regex rather than an XML parse: every shipped world declares the name as a
    literal, so this works on unexpanded xacro too. Falls back to 'default',
    which is what Gazebo itself uses.
    """
    try:
        with open(path) as f:
            m = re.search(r"<world\s+name=['\"]([^'\"]+)['\"]", f.read())
    except OSError:
        return 'default'
    return m.group(1) if m else 'default'


def expand_world(path, xacro_args=None):
    """Run xacro on a world file and return the path to the expanded SDF.

    gz sim parses its world file as raw SDF and never runs xacro, so
    unexpanded <xacro:*> elements are skipped with only a warning and any
    macro-generated <model> silently never spawns. xacro_args is forwarded as
    name:=value; xacro ignores args a world does not declare. Non-xacro files
    pass through, and any failure falls back to the original path. The temp
    file is kept (delete=False) because the gz server and GUI open it
    independently, the GUI possibly after this returns.
    """
    try:
        with open(path) as f:
            if 'xacro' not in f.read():
                return path
    except OSError:
        return path

    cmd = ['xacro', path]
    for name, value in (xacro_args or {}).items():
        cmd.append(f'{name}:={value}')

    try:
        expanded = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=120).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, OSError):
        return path

    if not expanded.strip():
        return path

    try:
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.sdf',
            prefix=os.path.basename(path).split('.')[0] + '_', delete=False)
        with tmp:
            tmp.write(expanded)
    except OSError:
        return path
    return tmp.name


def build_gz_resource_path(package_share):
    model_paths = [
        os.path.join(package_share, 'models'),
    ]

    # Source-checkout fallback: find sibling tmc_wrs_gz source tree
    src_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tmc_source_models = os.path.join(src_root, 'tmc_wrs_gz', 'tmc_wrs_gz_worlds', 'models')
    if os.path.isdir(tmc_source_models):
        model_paths.append(tmc_source_models)

    for package_name in ('tmc_wrs_gz_worlds',):
        try:
            pkg_models = os.path.join(get_package_share_directory(package_name), 'models')
            if pkg_models not in model_paths:
                model_paths.append(pkg_models)
        except PackageNotFoundError:
            pass

    current_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    if current_path:
        model_paths.append(current_path)

    return os.pathsep.join(model_paths)
