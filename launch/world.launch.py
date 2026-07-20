from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from ament_index_python.packages import get_package_prefix, get_package_share_directory
import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from launch_utils import build_gz_resource_path


def generate_launch_description():
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='rcjo2025_arena.world.xacro',
        description=(
            'World filename under sobits_gazebo_worlds/worlds. '
            'Options: precomp2025_arena.world.xacro, '
            'rcjo2025_arena.world.xacro, '
            'rcjo2026_arena.world.xacro'
        ),
    )

    world_file_path = PathJoinSubstitution([
        get_package_share_directory('sobits_gazebo_worlds'),
        'worlds',
        LaunchConfiguration('world')
    ])

    gui_config_path = os.path.join(
        get_package_share_directory('sobits_gazebo_worlds'), 'config', 'gui.config')

    # gz_human_sim's HumanControlPanel GUI plugin (used by gui.config below)
    # lives under lib/gz_human_sim/gz-gui. gz_human_sim ships an
    # environment hook that adds this to GZ_GUI_PLUGIN_PATH/LD_LIBRARY_PATH
    # too, but that hook's $AMENT_CURRENT_PREFIX has been observed to
    # resolve to the wrong package prefix once ament chains multiple
    # workspaces (see conversation history) -- set it explicitly here so
    # panel loading does not depend on that being right.
    human_gui_plugin_dir = os.path.join(
        get_package_prefix('gz_human_sim'), 'lib', 'gz_human_sim', 'gz-gui')

    return LaunchDescription([
        world_arg,
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=build_gz_resource_path(
                get_package_share_directory('sobits_gazebo_worlds')
            ),
        ),
        SetEnvironmentVariable(
            name='GZ_GUI_PLUGIN_PATH',
            value=human_gui_plugin_dir + os.pathsep + os.environ.get('GZ_GUI_PLUGIN_PATH', ''),
        ),
        SetEnvironmentVariable(
            name='LD_LIBRARY_PATH',
            value=human_gui_plugin_dir + os.pathsep + os.environ.get('LD_LIBRARY_PATH', ''),
        ),
        # guide_robot(guider_multifloor_builder)と同じ対策: これが無いと
        # gz-simのogre2レンダーパスがディスプレイのデフォルトGLXベンダー
        # （ハイブリッドグラフィックス環境だとllvmpipe等のソフトウェア
        # 実装のことがある）に無警告でフォールバックしてしまうことがある。
        SetEnvironmentVariable(name='__GLX_VENDOR_LIBRARY_NAME', value='nvidia'),
        SetEnvironmentVariable(name='__NV_PRIME_RENDER_OFFLOAD', value='1'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch'), '/gz_sim.launch.py']),
            launch_arguments=[
                # -r: start the server running instead of paused. Without
                # it, gui.config's WorldControl <start_paused>true</...>
                # leaves the world frozen -- PreUpdate() in every gz-sim
                # System plugin (including ActorCommandPlugin) returns
                # immediately while paused, so human teleop (GUI pad and
                # keyboard alike) looks completely dead until someone
                # manually hits the play button. guide_robot's own launch
                # files (project_world.launch.py, generated_world.launch.py)
                # always pass -r for the same reason.
                ('gz_args', ['-r ', world_file_path, ' --gui-config ', gui_config_path])]
        )
    ])
