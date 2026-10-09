#!/usr/bin/env python3
"""Host-side Isaac Sim 6.1 runner driven by a ROS 2 container through simulation_interfaces.

Opens Isaac Sim with the ROS 2 bridge and isaacsim.ros2.sim_control, then idles; the container loads the
world and spawns robots with /load_world, /spawn_entities, /set_simulation_state, ... Start it with
scripts/isaac_sim.sh, then in the container: ros2 launch sobit_home_bringup isaac_minimal.launch.py
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(os.path.dirname(HERE))
CONTROL_NODE = "isaacsim.ros2.control.ROS2ControlManager"
CONTEXT_NODE = "isaacsim.ros2.bridge.ROS2Context"
CLOCK_PATH = "/World/ROS2_Clock"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--domain", type=int, default=69)
    p.add_argument("--rmw", default="rmw_cyclonedds_cpp")
    p.add_argument("--cyclonedds-uri", default=None, help="default: $CYCLONEDDS_URI, else sobit_home/cyclonedds_local.xml")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--urdf2usd-ros", default=os.environ.get("URDF2USD_ROS", os.path.join(SRC, "urdf2usd_ros")))
    p.add_argument("--world", help="open this USD at start (local test without the container)")
    p.add_argument("--robot", help="reference this robot USD under /World/<name>")
    p.add_argument("--name", help="entity name (default: robot USD stem)")
    p.add_argument("--pose", type=float, nargs=4, default=[0.0, 0.0, 0.0, 0.0], metavar=("X", "Y", "Z", "YAW"))
    p.add_argument("--play", action="store_true", help="play after the local load")
    return p.parse_args()


def resolve_cyclonedds_uri(arg):
    if arg:
        return arg, "--cyclonedds-uri"
    if os.environ.get("CYCLONEDDS_URI"):
        return os.environ["CYCLONEDDS_URI"], "env"
    xml = os.path.join(SRC, "sobit_home", "cyclonedds_local.xml")
    return (f"file://{xml}", "sobit_home default") if os.path.isfile(xml) else (None, "unset")


def setup_env(args):
    """Set the ROS env, then re-exec with Isaac's bundled Jazzy libs (inherits everything set before)."""
    repo = os.path.abspath(args.urdf2usd_ros)
    if not os.path.isfile(os.path.join(repo, "utils", "ros_env.py")):
        sys.exit(f"error: urdf2usd_ros not found at {repo} (set --urdf2usd-ros or URDF2USD_ROS)")
    sys.path.insert(0, repo)
    env_domain = os.environ.get("ROS_DOMAIN_ID")
    if not os.environ.get("URDF2USD_ROS_REEXEC") and env_domain not in (None, str(args.domain)):
        print(f"warning: ROS_DOMAIN_ID={env_domain} in env ignored, using --domain {args.domain}", file=sys.stderr)
    uri, src = resolve_cyclonedds_uri(args.cyclonedds_uri)
    if not os.environ.get("URDF2USD_ROS_REEXEC"):
        print(f"CYCLONEDDS_URI from {src}: {uri}", flush=True)
    os.environ.update({"ROS_AUTOMATIC_DISCOVERY_RANGE": "LOCALHOST", "OMNI_KIT_ACCEPT_EULA": "yes"})
    if uri:
        os.environ["CYCLONEDDS_URI"] = uri
    from utils.ros_env import ensure_bundled_ros
    ensure_bundled_ros(domain_id=args.domain)
    os.environ["RMW_IMPLEMENTATION"] = args.rmw  # ensure_bundled_ros pins fastrtps
    keys = ("ROS_DOMAIN_ID", "RMW_IMPLEMENTATION", "CYCLONEDDS_URI", "ROS_AUTOMATIC_DISCOVERY_RANGE")
    print("ROS env:", {k: os.environ.get(k) for k in keys}, flush=True)


def prepare_stage(stage):
    """One root-layer physics scene (referenced-only scenes double sim time) and one /clock per stage."""
    from pxr import UsdPhysics
    from utils import isaac_world
    scenes = [p.GetPath() for p in stage.Traverse() if p.IsA(UsdPhysics.Scene)]
    root = stage.GetRootLayer()
    if not scenes or all(root.GetPrimAtPath(p) is None for p in scenes):
        isaac_world.ensure_root_physics_scene(stage)
        print("stage: root physics scene at /World/physicsScene", flush=True)
    if not stage.GetPrimAtPath(CLOCK_PATH):
        isaac_world.add_clock_graph(stage, CLOCK_PATH, use_domain_id_env=True)
        print(f"stage: /clock graph at {CLOCK_PATH}", flush=True)


def fix_control_config(prim):
    attr = prim.GetAttribute("inputs:controllerConfig")
    value = attr.Get() if attr else None
    if not value or os.path.isfile(value):
        return
    name = os.path.basename(value)
    for spec in prim.GetPrimStack():
        real = spec.layer.realPath
        cand = os.path.join(os.path.dirname(real), name) if real else None
        if cand and os.path.isfile(cand):
            attr.Set(cand)
            print(f"controllerConfig {prim.GetPath()}: {value} -> {cand}", flush=True)
            return
    print(f"warning: controllerConfig {value} missing and no {name} next to the layers of {prim.GetPath()}", flush=True)


def fix_subtree(prim, domain, noted):
    """Repair asset-baked values on the OmniGraph nodes under prim (only resynced subtrees, never per frame)."""
    from pxr import Usd
    for p in Usd.PrimRange(prim):
        if p.GetTypeName() != "OmniGraphNode":
            continue
        kind = p.GetAttribute("node:type").Get()
        if kind == CONTROL_NODE:
            fix_control_config(p)
        elif kind == CONTEXT_NODE:
            env, dom = p.GetAttribute("inputs:useDomainIDEnvVar"), p.GetAttribute("inputs:domain_id")
            if not (env and env.Get()) and dom and dom.Get() != domain:
                if p.GetPath() not in noted:
                    noted.add(p.GetPath())
                    print(f"ROS2Context {p.GetPath()}: domain_id {dom.Get()} -> {domain}", flush=True)
                dom.Set(domain)


def report_entity(path, prim):
    """One line per top-level prim change (spawn / delete / world reload), the operator's trace of the services.
    A deleted robot is not respawnable: its sensor writers and controller_manager outlive the prim; reload the world."""
    if not prim or not prim.IsValid():
        print(f"entity {path}: removed", flush=True)
        return
    layers = sorted({os.path.basename(s.layer.identifier) for s in prim.GetPrimStack()})
    print(f"entity {path}: {'active' if prim.IsActive() else 'INACTIVE'} layers={layers}", flush=True)


def spawn_local(stage, robot, name, pose):
    """Mimic /spawn_entities: referenced Xform, pose, and the marker /reset_simulation removes."""
    from pxr import Gf, Sdf, UsdGeom
    prim = stage.DefinePrim(f"/World/{name}", "Xform")
    prim.GetReferences().AddReference(os.path.abspath(robot))
    xf = UsdGeom.XformCommonAPI(prim)
    if not (xf.SetTranslate(Gf.Vec3d(*pose[:3])) and xf.SetRotate(Gf.Vec3f(0, 0, math.degrees(pose[3])))):
        print(f"warning: could not set the pose of {prim.GetPath()}", flush=True)
    prim.CreateAttribute("simulationInterfacesSpawned", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
    print(f"spawned {prim.GetPath()} <- {robot} at {pose}", flush=True)
    return prim


def main():
    args = parse_args()
    setup_env(args)
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": args.headless, "renderer": "RayTracedLighting"})
    try:
        run(app, args)
    except KeyboardInterrupt:
        pass
    finally:
        app.close()


def run(app, args):
    from isaacsim.core.utils.extensions import enable_extension
    for ext in ("isaacsim.ros2.bridge", "isaacsim.ros2.sim_control"):
        if not enable_extension(ext):
            print(f"warning: could not enable {ext}", flush=True)
    from utils import ros2_control
    if not ros2_control.enable():
        print("warning: isaacsim.ros2.control not enabled/patched, robots with ros2_control will fail", flush=True)
    for _ in range(10):  # omni.graph.core crashes if a stage opens right after enabling
        app.update()
    import omni.usd
    from pxr import Tf, Usd
    ctx = omni.usd.get_context()
    state = {"opened": False, "paths": set(), "listener": None, "noted": set()}

    def on_changed(notice, _stage):
        state["paths"].update(notice.GetResyncedPaths())

    def on_opened(_event):
        state["opened"] = True  # handled on the next frame, not inside the event

    def handle_opened():
        state["opened"] = False
        stage = ctx.get_stage()
        if state["listener"]:
            state["listener"].Revoke()
        state["listener"] = Tf.Notice.Register(Usd.Notice.ObjectsChanged, on_changed, stage)
        state["paths"].clear()
        prepare_stage(stage)
        return stage

    def drain():
        if state["opened"]:
            handle_opened()
        if not state["paths"]:
            return
        stage, paths = ctx.get_stage(), state["paths"]
        state["paths"] = set()
        for path in paths:
            prim = stage.GetPrimAtPath(path) if path.IsPrimPath() or path.IsAbsoluteRootPath() else None
            if path.IsPrimPath() and path.GetParentPath().IsAbsoluteRootPath():
                report_entity(path, prim)
            if prim:
                fix_subtree(prim, args.domain, state["noted"])

    sub = ctx.get_stage_event_stream().create_subscription_to_pop_by_type(  # noqa: F841  keep alive
        int(omni.usd.StageEventType.OPENED), on_opened)
    stage = handle_opened()
    if args.world:
        state["opened"] = False
        if not ctx.open_stage(os.path.abspath(args.world)):
            sys.exit(f"error: could not open {args.world}")
        while not state["opened"] and app.is_running():
            app.update()
        stage = handle_opened()
        print(f"opened {args.world}", flush=True)
    if args.robot:
        spawn_local(stage, args.robot, args.name or os.path.splitext(os.path.basename(args.robot))[0], args.pose)
    if args.world or args.robot:
        state["paths"].clear()
        fix_subtree(stage.GetPseudoRoot(), args.domain, state["noted"])
    for _ in range(10):
        app.update()
    if args.play and (args.world or args.robot):
        import omni.timeline
        omni.timeline.get_timeline_interface().play()
        print("playing", flush=True)
    print(f"READY domain={args.domain} rmw={args.rmw} services=simulation_interfaces", flush=True)
    while app.is_running():
        app.update()
        drain()


if __name__ == "__main__":
    main()
