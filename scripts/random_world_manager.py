#!/usr/bin/env python3

import os
import sys
import time
from copy import deepcopy

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rcl_interfaces.msg import SetParametersResult

from ros_gz_interfaces.msg import Entity, WorldControl
from ros_gz_interfaces.srv import ControlWorld, DeleteEntity, SpawnEntity
from std_srvs.srv import Trigger

from ament_index_python.packages import get_package_share_directory


SCRIPTS_DIR = os.path.join(get_package_share_directory('sobits_gazebo_worlds'), 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from random_world_runtime_lib import build_pose, build_spawn_sdf, generate_layout_specs, load_initial_layout_specs


class RandomWorldManager(Node):
    def __init__(self):
        super().__init__('random_world_manager')
        self._client_callback_group = ReentrantCallbackGroup()
        self._service_callback_group = ReentrantCallbackGroup()

        self.declare_parameter('world_name', 'default')
        self.declare_parameter('base_world', '')
        self.declare_parameter('placement_config', '')
        self.declare_parameter('models_root', '')
        self.declare_parameter('initial_layout_world_path', '')
        self.declare_parameter('seed', '')
        self.declare_parameter('object_count', 15)
        self.declare_parameter('object_prefix', 'random_ycb')
        self.declare_parameter('pause_physics_during_reconfigure', True)
        self.declare_parameter('spawn_on_start', False)

        self._world_name = self.get_parameter('world_name').value
        self._base_world = self.get_parameter('base_world').value
        self._placement_config = self.get_parameter('placement_config').value
        self._models_root = self.get_parameter('models_root').value
        self._initial_layout_world_path = self.get_parameter('initial_layout_world_path').value
        self._object_prefix = self.get_parameter('object_prefix').value
        self._pause_physics = bool(self.get_parameter('pause_physics_during_reconfigure').value)
        self._spawn_on_start = bool(self.get_parameter('spawn_on_start').value)
        self._seed_text = str(self.get_parameter('seed').value or '').strip()
        self._object_count = int(self.get_parameter('object_count').value)
        self._current_layout = load_initial_layout_specs(self._initial_layout_world_path, self._object_prefix)
        self.add_on_set_parameters_callback(self._on_parameter_update)
        self._startup_timer = None

        create_service_name = f'/world/{self._world_name}/create'
        remove_service_name = f'/world/{self._world_name}/remove'
        control_service_name = f'/world/{self._world_name}/control'
        self._spawn_client = self.create_client(
            SpawnEntity,
            create_service_name,
            callback_group=self._client_callback_group,
        )
        self._delete_client = self.create_client(
            DeleteEntity,
            remove_service_name,
            callback_group=self._client_callback_group,
        )
        self._control_client = self.create_client(
            ControlWorld,
            control_service_name,
            callback_group=self._client_callback_group,
        )

        self.create_service(
            Trigger,
            '/random_world/regenerate',
            self._handle_regenerate_trigger,
            callback_group=self._service_callback_group,
        )
        self.create_service(
            Trigger,
            '/sobits_gazebo_worlds/change_world',
            self._handle_regenerate_trigger,
            callback_group=self._service_callback_group,
        )
        self.create_service(
            Trigger,
            '/random_world/clear',
            self._handle_clear_trigger,
            callback_group=self._service_callback_group,
        )

        self.get_logger().info(
            f'Random world manager ready for world={self._world_name!r}, '
            f'tracking {len(self._current_layout)} random entities.'
        )

        if self._spawn_on_start and not self._current_layout:
            self._startup_timer = self.create_timer(1.0, self._handle_startup_spawn)

    def _on_parameter_update(self, params):
        updated_seed = self._seed_text
        updated_object_count = self._object_count
        updated_pause = self._pause_physics
        updated_spawn_on_start = self._spawn_on_start

        for param in params:
            if param.name == 'seed':
                updated_seed = str(param.value or '').strip()
                if updated_seed:
                    try:
                        int(updated_seed)
                    except ValueError:
                        return SetParametersResult(
                            successful=False,
                            reason='seed must be empty or an integer string',
                        )
            elif param.name == 'object_count':
                try:
                    updated_object_count = int(param.value)
                except (TypeError, ValueError):
                    return SetParametersResult(
                        successful=False,
                        reason='object_count must be an integer',
                    )
                if updated_object_count < 0:
                    return SetParametersResult(
                        successful=False,
                        reason='object_count must be >= 0',
                    )
            elif param.name == 'pause_physics_during_reconfigure':
                updated_pause = bool(param.value)
            elif param.name == 'spawn_on_start':
                updated_spawn_on_start = bool(param.value)

        self._seed_text = updated_seed
        self._object_count = updated_object_count
        self._pause_physics = updated_pause
        self._spawn_on_start = updated_spawn_on_start
        return SetParametersResult(successful=True)

    def _handle_startup_spawn(self):
        if self._startup_timer is not None:
            self._startup_timer.cancel()
            self._startup_timer = None
        try:
            new_layout = self._regenerate_impl(
                seed=self._current_seed_value(),
                object_count=self._object_count,
                pause_physics=self._pause_physics,
            )
            self.get_logger().info(
                f'Spawned {len(new_layout)} random entities during startup attach mode.'
            )
        except Exception as exc:
            self.get_logger().error(f'Failed startup random world spawn: {exc}')

    def _current_seed_value(self):
        if self._seed_text == '':
            return None
        return int(self._seed_text)

    def _wait_for_gazebo_services(self, timeout_sec=10.0):
        clients = (
            (self._spawn_client, 'spawn'),
            (self._delete_client, 'delete'),
            (self._control_client, 'control'),
        )
        for client, label in clients:
            if not client.wait_for_service(timeout_sec=timeout_sec):
                raise RuntimeError(
                    f'Gazebo {label} service is not available for world {self._world_name!r}.'
                )

    def _call_client(self, client, request, service_label):
        future = client.call_async(request)
        while rclpy.ok() and not future.done():
            time.sleep(0.01)
        if not future.done() or future.result() is None:
            raise RuntimeError(f'Call to Gazebo {service_label} service failed.')
        return future.result()

    def _set_paused(self, paused):
        request = ControlWorld.Request()
        request.world_control = WorldControl()
        request.world_control.pause = bool(paused)
        response = self._call_client(self._control_client, request, 'control')
        if not response.success:
            raise RuntimeError(f'Gazebo rejected pause={paused} request.')

    def _delete_layout(self, layout_specs, ignore_missing=True):
        deleted_names = []
        failures = []
        for spec in layout_specs:
            request = DeleteEntity.Request()
            request.entity = Entity()
            request.entity.name = spec['name']
            request.entity.type = Entity.MODEL
            response = self._call_client(self._delete_client, request, 'delete')
            if response.success:
                deleted_names.append(spec['name'])
                continue
            failures.append(spec['name'])

        if failures and not ignore_missing:
            raise RuntimeError(f'Failed to delete entities: {", ".join(failures)}')
        return deleted_names, failures

    def _spawn_layout(self, layout_specs):
        spawned_names = []
        for spec in layout_specs:
            request = SpawnEntity.Request()
            request.entity_factory.name = spec['name']
            request.entity_factory.allow_renaming = False
            request.entity_factory.sdf = build_spawn_sdf(
                spec['uri'],
                spec['name'],
                self._models_root,
                is_static=spec.get('static', True),
            )
            x, y, z, yaw = spec['pose']
            request.entity_factory.pose = build_pose(x, y, z, yaw)
            request.entity_factory.relative_to = 'world'
            response = self._call_client(self._spawn_client, request, 'spawn')
            if not response.success:
                raise RuntimeError(f'Failed to spawn entity {spec["name"]!r}.')
            spawned_names.append(spec['name'])
        return spawned_names

    def _regenerate_impl(self, seed, object_count, pause_physics):
        self._wait_for_gazebo_services()

        previous_layout = deepcopy(self._current_layout)
        if pause_physics:
            self._set_paused(True)

        spawned_new_layout = []
        try:
            self._delete_layout(previous_layout, ignore_missing=True)
            new_layout = generate_layout_specs(
                self._base_world,
                self._placement_config,
                self._models_root,
                object_count,
                self._object_prefix,
                seed,
            )
            spawned_new_layout = self._spawn_layout(new_layout)
            self._current_layout = new_layout
            self._object_count = object_count
            self._seed_text = '' if seed is None else str(seed)
            return new_layout
        except Exception as exc:
            self.get_logger().error(f'Regeneration failed, attempting rollback: {exc}')
            try:
                if spawned_new_layout:
                    partial_specs = [
                        spec for spec in new_layout
                        if spec['name'] in set(spawned_new_layout)
                    ]
                    self._delete_layout(partial_specs, ignore_missing=True)
                if previous_layout:
                    self._spawn_layout(previous_layout)
                    self._current_layout = previous_layout
            except Exception as rollback_exc:
                self.get_logger().error(f'Rollback failed: {rollback_exc}')
            raise
        finally:
            if pause_physics:
                try:
                    self._set_paused(False)
                except Exception as exc:
                    self.get_logger().warning(f'Failed to resume physics after reconfigure: {exc}')

    def _clear_impl(self, pause_physics):
        self._wait_for_gazebo_services()
        previous_layout = deepcopy(self._current_layout)
        if pause_physics:
            self._set_paused(True)
        try:
            deleted_names, failures = self._delete_layout(previous_layout, ignore_missing=True)
            self._current_layout = []
            return deleted_names, failures
        finally:
            if pause_physics:
                try:
                    self._set_paused(False)
                except Exception as exc:
                    self.get_logger().warning(f'Failed to resume physics after clear: {exc}')

    def _handle_regenerate_trigger(self, _request, response):
        try:
            new_layout = self._regenerate_impl(
                seed=self._current_seed_value(),
                object_count=self._object_count,
                pause_physics=self._pause_physics,
            )
            response.success = True
            response.message = ','.join(spec['name'] for spec in new_layout)
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_clear_trigger(self, _request, response):
        try:
            deleted_names, failures = self._clear_impl(self._pause_physics)
            response.success = True
            response.message = (
                f'Removed {len(deleted_names)} random entities.'
                + (f' Failures: {", ".join(failures)}' if failures else '')
            )
        except Exception as exc:
            response.success = False
            response.message = str(exc)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RandomWorldManager()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        executor.remove_node(node)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
