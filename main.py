import tkinter as tk
from tkinter import ttk
import socket
import threading
import json
import queue
import math
import time  # For timestamp in command tab (example)

# GUI側もconfigを参照してポートなどを設定
import config  # Assuming config.py is in the same directory or PYTHONPATH

# 定数
CANVAS_WIDTH = 800  # キャンバスの幅
CANVAS_HEIGHT = 600  # キャンバスの高さ
FIELD_MARGIN = 50   # コート周囲のマージン
ROBOT_RADIUS_GUI = 10  # GUI上でのロボットの半径 (ピクセル)
BALL_RADIUS_GUI = 5   # GUI上でのボールの半径 (ピクセル)

# コートの寸法 (configから取得)
COURT_WIDTH_M = config.COURT_WIDTH   # メートル
COURT_HEIGHT_M = config.COURT_HEIGHT  # メートル


class RobotGUI:
    def __init__(self, master):
        self.master = master
        master.title("Robot Control GUI")
        master.geometry("850x700")  # ウィンドウサイズ調整

        self.data_queue = queue.Queue()
        self.running = True

        # UDP受信用ソケット (コントローラーからのデータ)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.udp_sock.bind((config.GUI_TARGET_IP, config.GUI_TARGET_PORT))
            print(
                f"GUI UDP server bound to {config.GUI_TARGET_IP}:{config.GUI_TARGET_PORT}")
        except socket.error as e:
            print(
                f"Failed to bind GUI UDP socket: {e}. Check if address is already in use.")
            master.destroy()
            return
        self.udp_sock.settimeout(1.0)

        # UDP送信用ソケット (GUIからコントローラーへのコマンド)
        self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(
            f"GUI Command UDP client socket created for sending to {config.CONTROLLER_GUI_LISTEN_IP}:{config.CONTROLLER_GUI_LISTEN_PORT}")

        # タブコントロール
        self.notebook = ttk.Notebook(master)

        # Gameタブ
        self.game_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.game_frame, text='Game')
        self.init_game_tab()

        # Robotタブ
        self.robot_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.robot_frame, text='Robot')
        self.init_robot_tab()

        # Commandタブ
        self.command_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.command_frame, text='Command')
        self.init_command_tab()

        self.notebook.pack(expand=True, fill='both')

        # データ保持用
        self.all_robots_status = {}  # key: robot_id, value: robot_status_dict
        self.latest_ball_pos = None
        self.latest_team_color = "Unknown"
        self.last_data_received_time = {}  # key: robot_id, value: timestamp

        # 受信スレッド開始
        self.receive_thread = threading.Thread(
            target=self.receive_data, daemon=True)
        self.receive_thread.start()

        # GUI更新処理
        self.update_gui()

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def init_game_tab(self):
        self.canvas = tk.Canvas(
            self.game_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="dark green")
        self.canvas.pack(pady=10, padx=10)
        self.draw_field()

        self.team_color_label = ttk.Label(
            self.game_frame, text="Team: Unknown", font=("Arial", 12))
        self.team_color_label.pack(pady=5)

        self.robot_items = {}
        self.ball_item = None

    def draw_field(self):
        self.canvas.create_rectangle(
            *self.world_to_canvas(-COURT_WIDTH_M / 2, COURT_HEIGHT_M / 2),
            *self.world_to_canvas(COURT_WIDTH_M / 2, -COURT_HEIGHT_M / 2),
            outline="white", width=2
        )
        self.canvas.create_line(
            *self.world_to_canvas(0, COURT_HEIGHT_M / 2),
            *self.world_to_canvas(0, -COURT_HEIGHT_M / 2),
            fill="white", width=2
        )
        center_circle_radius_m = 0.5
        self.canvas.create_oval(
            *self.world_to_canvas(-center_circle_radius_m,
                                  center_circle_radius_m),
            *self.world_to_canvas(center_circle_radius_m, -
                                  center_circle_radius_m),
            outline="white", width=2
        )

    def world_to_canvas(self, x_m, y_m):
        scale_x = (CANVAS_WIDTH - 2 * FIELD_MARGIN) / COURT_WIDTH_M
        scale_y = (CANVAS_HEIGHT - 2 * FIELD_MARGIN) / COURT_HEIGHT_M
        scale = min(scale_x, scale_y)

        canvas_x = CANVAS_WIDTH / 2 + x_m * scale
        canvas_y = CANVAS_HEIGHT / 2 - y_m * scale
        return canvas_x, canvas_y

    def update_game_tab_full(self):  # メソッド名を変更し、保持データから描画
        # チームカラー更新
        self.team_color_label.config(
            text=f"Team: {self.latest_team_color.capitalize()}")

        current_time = time.time()
        active_robot_ids = set()

        # 保持している全ロボットのステータスを描画
        # list()でコピーしてイテレート中の変更に対応
        for robot_id, r_status in list(self.all_robots_status.items()):
            # 一定時間データが更新されないロボットは表示から消す（タイムアウト処理）
            if robot_id in self.last_data_received_time and \
               current_time - self.last_data_received_time[robot_id] > (config.SOCKET_TIMEOUT + 1.0):  # SOCKET_TIMEOUTより少し長め
                print(
                    f"GUI: Robot {robot_id} timed out. Removing from display.")
                if robot_id in self.robot_items:
                    self.canvas.delete(self.robot_items[robot_id]['body'])
                    self.canvas.delete(self.robot_items[robot_id]['dir'])
                    self.canvas.delete(self.robot_items[robot_id]['id_text'])
                    del self.robot_items[robot_id]
                del self.all_robots_status[robot_id]  # 状態からも削除
                if robot_id in self.last_data_received_time:
                    del self.last_data_received_time[robot_id]
                continue  # 次のロボットへ

            active_robot_ids.add(robot_id)
            pos_m = r_status.get("pos")
            angle_deg = r_status.get("angle")

            if pos_m is None or angle_deg is None:
                continue

            cx, cy = self.world_to_canvas(pos_m[0], pos_m[1])
            angle_rad = math.radians(angle_deg)
            line_len = ROBOT_RADIUS_GUI * 1.5
            end_x = cx + line_len * math.cos(angle_rad)
            end_y = cy - line_len * math.sin(angle_rad)

            robot_color = "yellow" if self.latest_team_color == "yellow" else "blue"

            if robot_id not in self.robot_items:
                body = self.canvas.create_oval(cx - ROBOT_RADIUS_GUI, cy - ROBOT_RADIUS_GUI,
                                               cx + ROBOT_RADIUS_GUI, cy + ROBOT_RADIUS_GUI,
                                               fill=robot_color, outline="black")
                direction_line = self.canvas.create_line(
                    cx, cy, end_x, end_y, fill="black", width=2)
                id_text = self.canvas.create_text(
                    cx, cy, text=str(robot_id), fill="white")
                self.robot_items[robot_id] = {
                    'body': body, 'dir': direction_line, 'id_text': id_text}
            else:
                self.canvas.coords(self.robot_items[robot_id]['body'],
                                   cx - ROBOT_RADIUS_GUI, cy - ROBOT_RADIUS_GUI,
                                   cx + ROBOT_RADIUS_GUI, cy + ROBOT_RADIUS_GUI)
                self.canvas.coords(
                    self.robot_items[robot_id]['dir'], cx, cy, end_x, end_y)
                self.canvas.coords(
                    self.robot_items[robot_id]['id_text'], cx, cy)
                self.canvas.itemconfig(
                    self.robot_items[robot_id]['body'], fill=robot_color)

        # self.robot_items に残っているが、active_robot_ids にないものは削除 (タイムアウト処理でカバーされるはずだが念のため)
        ids_to_remove_on_canvas = set(
            self.robot_items.keys()) - active_robot_ids
        for rid in ids_to_remove_on_canvas:
            if rid in self.robot_items:  # 二重確認
                self.canvas.delete(self.robot_items[rid]['body'])
                self.canvas.delete(self.robot_items[rid]['dir'])
                self.canvas.delete(self.robot_items[rid]['id_text'])
                del self.robot_items[rid]

        # ボールの描画/更新
        if self.latest_ball_pos:
            bx, by = self.world_to_canvas(
                self.latest_ball_pos[0], self.latest_ball_pos[1])
            if self.ball_item is None:
                self.ball_item = self.canvas.create_oval(bx - BALL_RADIUS_GUI, by - BALL_RADIUS_GUI,
                                                         bx + BALL_RADIUS_GUI, by + BALL_RADIUS_GUI,
                                                         fill="orange", outline="black")
            else:
                self.canvas.coords(self.ball_item,
                                   bx - BALL_RADIUS_GUI, by - BALL_RADIUS_GUI,
                                   bx + BALL_RADIUS_GUI, by + BALL_RADIUS_GUI)
        elif self.ball_item is not None:
            self.canvas.delete(self.ball_item)
            self.ball_item = None

    def init_robot_tab(self):
        self.robot_info_labels = {}

        robot_tab_canvas = tk.Canvas(self.robot_frame)
        scrollbar = ttk.Scrollbar(
            self.robot_frame, orient="vertical", command=robot_tab_canvas.yview)
        self.scrollable_robot_info_frame = ttk.Frame(robot_tab_canvas)  # 参照を保持

        self.scrollable_robot_info_frame.bind(
            "<Configure>",
            lambda e: robot_tab_canvas.configure(
                scrollregion=robot_tab_canvas.bbox("all")
            )
        )

        robot_tab_canvas.create_window(
            (0, 0), window=self.scrollable_robot_info_frame, anchor="nw")
        robot_tab_canvas.configure(yscrollcommand=scrollbar.set)

        robot_tab_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 最初は空。データ受信時に動的にLabelFrameを作成

    def update_robot_tab_full(self):  # メソッド名を変更し、保持データから描画
        # 保持している全ロボットのステータスでラベルを更新または作成
        for robot_id, r_status in self.all_robots_status.items():
            if robot_id not in self.robot_info_labels:  # 初めてのロボットIDならLabelFrameとラベル群を作成
                frame = ttk.LabelFrame(
                    self.scrollable_robot_info_frame, text=f"Robot ID: {robot_id}")
                frame.pack(padx=10, pady=5, fill="x")
                labels = {}
                labels['voltage'] = ttk.Label(frame, text="Voltage: N/A")
                labels['voltage'].pack(anchor='w')
                labels['photo_front'] = ttk.Label(
                    frame, text="Photo Front: N/A")
                labels['photo_front'].pack(anchor='w')
                labels['photo_back'] = ttk.Label(frame, text="Photo Back: N/A")
                labels['photo_back'].pack(anchor='w')
                labels['ball_angle'] = ttk.Label(
                    frame, text="Ball Angle (Rel, CW): N/A")
                labels['ball_angle'].pack(anchor='w')
                labels['ball_dist'] = ttk.Label(
                    frame, text="Ball Distance (Rel): N/A")
                labels['ball_dist'].pack(anchor='w')
                self.robot_info_labels[robot_id] = {
                    'frame': frame, 'labels': labels}  # frameも保存

            # ラベル更新
            labels_dict = self.robot_info_labels[robot_id]['labels']

            voltage = r_status.get("voltage", "N/A")
            labels_dict['voltage'].config(text=f"Voltage: {voltage:.2f} V" if isinstance(
                voltage, float) else f"Voltage: {voltage}")

            photo_f = r_status.get("photo_front", "N/A")
            labels_dict['photo_front'].config(text=f"Photo Front: {photo_f}")

            photo_b = r_status.get("photo_back", "N/A")
            labels_dict['photo_back'].config(text=f"Photo Back: {photo_b}")

            ball_angle = r_status.get("ball_relative_angle")
            labels_dict['ball_angle'].config(
                text=f"Ball Angle (Rel, CW): {ball_angle:.1f}°" if ball_angle is not None else "Ball Angle (Rel, CW): N/A")

            ball_dist = r_status.get("ball_relative_distance")
            labels_dict['ball_dist'].config(
                text=f"Ball Distance (Rel): {ball_dist:.3f} m" if ball_dist is not None else "Ball Distance (Rel): N/A")

        # データが来なくなったロボットの情報をRobotタブから削除する (タイムアウト処理)
        current_time = time.time()
        robot_ids_to_remove_from_tab = []
        for robot_id_tab in list(self.robot_info_labels.keys()):
            if robot_id_tab not in self.all_robots_status:  # all_robots_status から既に消えている場合
                robot_ids_to_remove_from_tab.append(robot_id_tab)
            elif robot_id_tab in self.last_data_received_time and \
                    current_time - self.last_data_received_time[robot_id_tab] > (config.SOCKET_TIMEOUT + 1.0):
                robot_ids_to_remove_from_tab.append(robot_id_tab)

        for rid_remove in robot_ids_to_remove_from_tab:
            if rid_remove in self.robot_info_labels:
                self.robot_info_labels[rid_remove]['frame'].destroy()
                del self.robot_info_labels[rid_remove]
                print(
                    f"GUI: Robot {rid_remove} info removed from Robot Tab due to timeout or no data.")

    def init_command_tab(self):
        self.interrupt_var = tk.BooleanVar(value=False)
        interrupt_check = ttk.Checkbutton(self.command_frame, text="Enable Interrupt Commands",
                                          variable=self.interrupt_var, command=self.on_interrupt_toggle)
        interrupt_check.pack(pady=10, padx=10, anchor='w')

        stop_all_button = ttk.Button(self.command_frame, text="Send Stop All (Interrupt)",
                                     command=lambda: self.send_gui_command({"type": "interrupt_cmd", "command": "stop_all"}))
        stop_all_button.pack(pady=5, padx=10, anchor='w')

        move_robot0_button = ttk.Button(self.command_frame, text="Move Robot 0 to (0,0) (Interrupt Example)",
                                        command=lambda: self.send_gui_command({
                                            "type": "interrupt_cmd",
                                            "command": "move_to",
                                            "robot_id": 0,
                                            "target_pos": [0.0, 0.0],
                                            "target_angle": 0.0
                                        }))
        move_robot0_button.pack(pady=5, padx=10, anchor='w')

        ttk.Label(self.command_frame, text="Note: Interrupt commands are sent to the controller.\n"
                                           "Controller logic must be implemented to handle them.").pack(pady=10)

    def on_interrupt_toggle(self):
        print(f"Interrupt commands enabled: {self.interrupt_var.get()}")

    def send_gui_command(self, command_payload):
        if not self.interrupt_var.get() and command_payload.get("type") == "interrupt_cmd":
            print("Interrupt commands are disabled. Command not sent.")
            return

        if not self.cmd_sock:
            print("GUI command socket not initialized.")
            return
        try:
            command_payload["timestamp"] = int(time.time() * 1000)
            json_data = json.dumps(command_payload)
            byte_data = json_data.encode('utf-8')
            self.cmd_sock.sendto(
                byte_data, (config.CONTROLLER_GUI_LISTEN_IP, config.CONTROLLER_GUI_LISTEN_PORT))
            print(f"Sent GUI command: {command_payload}")
        except socket.error as e:
            print(f"Failed to send GUI command: {e}")
        except TypeError as e:
            print(f"Error encoding GUI command: {e}")

    def receive_data(self):
        while self.running:
            try:
                data, addr = self.udp_sock.recvfrom(config.BUFFER_SIZE)
                json_string = data.decode('utf-8')
                parsed_data = json.loads(json_string)
                if parsed_data.get("type") == "gui_update":
                    self.data_queue.put(parsed_data)
            except socket.timeout:
                continue
            except json.JSONDecodeError:
                pass
            except Exception as e:
                if self.running:
                    print(f"GUI receiver error: {e}")
                break
        print("GUI receiver thread stopped.")

    def process_queued_data(self):
        """キュー内のデータを処理して内部状態を更新する"""
        data_updated = False
        while not self.data_queue.empty():
            try:
                data = self.data_queue.get_nowait()
                data_updated = True  # データを受信したら更新フラグを立てる

                # チームカラーを更新 (最後に受信したものを採用)
                self.latest_team_color = data.get(
                    "team_color", self.latest_team_color)

                # ボール情報を更新 (最後に受信したものを採用)
                # ball_pos が None の場合もあるので、Noneでない場合のみ更新する、
                # または、常に上書きして、最後にボールが見えたコントローラーの情報を採用する
                if data.get("ball_pos") is not None:
                    self.latest_ball_pos = data.get("ball_pos")
                # もし、どのコントローラーからもボールが見えないことを知りたいなら、
                # 一定時間ボール情報が来なければ self.latest_ball_pos = None にする処理が必要

                # ロボットステータスを更新
                # "robots_status" はリストだが、コントローラーからは1要素のリストで送られてくる想定
                robots_status_list = data.get("robots_status", [])
                for r_status in robots_status_list:
                    robot_id = r_status.get("id")
                    if robot_id is not None:
                        self.all_robots_status[robot_id] = r_status
                        # 最終受信時刻を記録
                        self.last_data_received_time[robot_id] = time.time()

            except queue.Empty:
                break  # キューが空になった
        return data_updated

    def update_gui(self):
        data_was_processed = self.process_queued_data()

        # データが処理されたか、または一定時間ごとに描画を強制するなどのロジックも可能
        # ここでは、データ処理があった場合にGUIを更新する
        # if data_was_processed: # この条件だとデータが来ない間は更新されない
        # 常に更新してタイムアウト処理を有効にする
        self.update_game_tab_full()  # 保持している全データでGameタブを更新
        self.update_robot_tab_full()  # 保持している全データでRobotタブを更新

        if self.running:
            self.master.after(
                int(config.GUI_UPDATE_INTERVAL * 1000), self.update_gui)

    def on_closing(self):
        print("Closing GUI...")
        self.running = False
        if self.udp_sock:
            self.udp_sock.close()
        if self.cmd_sock:
            self.cmd_sock.close()
        self.master.destroy()


if __name__ == '__main__':
    import os
    os.makedirs("lib", exist_ok=True)
    os.makedirs("algorithm", exist_ok=True)
    os.makedirs("strategy", exist_ok=True)

    if not os.path.exists("lib/my_math.py"):
        with open("lib/my_math.py", "w") as f:
            f.write("""
def NormalizeDeg180(angle):
    angle = angle % 360
    if angle > 180:
        angle -= 360
    return angle

def NormalizeDeg360(angle):
    return angle % 360
""")
    for fname in ["basic_move.py", "ball_placement.py", "attack.py", "pass_ball.py"]:
        if not os.path.exists(f"algorithm/{fname}"):
            with open(f"algorithm/{fname}", "w") as f:
                if fname == "basic_move.py":
                    f.write("""
class BasicMove:
    def __init__(self, state):
        self.state = state
    def move_to_target(self, target_pos, target_angle):
        print(f"[BasicMove] Move to {target_pos} face {target_angle}")
        return {"cmd": {"move_speed": 0}} 
    def turn_to_angle(self, target_angle):
        print(f"[BasicMove] Turn to {target_angle}")
        return {"cmd": {"face_angle": target_angle}} 
""")
                elif fname == "ball_placement.py":
                    f.write("""
class BallPlacement:
    def __init__(self, state, basic_move):
        self.state = state
        self.basic_move = basic_move
    def ball_placement(self, target_pos):
        print(f"[BallPlacement] Place ball at {target_pos}")
        return {"cmd": {"move_speed": 0}} 
""")
                elif fname == "attack.py":
                    f.write("""
class Attack:
    def __init__(self, state, basic_move):
        self.state = state
        self.basic_move = basic_move
    def attack(self):
        print(f"[Attack] Attacking")
        return {"cmd": {"kick": True}} 
""")
                elif fname == "pass_ball.py":
                    f.write("""
class PassBall:
    def __init__(self, state, basic_move):
        self.state = state
        self.basic_move = basic_move
    def pass_to_target(self, target_robot_id):
        print(f"[PassBall] Pass to robot {target_robot_id}")
        return {"cmd": {"kick": True, "kick_power": 50}} 
""")

    if not os.path.exists("strategy/strategy_maneger.py"):
        with open("strategy/strategy_maneger.py", "w") as f:
            f.write("""
import time
import math # for dummy move_to
import config

class StrategyManager:
    def __init__(self, robot_controllers, udp_communicator):
        self.robot_controllers = robot_controllers
        self.udp_comm = udp_communicator 
        self.current_strategy = "stop"
        self.game_state = "HALT"
        self.interrupt_mode = False 
        self.interrupt_command_active = False

    def handle_game_command(self, command_data):
        ref_command = command_data.get("command", "UNKNOWN").upper()
        print(f"[StrategyManager] Received Game Command: {ref_command}")
        self.game_state = ref_command
        if ref_command == "NORMAL_START":
            self.current_strategy = "attack"
            self.interrupt_mode = False # Game command should override GUI interrupt
            self.interrupt_command_active = False
        elif ref_command in ["STOP", "HALT"]:
            self.current_strategy = "stop"
            self.interrupt_mode = False
            self.interrupt_command_active = False
        elif "BALL_PLACEMENT" in ref_command:
            self.current_strategy = "ball_placement"
            self.interrupt_mode = False
            self.interrupt_command_active = False

    def handle_gui_command(self, command_data):
        print(f"[StrategyManager] Received GUI Command: {command_data}")
        cmd_type = command_data.get("type")
        if cmd_type == "interrupt_cmd":
            # Check if GUI is allowed to interrupt current game state
            if self.game_state in ["HALT", "STOP"]: # Only allow interrupt if game is stopped/halted
                self.interrupt_mode = True 
                self.process_interrupt_command(command_data)
            else:
                print(f"[StrategyManager] GUI Interrupt ignored. Game state is {self.game_state}")


    def process_interrupt_command(self, gui_cmd):
        command = gui_cmd.get("command")
        robot_id = gui_cmd.get("robot_id")
        
        self.interrupt_command_active = True 

        if command == "stop_all":
            for rc_id, rc in self.robot_controllers.items():
                rc.send_stop_command()
            # self.interrupt_mode = False # Stop後は割り込みモード自体は維持し、次のコマンドを待つか、解除するかは設計次第
            self.interrupt_command_active = False # コマンド実行は完了

        elif command == "move_to":
            if robot_id in self.robot_controllers:
                rc = self.robot_controllers[robot_id]
                target_pos = gui_cmd.get("target_pos")
                target_angle = gui_cmd.get("target_angle", rc.state.robot_dir_angle or 0)
                
                move_cmd_data = {
                    "ts": int(time.time() * 1000),
                    "cmd": {
                        "move_angle": 0, # Placeholder
                        "move_speed": config.MAX_SPEED * 0.3, 
                        "move_acce": 0,
                        "face_angle": target_angle,
                        "stop": False, "kick": False, "dribble": False,
                        "vision_angle": rc.state.robot_dir_angle # Always send current vision angle
                    }
                }
                if rc.state.robot_pos and target_pos:
                    dx = target_pos[0] - rc.state.robot_pos[0]
                    dy = target_pos[1] - rc.state.robot_pos[1]
                    # ターゲットへの角度を計算 (X軸0度、CCW正)
                    angle_to_target_rad = math.atan2(dy, dx)
                    move_cmd_data["cmd"]["move_angle"] = math.degrees(angle_to_target_rad)
                else: # ロボット位置が不明な場合は正面に移動（など、適切なフォールバック）
                    move_cmd_data["cmd"]["move_angle"] = rc.state.robot_dir_angle or 0


                print(f"Sending INTERRUPT move_to {target_pos} for robot {robot_id} with cmd: {move_cmd_data}")
                rc.send_command(move_cmd_data)
                # move_toのような一度きりのコマンドの場合、activeフラグはすぐに倒す
                self.interrupt_command_active = False 
            else: # target robot_id not found
                self.interrupt_command_active = False


    def update_strategy_and_control(self, vision_data):
        if self.interrupt_mode and self.interrupt_command_active:
            # 割り込みコマンドが現在アクティブに「実行中」の場合 (例: 連続的なGUI操作など) はスキップ。
            # 今回の move_to や stop_all は一度送ったら終わりなので、
            # interrupt_command_active はすぐに False になる想定。
            # interrupt_mode が True の間は、GUIからの次のコマンドを待つ状態。
            return
        
        if self.interrupt_mode and not self.interrupt_command_active:
            # 割り込みモードだが、現在実行中の割り込みコマンドがない場合。
            # ここでは何もしないでGUIからの次のコマンドを待つ。
            # もしGUIから一定時間コマンドが来なければ割り込みモードを解除するなどのタイムアウト処理も考えられる。
            # 例: 停止コマンドだけ送って待機状態にする。
            for rc in self.robot_controllers.values():
                 if not rc.state.robot_pos: # Visionが取れてないならStopを送り続ける
                    rc.send_stop_command()
            return


        # 通常の戦略実行 (interrupt_mode == False の場合)
        if self.current_strategy == "stop":
            for rc in self.robot_controllers.values():
                rc.send_stop_command()
        elif self.current_strategy == "attack":
            if 0 in self.robot_controllers:
                rc0 = self.robot_controllers[0]
                rc0.mode = 'attack' 
                # attack_cmd = rc0.attack() # rc0.attack() がコマンド辞書を返す想定
                # ダミーコマンド
                attack_cmd = {"ts": int(time.time()*1000), "cmd": {"kick": True, "dribble": True, "move_speed": 0, "vision_angle": rc0.state.robot_dir_angle}}
                if attack_cmd:
                     rc0.send_command(attack_cmd)
            for i in range(1, config.NUM_ROBOTS):
                if i in self.robot_controllers:
                    self.robot_controllers[i].send_stop_command() 

        elif self.current_strategy == "ball_placement":
            if 0 in self.robot_controllers:
                rc0 = self.robot_controllers[0]
                rc0.mode = 'ball_placement'
                # placement_cmd = rc0.ball_placement([0.0,0.0]) 
                # ダミーコマンド
                placement_cmd = {"ts": int(time.time()*1000), "cmd": {"move_speed": 0, "vision_angle": rc0.state.robot_dir_angle}} # 停止するだけ
                if placement_cmd:
                    rc0.send_command(placement_cmd)
            for i in range(1, config.NUM_ROBOTS):
                if i in self.robot_controllers:
                    self.robot_controllers[i].send_stop_command()
""")

    root = tk.Tk()
    gui = RobotGUI(root)
    root.mainloop()
