#!/usr/bin/env python3
import sys
import math
import argparse
from gz.transport13 import Node
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.entity_factory_pb2 import EntityFactory
from gz.msgs10.entity_pb2 import Entity
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.world_control_pb2 import WorldControl
from gz.msgs10.quaternion_pb2 import Quaternion

def euler_to_quaternion(r, p, y):
    sr, cr = math.sin(r/2), math.cos(r/2)
    sp, cp = math.sin(p/2), math.cos(p/2)
    sy, cy = math.sin(y/2), math.cos(y/2)
    q = Quaternion()
    q.x = sr * cp * cy - cr * sp * sy
    q.y = cr * sp * cy + sr * cp * sy
    q.z = cr * cp * sy - sr * sp * cy
    q.w = cr * cp * cy + sr * sp * sy
    return q

def get_world(node):
    for srv in node.service_list():
        if '/control' in srv and srv.startswith('/world/'):
            return srv.split('/')[2]
    return None

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    
    # Pose / Teleport
    sp = sub.add_parser("set_pose")
    sp.add_argument("name"); sp.add_argument("coords", type=float, nargs=6)
    
    # Simulation Control
    sub.add_parser("pause")
    sub.add_parser("play")
    
    # Delete
    del_p = sub.add_parser("delete")
    del_p.add_argument("name")

    args = parser.parse_args()
    node = Node()
    world = get_world(node)
    
    if not world:
        print("Error: World not found. Is Gazebo running?")
        sys.exit(1)

    if args.cmd in ["pause", "play"]:
        req = WorldControl()
        req.pause = (args.cmd == "pause")
        res = node.request(f"/world/{world}/control", req, WorldControl, Boolean, 2000)
        print(f"World {args.cmd}ed: {res[0]}")

    elif args.cmd == "set_pose":
        req = Pose()
        req.name = args.name
        req.position.x, req.position.y, req.position.z = args.coords[:3]
        q = euler_to_quaternion(*args.coords[3:])
        req.orientation.CopyFrom(q)
        res = node.request(f"/world/{world}/set_pose", req, Pose, Boolean, 2000)
        print(f"Pose set: {res[0]}")

    elif args.cmd == "delete":
        req = Entity()
        req.name = args.name
        req.type = 2 # MODEL
        res = node.request(f"/world/{world}/remove", req, Entity, Boolean, 2000)
        print(f"Entity deleted: {res[0]}")

if __name__ == "__main__":
    main()
