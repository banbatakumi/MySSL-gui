
import time
import config

class StrategyManager:
    def __init__(self, robot_controllers, udp_communicator):
        self.robot_controllers = robot_controllers
        self.udp_comm = udp_communicator # GUIコマンド送信用
        self.current_strategy = "stop"
        self.game_state = "HALT"
        self.interrupt_mode = False # GUIからの割り込みコマンドを優先するか
        self.interrupt_command_active = False

    def handle_game_command(self, command_data):
        ref_command = command_data.get("command", "UNKNOWN").upper()
        print(f"[StrategyManager] Received Game Command: {ref_command}")
        self.game_state = ref_command
        # 通常のゲームコマンドに応じて戦略を切り替え
        if ref_command == "NORMAL_START":
            self.current_strategy = "attack"
        elif ref_command in ["STOP", "HALT"]:
            self.current_strategy = "stop"
        elif "BALL_PLACEMENT" in ref_command:
            self.current_strategy = "ball_placement"
            # target_pos = command_data.get("target_pos") # [x,y]
            # self.placement_target = target_pos
        # ... more states

    def handle_gui_command(self, command_data):
        print(f"[StrategyManager] Received GUI Command: {command_data}")
        cmd_type = command_data.get("type")
        if cmd_type == "interrupt_cmd":
            self.interrupt_mode = True # 割り込みモードON
            self.process_interrupt_command(command_data)


    def process_interrupt_command(self, gui_cmd):
        command = gui_cmd.get("command")
        robot_id = gui_cmd.get("robot_id") # 対象ロボットID、Noneなら全体など

        # ここでコマンドを解析し、直接ロボットコントローラーに指示を出す
        # RobotControllerに新しいメソッド(例: execute_direct_command)を作るか、
        # mode を直接書き換えて、StrategyManagerがコマンドを生成・送信する。
        # 今回は、StrategyManagerが直接コマンドを生成・送信する例：
        
        self.interrupt_command_active = True # 割り込みコマンド実行中フラグ

        if command == "stop_all":
            for rc_id, rc in self.robot_controllers.items():
                rc.send_stop_command()
            self.interrupt_mode = False # Stop後は割り込み解除することが多い
            self.interrupt_command_active = False

        elif command == "move_to":
            if robot_id in self.robot_controllers:
                rc = self.robot_controllers[robot_id]
                target_pos = gui_cmd.get("target_pos")
                target_angle = gui_cmd.get("target_angle", rc.state.robot_dir_angle or 0)
                # BasicMoveを使ってコマンド生成 (RobotController内部のbasic_moveインスタンスを使う)
                # move_cmd = rc.basic_move.move_to_target(target_pos, target_angle)
                # rc.send_command(move_cmd)
                # ダミー実装として直接値を設定するコマンド
                move_cmd_data = {
                    "ts": int(time.time() * 1000),
                    "cmd": {
                        "move_angle": rc.state.robot_dir_angle, # ひとまず現在の向きに移動
                        "move_speed": config.MAX_SPEED * 0.5, # 適当な速度
                        "move_acce": 0,
                        "face_angle": target_angle,
                        "stop": False, "kick": False, "dribble": False
                    }
                }
                # 実際には目標位置への移動角度を計算する必要がある
                if rc.state.robot_pos and target_pos:
                    dx = target_pos[0] - rc.state.robot_pos[0]
                    dy = target_pos[1] - rc.state.robot_pos[1]
                    move_cmd_data["cmd"]["move_angle"] = math.degrees(math.atan2(dy, dx))
                
                print(f"Sending INTERRUPT move_to {target_pos} for robot {robot_id}")
                rc.send_command(move_cmd_data)
                # 1回きりのコマンドならここで割り込み解除してもよい
                # self.interrupt_mode = False
                # self.interrupt_command_active = False


    def update_strategy_and_control(self, vision_data):
        if self.interrupt_mode and self.interrupt_command_active:
            # 割り込みコマンドがアクティブな間は、通常の戦略ループはスキップ
            # (ただし、割り込みコマンドが継続的なものでない場合、すぐに interrupt_command_active を False に戻す)
            # 例：move_to は一度コマンドを送ったら、あとはロボットが自律的に動くので False にしても良い
            # self.interrupt_command_active = False #
            return

        # 通常の戦略実行
        if self.current_strategy == "stop":
            for rc in self.robot_controllers.values():
                rc.send_stop_command()
        elif self.current_strategy == "attack":
            # simplistic attack: robot 0 attacks
            if 0 in self.robot_controllers:
                rc0 = self.robot_controllers[0]
                rc0.mode = 'attack' # RobotController内のモードを変更
                attack_cmd = rc0.attack() # attackメソッドがコマンドを返す
                if attack_cmd:
                     rc0.send_command(attack_cmd)
            # Other robots might do something else (e.g., support, defense)
            for i in range(1, config.NUM_ROBOTS):
                if i in self.robot_controllers:
                    self.robot_controllers[i].send_stop_command() # 他は停止（仮）

        elif self.current_strategy == "ball_placement":
            # simplistic ball placement: robot 0 places ball
            if 0 in self.robot_controllers: # and hasattr(self, 'placement_target'):
                rc0 = self.robot_controllers[0]
                rc0.mode = 'ball_placement'
                # target_pos = self.placement_target
                # 実際にはレフェリーコマンドからplacement_targetを取得する
                # ダミーで中央に配置
                placement_cmd = rc0.ball_placement([0.0,0.0]) 
                if placement_cmd:
                    rc0.send_command(placement_cmd)
            for i in range(1, config.NUM_ROBOTS):
                if i in self.robot_controllers:
                    self.robot_controllers[i].send_stop_command()
        # ... other strategies ...
