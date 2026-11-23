#!/usr/bin/env python3
"""Write a MuJoCo scene = exported world + exported robot at a pose, for mujoco_ros2_control (`mujoco_model`).

  python3 scripts/mujoco_scene.py --world export/mjcf/rcw2026_arena/rcw2026_arena.xml \\
      --robot export/mjcf/robots/sobit_home/sobit_home.xml --pose -6 1.5 0 0 [--out PATH]

The robot's sections come first (its joints lead qpos, so its `home` keyframe is kept with the root pose set to
--pose and the world's joints appended at their defaults), the world's mesh paths stay relative to its own
directory, and its degree-valued joint ranges are converted because the robot is authored in radians.
Only the standard library is needed. Prints the scene path.
"""
import argparse
import math
import os
import sys
import xml.etree.ElementTree as ET

ROBOT_FIRST = ("option", "visual", "equality", "actuator")  # one source: the robot (keyframe: build())
MERGED = ("extension", "asset", "contact", "sensor", "tendon", "custom")  # extension: mujoco.plugin.lidar instances


def _parse(path):
    return ET.parse(path).getroot()


def _joint_qpos0(body, joint):
    """Default qpos of one world joint: a free joint takes its body's pose, everything else sits at 0."""
    if joint.tag == "freejoint" or joint.get("type") == "free":
        pos = body.get("pos", "0 0 0").split()
        quat = body.get("quat", "1 0 0 0").split()
        return pos + quat
    return ["0"] * (4 if joint.get("type") == "ball" else 1)


def world_qpos0(worldbody):
    """qpos of the world's joints in MuJoCo's order (document order of the body tree)."""
    out = []
    for body in worldbody.iter("body"):
        for child in body:
            if child.tag in ("joint", "freejoint"):
                out += _joint_qpos0(body, child)
    return out


def deg_ranges_to_rad(root):
    """World files from gz export carry degree ranges; the scene compiles with angle="radian".

    MuJoCo reads only hinge/ball joint ranges as angles (type defaults to hinge); slide joints and tendons are metres.
    """
    comp = root.find("compiler")
    if comp is not None and comp.get("angle", "degree") == "radian":
        return
    for e in root.iter():
        if e.tag == "joint" and e.get("range") and e.get("type", "hinge") in ("hinge", "ball"):
            e.set("range", " ".join(f"{math.radians(float(v)):.9g}" for v in e.get("range").split()))
        if e.get("euler"):
            raise SystemExit("error: euler attributes in the world need a conversion this script lacks")


def merge_defaults(robot, world):
    """One <default> tree: the robot's root default plus the world's named classes (sdf2mjcf emits only those)."""
    rdef, wdef = robot.find("default"), world.find("default")
    if wdef is None or rdef is None:
        return rdef if rdef is not None else wdef
    if any(c.tag != "default" for c in wdef):
        raise SystemExit("error: both robot and world set root <default> values; merge them by hand")
    taken = {d.get("class") for d in rdef.iter("default")}
    for cls in wdef:
        clash = taken & {d.get("class") for d in cls.iter("default")}
        if clash:
            raise SystemExit(f"error: default class(es) {sorted(clash)} defined by both robot and world")
        rdef.append(cls)
    return rdef


def absolutize_robot_files(robot, robot_path):
    """Robot asset files relative to its own meshdir/texturedir; absolute paths ignore the scene's (world) dirs."""
    rdir = os.path.dirname(os.path.abspath(robot_path))
    comp = robot.find("compiler")
    get = (lambda k: comp.get(k)) if comp is not None else (lambda k: None)
    asset = get("assetdir") or ""
    dirs = {"mesh": get("meshdir") or asset, "hfield": get("meshdir") or asset,
            "skin": get("meshdir") or asset, "texture": get("texturedir") or asset}
    for e in robot.iter():
        f = e.get("file")
        if f and not os.path.isabs(f):
            e.set("file", os.path.normpath(os.path.join(rdir, dirs.get(e.tag, ""), f)))


def build(world_path, robot_path, pose, name, keyframe):
    world, robot = _parse(world_path), _parse(robot_path)
    deg_ranges_to_rad(world)
    absolutize_robot_files(robot, robot_path)
    scene = ET.Element("mujoco", model=f"scene_{name}")
    wdir = os.path.dirname(os.path.abspath(world_path))
    wcomp = world.find("compiler")
    comp = ET.SubElement(scene, "compiler", angle="radian")
    for key in ("meshdir", "texturedir"):
        val = wcomp.get(key, ".") if wcomp is not None else "."
        comp.set(key, os.path.normpath(os.path.join(wdir, val)))
    for tag in ROBOT_FIRST:
        src = robot.find(tag)
        if src is not None:
            scene.append(src)
    default = merge_defaults(robot, world)
    if default is not None:
        scene.append(default)
    for tag in MERGED:
        dst = None
        for src in (robot.find(tag), world.find(tag)):
            if src is None:
                continue
            if dst is None:
                dst = ET.SubElement(scene, tag)
            dst.extend(list(src))
    wb = ET.SubElement(scene, "worldbody")
    rwb = robot.find("worldbody")
    root_body = next(b for b in rwb if b.tag == "body")
    x, y, z, yaw = pose
    base_z = float(root_body.get("pos", "0 0 0").split()[2])
    root_pose = [f"{x:.9g}", f"{y:.9g}", f"{z + base_z:.9g}",
                 f"{math.cos(yaw / 2):.9g}", "0", "0", f"{math.sin(yaw / 2):.9g}"]
    root_body.set("pos", " ".join(root_pose[:3]))
    root_body.set("quat", " ".join(root_pose[3:]))
    wb.extend(list(rwb))
    wb.extend(list(world.find("worldbody")))
    key = robot.find(f"keyframe/key[@name='{keyframe}']")
    if key is not None:
        qpos = key.get("qpos", "").split() or world_qpos0(rwb)  # ctrl-only key: the robot's default qpos
        if root_body.find("freejoint") is not None or any(j.get("type") == "free" for j in root_body.findall("joint")):
            qpos[:7] = root_pose
        qpos += world_qpos0(world.find("worldbody"))
        kf = ET.SubElement(scene, "keyframe")
        k = ET.SubElement(kf, "key", name=keyframe, qpos=" ".join(qpos))
        if key.get("ctrl"):
            k.set("ctrl", key.get("ctrl"))
    return scene


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--world", required=True)
    ap.add_argument("--robot", required=True)
    ap.add_argument("--pose", type=float, nargs=4, default=[0.0, 0.0, 0.0, 0.0], metavar=("X", "Y", "Z", "YAW"))
    ap.add_argument("--name", help="robot entity name (default: robot file stem)")
    ap.add_argument("--keyframe", default="home", help="robot keyframe to carry over (default home)")
    ap.add_argument("--out", help="default: <world dir>/scene_<name>.xml")
    a = ap.parse_args()
    name = a.name or os.path.splitext(os.path.basename(a.robot))[0]
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.world)), f"scene_{name}.xml")
    scene = build(a.world, a.robot, a.pose, name, a.keyframe)
    ET.indent(scene)
    ET.ElementTree(scene).write(out, xml_declaration=False, encoding="unicode")
    with open(out, "a") as f:
        f.write("\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
