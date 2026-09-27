#!/usr/bin/env python3
"""Drive the hinged arena doors in rcw2026_arena.

The doors are revolute joints with a JointPositionController; commanding one
means publishing an angle in radians on
/model/<door>/joint/hinge/0/cmd_pos.

Examples:
  door_demo.py                     # open, pause, close (both doors)
  door_demo.py --cycles 3          # repeat three times
  door_demo.py --door arena_door_lower
  door_demo.py --angle 0.7854      # 45 deg instead of 90
  door_demo.py --open              # just open and exit
  door_demo.py --close             # just close and exit
"""

import argparse
import math
import shutil
import subprocess
import sys
import time

DOORS = ['arena_door_lower', 'arena_door_upper']
OPEN_RAD = math.pi / 2.0
CLOSED_RAD = 0.0


def cmd_topic(door):
    return f'/model/{door}/joint/hinge/0/cmd_pos'


def send(door, angle, gz='gz'):
    """Publish one position command. Returns True if gz accepted it."""
    result = subprocess.run(
        [gz, 'topic', '-t', cmd_topic(door),
         '-m', 'gz.msgs.Double', '-p', f'data: {angle}'],
        capture_output=True, text=True)
    return result.returncode == 0


def move(doors, angle, label, settle, gz='gz'):
    print(f'{label:>7}: {math.degrees(angle):5.1f} deg -> {", ".join(doors)}')
    for door in doors:
        if not send(door, angle, gz):
            print(f'         WARNING: command to {door} failed', file=sys.stderr)
    time.sleep(settle)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--door', action='append', dest='doors', metavar='NAME',
                    help='door model name; repeatable. Default: both arena doors.')
    ap.add_argument('--cycles', type=int, default=1,
                    help='open/close repetitions (default 1)')
    ap.add_argument('--angle', type=float, default=OPEN_RAD,
                    help=f'open angle in radians (default {OPEN_RAD:.4f} = 90 deg)')
    ap.add_argument('--settle', type=float, default=3.0,
                    help='seconds to wait after each command (default 3)')
    group = ap.add_mutually_exclusive_group()
    group.add_argument('--open', action='store_true', help='open only, then exit')
    group.add_argument('--close', action='store_true', help='close only, then exit')
    args = ap.parse_args()

    gz = shutil.which('gz')
    if not gz:
        sys.exit('gz not on PATH. Source the ROS/Gazebo environment first '
                 '(the container needs ~/.bashrc for GZ_CONFIG_PATH).')

    doors = args.doors or DOORS

    if args.open:
        move(doors, args.angle, 'open', args.settle, gz)
        return
    if args.close:
        move(doors, CLOSED_RAD, 'close', args.settle, gz)
        return

    for i in range(args.cycles):
        if args.cycles > 1:
            print(f'--- cycle {i + 1}/{args.cycles} ---')
        move(doors, args.angle, 'open', args.settle, gz)
        move(doors, CLOSED_RAD, 'close', args.settle, gz)
    print('done')


if __name__ == '__main__':
    main()
