import socket
import threading
import json
import time
import config  # config.pyから設定をインポート


class GUIUDPListener:
    def __init__(self, listen_ip, listen_port):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.listen_ip, self.listen_port))
        self.sock.settimeout(0.1)  # Receive timeout

        self.latest_data = {
            "yellow_robots": {},
            "blue_robots": {},
            "ball": None,
            "timestamp": 0
        }
        self.running = False
        self.thread = None
        self.lock = threading.Lock()  # 共有データへのアクセスを保護するためのロック

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop)
        self.thread.daemon = True  # メインスレッド終了時に一緒に終了
        self.thread.start()
        print(
            f"GUI UDP listener started on {self.listen_ip}:{self.listen_port}")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)  # スレッドが終了するのを待つ
        self.sock.close()
        print("GUI UDP listener stopped.")

    def _listen_loop(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(config.BUFFER_SIZE)
                decoded_data = json.loads(data.decode('utf-8'))
                self._process_received_data(decoded_data)
            except socket.timeout:
                continue  # タイムアウトは通常動作なので無視
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
            except Exception as e:
                print(f"Error receiving GUI data: {e}")
            time.sleep(0.001)  # CPU使用率を下げるための短いスリープ

    def _process_received_data(self, data):
        if data.get("type") == "gui_update":
            with self.lock:
                # ロボットデータを更新 (チームカラーとIDで区別)
                team_color = data.get("team_color")
                if team_color == "yellow":
                    for robot_status in data.get("robots_status", []):
                        robot_id = str(robot_status["id"])
                        self.latest_data["yellow_robots"][robot_id] = robot_status
                elif team_color == "blue":
                    for robot_status in data.get("robots_status", []):
                        robot_id = str(robot_status["id"])
                        self.latest_data["blue_robots"][robot_id] = robot_status

                # ボールデータを更新
                self.latest_data["ball"] = data.get("ball_pos")
                self.latest_data["timestamp"] = data.get("timestamp")

    def get_latest_robot_data(self):
        """最新のロボットデータとボールデータを取得"""
        with self.lock:
            return self.latest_data["yellow_robots"].copy(), \
                self.latest_data["blue_robots"].copy(), \
                self.latest_data["ball"], \
                self.latest_data["timestamp"]
