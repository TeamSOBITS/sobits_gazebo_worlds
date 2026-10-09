#!/usr/bin/env python3
"""Thin CLI client for the simulation_interfaces services of Isaac Sim.

Launch sequence (exit codes: 0 ok, 1 service error, 2 service unavailable):
  wait -> load-world <asset_root>/usd/rcw2026_arena.usda --if-different
  -> spawn sobit_home <asset_root>/usd/robots/sobit_home/sobit_home.usd
     --pose -6 1.5 0 0 --replace -> state play
"""
import argparse
import math
import os
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from simulation_interfaces.msg import Result, SimulationState
from simulation_interfaces.msg import SpawnEntity as SpawnEntityMsg
from simulation_interfaces.srv import (
    DeleteEntity, GetCurrentWorld, GetEntities, GetSimulatorFeatures,
    LoadWorld, ResetSimulation, SetSimulationState, SpawnEntities,
    SpawnEntity)

STATES = {'stop': SimulationState.STATE_STOPPED,
          'play': SimulationState.STATE_PLAYING,
          'pause': SimulationState.STATE_PAUSED}
NODE = None


class Unavailable(Exception):
    pass


class Failed(Exception):
    pass


def call(srv_type, name, request, timeout):
    # Wait for the service, call it async and spin until the reply arrives.
    client = NODE.create_client(srv_type, name)
    end = time.monotonic() + timeout
    while not client.wait_for_service(timeout_sec=0.5):
        if time.monotonic() > end:
            raise Unavailable(f'service {name} not available after {timeout:g}s')
    future = client.call_async(request)
    rclpy.spin_until_future_complete(NODE, future, timeout_sec=max(timeout, 1.0))
    if not future.done():
        raise Unavailable(f'service {name} did not answer within {timeout:g}s')
    return future.result()


def check(response, what, ok_codes=()):
    # Raise Failed unless response.result is RESULT_OK or one of ok_codes.
    res = response.result
    if res.result == Result.RESULT_OK or res.result in ok_codes:
        return response
    raise Failed(f'{what}: code {res.result}: {res.error_message}')


def yaw_to_quat(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def make_pose(x, y, z, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'world'
    pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = x, y, z
    q = yaw_to_quat(yaw)
    (pose.pose.orientation.x, pose.pose.orientation.y,
     pose.pose.orientation.z, pose.pose.orientation.w) = q
    return pose


def prim_path(name):
    # Isaac maps an entity name to the prim path "/<name>" (not /World/<name>).
    return name if name.startswith('/') else '/' + name


def current_world(t):
    resp = call(GetCurrentWorld, '/get_current_world', GetCurrentWorld.Request(), t)
    # NO_WORLD_LOADED (101) is not an error here, it means "no world".
    check(resp, 'get_current_world', ok_codes=(GetCurrentWorld.Response.NO_WORLD_LOADED,))
    return resp.world.world_resource.uri


def same_uri(a, b):
    if os.path.exists(a) and os.path.exists(b):
        return os.path.realpath(a) == os.path.realpath(b)
    return a == b


def set_state(name, t):
    req = SetSimulationState.Request()
    req.state.state = STATES[name]
    check(call(SetSimulationState, '/set_simulation_state', req, t),
          f'set_simulation_state {name}',
          ok_codes=(SetSimulationState.Response.ALREADY_IN_TARGET_STATE,))


def entity_exists(path, t):
    req = GetEntities.Request()
    req.filters.filter = '^' + path + '$'
    return path in check(call(GetEntities, '/get_entities', req, t), 'get_entities').entities


def delete(name, t, ignore_missing, stop=False):
    # Isaac removes the prim on a later frame: wait until it is gone so a spawn right after cannot clash.
    req = DeleteEntity.Request()
    req.entity = prim_path(name)
    if stop:
        set_state('stop', t)
    ok = (Result.RESULT_NOT_FOUND,) if ignore_missing else ()
    check(call(DeleteEntity, '/delete_entity', req, t), f'delete {req.entity}', ok)
    end = time.monotonic() + min(t, 10.0)
    while entity_exists(req.entity, t) and time.monotonic() < end:
        time.sleep(0.2)
    time.sleep(0.5)  # the runner drops Isaac's ghost of the entity a frame later


def cmd_wait(a):
    resp = call(GetSimulatorFeatures, '/get_simulator_features',
                GetSimulatorFeatures.Request(), a.timeout)
    f = resp.features
    print(f'features={list(f.features)} formats={list(f.spawn_formats)}')


def cmd_state(a):
    set_state(a.state, a.timeout)


def cmd_load_world(a):
    if a.if_different and same_uri(current_world(a.timeout), a.uri):
        print('already loaded')
        return
    set_state('stop', a.timeout)
    req = LoadWorld.Request()
    req.uri = a.uri
    check(call(LoadWorld, '/load_world', req, a.timeout), f'load_world {a.uri}')


def cmd_spawn(a):
    if a.replace:
        delete(a.name, a.timeout, True, a.stop)
    pose = make_pose(*a.pose)
    client = NODE.create_client(SpawnEntities, '/spawn_entities')
    if client.wait_for_service(timeout_sec=min(5.0, a.timeout)):
        one = SpawnEntityMsg(name=a.name, allow_renaming=a.allow_renaming,
                             entity_namespace=a.namespace, initial_pose=pose)
        one.entity_resource.uri = a.uri
        req = SpawnEntities.Request()
        req.spawn_requests = [one]
        resp = call(SpawnEntities, '/spawn_entities', req, a.timeout)
        for r in resp.results:
            check(r, f'spawn {a.name}')
        check(resp, f'spawn {a.name}')
        names = [r.entity_name for r in resp.results]
    else:
        req = SpawnEntity.Request(name=a.name, allow_renaming=a.allow_renaming,
                                  uri=a.uri, entity_namespace=a.namespace,
                                  initial_pose=pose)
        resp = check(call(SpawnEntity, '/spawn_entity', req, a.timeout),
                     f'spawn {a.name}')
        names = [resp.entity_name]
    print('spawned ' + ' '.join(names))


def cmd_delete(a):
    delete(a.name, a.timeout, a.ignore_missing, a.stop)


def cmd_graphs_off(a):
    # Parameter of the host runner (scripts/isaac_sim.py); applied to every robot spawned afterwards.
    from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType
    from rcl_interfaces.srv import SetParameters
    req = SetParameters.Request()
    req.parameters = [Parameter(name='graphs_off', value=ParameterValue(
        type=ParameterType.PARAMETER_STRING, string_value=','.join(a.patterns)))]
    resp = call(SetParameters, '/isaac_sim/set_parameters', req, a.timeout)
    if not resp.results or not resp.results[0].successful:
        raise Failed('graphs-off: ' + (resp.results[0].reason if resp.results else 'no result'))
    print('graphs_off=' + (','.join(a.patterns) or '(none)'))


def cmd_reset(a):
    check(call(ResetSimulation, '/reset_simulation', ResetSimulation.Request(), a.timeout),
          'reset_simulation')


def cmd_entities(a):
    req = GetEntities.Request()
    req.filters.filter = a.filter
    resp = check(call(GetEntities, '/get_entities', req, a.timeout), 'get_entities')
    print('\n'.join(resp.entities))


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)

    def add(name, fn, help_, default_timeout=30.0):
        s = sub.add_parser(name, help=help_, description=help_)
        s.add_argument('--timeout', type=float, default=default_timeout,
                       help='seconds to wait for the service (default %(default)s)')
        s.set_defaults(fn=fn)
        return s

    add('wait', cmd_wait, 'wait until the simulator answers', 120.0)
    s = add('state', cmd_state, 'set the simulation state')
    s.add_argument('state', choices=list(STATES))
    s = add('load-world', cmd_load_world, 'load a USD world (stops the sim first)')
    s.add_argument('uri')
    s.add_argument('--if-different', action='store_true',
                   help='skip when the same world is already loaded')
    s = add('spawn', cmd_spawn,
            'spawn a USD entity; NAME becomes prim path /NAME (bare name, not /World/NAME)')
    s.add_argument('name')
    s.add_argument('uri')
    s.add_argument('--pose', nargs=4, type=float, default=[0.0] * 4,
                   metavar=('X', 'Y', 'Z', 'YAW'), help='world pose, yaw in radians')
    s.add_argument('--namespace', default='')
    s.add_argument('--allow-renaming', action='store_true')
    s.add_argument('--replace', action='store_true',
                   help='delete an existing entity NAME first')
    s.add_argument('--stop', action='store_true',
                   help='with --replace: stop the sim before deleting (a playing robot keeps live physics views)')
    s = add('delete', cmd_delete, 'delete an entity (NAME -> prim path /NAME)')
    s.add_argument('name')
    s.add_argument('--ignore-missing', action='store_true')
    s.add_argument('--stop', action='store_true', help='stop the sim before deleting')
    s = add('graphs-off', cmd_graphs_off,
            'sensor graphs (ROS2_Lidar_lidar_back) or graph/node (ROS2_Camera_head_camera/HelperDepth) the runner '
            'deactivates on every robot spawned from now on; no argument re-enables all')
    s.add_argument('patterns', nargs='*')
    add('reset', cmd_reset, 'reset the simulation')
    s = add('entities', cmd_entities, 'list entity prim paths')
    s.add_argument('--filter', default='', help='regex on the prim path')
    return p


def main():
    global NODE
    args = build_parser().parse_args()
    rclpy.init()
    NODE = rclpy.create_node('isaac_sim_control')
    try:
        args.fn(args)
        return 0
    except Unavailable as e:
        print(f'error: {e}', file=sys.stderr)
        return 2
    except Failed as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    finally:
        NODE.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    sys.exit(main())
