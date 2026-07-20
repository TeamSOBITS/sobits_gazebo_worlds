import os
import sys
import math
import threading
import yaml
import rclpy
from rclpy.node import Node

# 正しいサービス型をインポート
from ros_gz_interfaces.srv import SpawnEntity
from geometry_msgs.msg import PoseArray 

class MarkerRecorder(Node):
    def __init__(self, config):
        super().__init__('marker_recorder')
        
        # YAML設定の読み込み
        self.world_name = config.get('world_name', 'restaurant') # 確実にrestaurantが使われるようにします
        self.marker_name = config.get('marker_name', 'interactive_marker')
        self.save_dir = config.get('save_directory', './saved_positions')
        
        init_pos = config.get('initial_position', {'x': 0.0, 'y': 0.0, 'z': 0.0})
        self.init_x = init_pos.get('x', 0.0)
        self.init_y = init_pos.get('y', 0.0)
        self.init_z = init_pos.get('z', 0.0)

        self.position_count = 1
        self.current_pose = None
        self.lock = threading.Lock()
        
        # 保存用フォルダの作成
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # 1. Gazebo Harmonicのポーズトピックをサブスクライブ
        self.subscription = self.create_subscription(
            PoseArray,
            f'/world/{self.world_name}/pose/info',
            self.pose_callback,
            10
        )
        
        # 2. あなたの環境に合わせたサービス名を設定
        self.spawn_service_name = f'/world/{self.world_name}/create'
        self.spawn_client = self.create_client(SpawnEntity, self.spawn_service_name)
        self.spawn_marker()

        # 3. キーボード入力監視スレッドの開始
        self.input_thread = threading.Thread(target=self.wait_for_user_input)
        self.input_thread.daemon = True
        self.input_thread.start()

    def spawn_marker(self):
        self.get_logger().info(f'{self.spawn_service_name} サービスが立ち上がるのを待っています...')
        while not self.spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('確認中: Gazebo側のサービス待機中...')
        
        # マーカー用SDFの定義
        marker_sdf = f"""
        <sdf version="1.8">
          <model name="{self.marker_name}">
            <static>false</static>
            <pose>{self.init_x} {self.init_y} {self.init_z} 0 0 0</pose>
            <link name="link">
              <visual name="visual">
                <geometry><box><size>0.3 0.3 0.3</size></box></geometry>
                <material>
                  <ambient>0 1 0 1</ambient>
                  <diffuse>0 1 0 1</diffuse>
                </material>
              </visual>
              <collision name="collision">
                <geometry><box><size>0.3 0.3 0.3</size></box></geometry>
              </collision>
            </link>
          </model>
        </sdf>
        """
        
        # 判明した ros_gz_interfaces/srv/SpawnEntity の構造にリクエストを適合
        req = SpawnEntity.Request()
        req.entity_name = self.marker_name
        req.xml = marker_sdf
        
        future = self.spawn_client.call_async(req)
        future.add_done_callback(self.spawn_callback)

    def spawn_callback(self, future):
        try:
            res = future.result()
            self.get_logger().info('マーカーの出現に成功しました！')
            self.get_logger().info('GazeboのUI上でマーカーを移動させ、ターミナルでEnterを押してください。')
        except Exception as e:
            self.get_logger().error(f'スポーン失敗: {e}')

    def pose_callback(self, msg):
        with self.lock:
            for name, pose in zip(msg.name, msg.pose):
                if name == self.marker_name:
                    self.current_pose = pose
                    break

    def quaternion_to_euler(self, q):
        ysqr = q.y * q.y
        t0 = +2.0 * (q.w * q.x + q.y * q.z)
        t1 = +1.0 - 2.0 * (q.x * q.x + ysqr)
        roll = math.atan2(t0, t1)
        
        t2 = +2.0 * (q.w * q.y - q.z * q.x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch = math.asin(t2)
        
        t3 = +2.0 * (q.w * q.z + q.x * q.y)
        t4 = +1.0 - 2.0 * (ysqr + q.z * q.z)
        yaw = math.atan2(t3, t4)
        
        return roll, pitch, yaw

    def wait_for_user_input(self):
        while rclpy.ok():
            input() 
            
            with self.lock:
                if self.current_pose is None:
                    self.get_logger().warn('まだGazeboからマーカーの座標を受信していません。')
                    continue
                
                p = self.current_pose.position
                o = self.current_pose.orientation
            
            r, p_ang, y = self.quaternion_to_euler(o)
            
            filename = f"position{self.position_count}.sdf"
            filepath = os.path.join(self.save_dir, filename)
            
            if os.path.exists(filepath):
                print(f"\n⚠️  警告: {filename} は既に存在します。")
                choice = input("上書きしますか？ (y/n): ").strip().lower()
                if choice != 'y':
                    print("保存をキャンセルしました。")
                    self.position_count += 1
                    continue

            # 指定されたフォーマットでSDFテキストを生成
            sdf_content = f"""<?xml version="1.0"?>
<sdf version="1.10">
  <model name="woman">
    <static>false</static>
    <link name="link">
      <pose>{p.x:.4f} {p.y:.4f} {p.z:.4f} {r:.4f} {p_ang:.4f} {y:.4f}</pose>
      <visual name="visual">
        <geometry>
          <mesh>
            <uri>model://woman/meshes/woman.glb</uri>
          </mesh>
        </geometry>
      </visual>
      <collision name="collision">
        <geometry>
          <mesh>
            <uri>model://woman/meshes/woman.glb</uri>
          </mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>"""

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sdf_content)
                
            print(f"✅ 保存完了: {filepath}")
            print(f"   位置 -> x: {p.x:.2f}, y: {p.y:.2f}, z: {p.z:.2f}")
            print(f"   向き -> Roll: {r:.2f}, Pitch: {p_ang:.2f}, Yaw: {y:.2f}\n")
            
            self.position_count += 1

def main(args=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"エラー: config.yaml の読み込みに失敗しました。({e})")
        return

    rclpy.init(args=args)
    node = MarkerRecorder(config)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()