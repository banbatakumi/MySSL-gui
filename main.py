import sim_params as params
import config
import collections
import time
import json
import socket
import threading
import math
import sys
import pygame


# configとsim_paramsをインポート


# --- UDPデータ受信リスナークラス ---
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

# --- GUIクラス ---


class GUI:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.current_screen_width_px = config.INITIAL_SCREEN_WIDTH_PX
        self.current_screen_height_px = config.INITIAL_SCREEN_HEIGHT_PX
        self.current_screen_padding_px = config.INITIAL_SCREEN_PADDING_PX
        self.current_pixels_per_meter = config.INITIAL_PIXELS_PER_METER

        # GUIウィンドウの初期化
        self.screen = pygame.display.set_mode(
            (self.current_screen_width_px, self.current_screen_height_px),
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Robot Soccer GUI")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16)
        self.running = True

        self.views = ['Match State', 'Robot States', 'Emergency Commands']
        self.current_view_index = 0

        # ボタンの高さと間隔
        self.button_height = 40
        self.button_spacing = 10
        self.button_width = 0

        # コート中央寄せのためのXオフセットを初期化
        self.x_offset_for_centering_px = 0

        # デバッグ表示フラグ (mキーで切り替え)
        self.show_debug_vectors = True

        self._update_drawing_parameters()

        # UDPリスナーの初期化と開始
        self.udp_listener = GUIUDPListener(
            config.CONTROLLER_IP, config.GUI_LISTEN_PORT)
        self.udp_listener.start()

        # 緊急コマンド送信用のUDPソケット
        self.emergency_sender_socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)

    def _update_drawing_parameters(self):
        # スクリーンサイズ変更時に描画関連のパラメータを更新
        self.current_screen_width_px = self.screen.get_width()
        self.current_screen_height_px = self.screen.get_height()

        # トップバーの占有する高さ (ボタンの上下マージンを含む)
        self.top_bar_total_height_px = self.button_height + 2 * self.button_spacing

        # コンテンツ描画領域の開始Y座標 (トップバーの下 + 全体のパディング)
        self.content_start_y_px = self.top_bar_total_height_px + \
            self.current_screen_padding_px

        # パディングを考慮したワールド表示領域のピクセル幅/高さ
        effective_width_px = self.current_screen_width_px - \
            2 * self.current_screen_padding_px
        effective_height_px = self.current_screen_height_px - \
            self.content_start_y_px - self.current_screen_padding_px  # トップバーの高さを考慮

        # ワールド座標での表示領域の幅/高さ (コート + 壁オフセット)
        world_display_width_m = config.COURT_WIDTH_M + 2 * params.WALL_OFFSET_M
        world_display_height_m = config.COURT_HEIGHT_M + 2 * params.WALL_OFFSET_M

        if world_display_width_m > 0 and world_display_height_m > 0 and effective_width_px > 0 and effective_height_px > 0:
            ppm_w = effective_width_px / world_display_width_m
            ppm_h = effective_height_px / world_display_height_m
            self.current_pixels_per_meter = min(ppm_w, ppm_h)
        else:
            self.current_pixels_per_meter = 1.0  # フォールバック値

        if self.current_pixels_per_meter <= 0:
            self.current_pixels_per_meter = 1.0  # フォールバック値

        # コート中央寄せのためのXオフセットを計算
        world_drawing_width_px = world_display_width_m * self.current_pixels_per_meter
        self.x_offset_for_centering_px = (
            effective_width_px - world_drawing_width_px) / 2.0
        if self.x_offset_for_centering_px < 0:  # 画面がワールド描画領域より狭い場合はオフセットしない
            self.x_offset_for_centering_px = 0

        # ボタンの幅を画面サイズに合わせて再計算
        num_buttons = len(self.views)
        total_spacing_width = (num_buttons + 1) * self.button_spacing
        available_width = self.current_screen_width_px - total_spacing_width
        self.button_width = max(1, available_width // num_buttons)

    def world_to_screen_pos(self, x_m: float, y_m: float) -> tuple[int, int]:
        # ワールド座標(Y軸上向き)をスクリーン座標(Y軸下向き)に変換
        # フィールド全体の描画領域の左下端のワールド座標を計算
        world_origin_x_m = -(config.COURT_WIDTH_M / 2.0 + params.WALL_OFFSET_M)
        world_origin_y_m = -(config.COURT_HEIGHT_M /
                             2.0 + params.WALL_OFFSET_M)

        # スクリーン座標のX位置: 左端パディング + 中央寄せオフセット + (ワールド座標からの相対位置) * ppm
        screen_x = self.current_screen_padding_px + self.x_offset_for_centering_px + \
            (x_m - world_origin_x_m) * self.current_pixels_per_meter

        # スクリーン座標のY位置: コンテンツ領域上端 + コンテンツ描画高さ - (ワールド座標からの相対位置) * ppm
        content_drawing_height = self.current_screen_height_px - \
            self.content_start_y_px - self.current_screen_padding_px
        screen_y = self.content_start_y_px + content_drawing_height - \
            (y_m - world_origin_y_m) * self.current_pixels_per_meter

        return int(screen_x), int(screen_y)

    def draw_button(self, text, x, y, width, height, is_selected):
        # ボタンの描画
        color = (100, 100, 100) if not is_selected else (150, 150, 150)
        pygame.draw.rect(self.screen, color, (x, y, width, height))
        pygame.draw.rect(self.screen, (200, 200, 200),
                         (x, y, width, height), 2)  # 枠線

        text_surf = self.font.render(text, True, config.COLOR_TEXT)
        text_rect = text_surf.get_rect(center=(x + width / 2, y + height / 2))
        self.screen.blit(text_surf, text_rect)
        return pygame.Rect(x, y, width, height)

    def draw_top_bar(self):
        # トップバー領域の背景を描画
        pygame.draw.rect(self.screen, config.COLOR_BACKGROUND,
                         (0, 0, self.current_screen_width_px, self.top_bar_total_height_px))

        # トップバーのボタンを描画
        start_x = self.button_spacing
        for i, view_name in enumerate(self.views):
            self.draw_button(view_name,
                             start_x + i * (self.button_width +
                                            self.button_spacing),
                             self.button_spacing,  # Y座標は画面上部からのマージン
                             self.button_width,
                             self.button_height,
                             i == self.current_view_index)

        # 上部バーとコートの間に白い線を描画
        line_y = self.top_bar_total_height_px
        pygame.draw.line(self.screen, config.COLOR_WHITE, (0, line_y),
                         (self.current_screen_width_px, line_y), 1)

    def draw_field(self):
        # フィールドの描画
        hw_m, hh_m = config.COURT_WIDTH_M / 2.0, config.COURT_HEIGHT_M / 2.0

        # フィールドラインの左上スクリーン座標
        field_tl_x_m = -hw_m
        field_tl_y_m = hh_m
        tl_lines_sx, tl_lines_sy = self.world_to_screen_pos(
            field_tl_x_m, field_tl_y_m)

        field_lines_w_px = max(
            1, int(config.COURT_WIDTH_M * self.current_pixels_per_meter))
        field_lines_h_px = max(
            1, int(config.COURT_HEIGHT_M * self.current_pixels_per_meter))

        if field_lines_w_px > 0 and field_lines_h_px > 0:
            pygame.draw.rect(self.screen, config.COLOR_FIELD_LINES,
                             (tl_lines_sx, tl_lines_sy,
                              field_lines_w_px, field_lines_h_px),
                             config.FIELD_MARKING_WIDTH_PX)

        # センターサークル
        cx_s, cy_s = self.world_to_screen_pos(0, 0)
        center_circle_radius_m = 0.25  # SSLセンターサークル半径
        cc_r_px = int(center_circle_radius_m * self.current_pixels_per_meter)
        if cc_r_px >= config.FIELD_MARKING_WIDTH_PX:
            pygame.draw.circle(self.screen, config.COLOR_FIELD_LINES,
                               (cx_s, cy_s), cc_r_px, config.FIELD_MARKING_WIDTH_PX)
        elif cc_r_px > 0:
            pygame.draw.circle(
                self.screen, config.COLOR_FIELD_LINES, (cx_s, cy_s), cc_r_px)

        # センターライン
        cl_top_s = self.world_to_screen_pos(0, hh_m)
        cl_bot_s = self.world_to_screen_pos(0, -hh_m)
        pygame.draw.line(self.screen, config.COLOR_FIELD_LINES,
                         cl_top_s, cl_bot_s, config.FIELD_MARKING_WIDTH_PX)

        # 壁
        wall_line_thickness_px = config.WALL_LINE_WIDTH_PX
        wall_top_y_m = config.COURT_HEIGHT_M / 2.0 + params.WALL_OFFSET_M
        wall_bottom_y_m = - (config.COURT_HEIGHT_M /
                             2.0 + params.WALL_OFFSET_M)
        wall_left_x_m = - (config.COURT_WIDTH_M / 2.0 + params.WALL_OFFSET_M)
        wall_right_x_m = config.COURT_WIDTH_M / 2.0 + params.WALL_OFFSET_M

        wall_top_left_s = self.world_to_screen_pos(wall_left_x_m, wall_top_y_m)
        wall_top_right_s = self.world_to_screen_pos(
            wall_right_x_m, wall_top_y_m)
        wall_bottom_left_s = self.world_to_screen_pos(
            wall_left_x_m, wall_bottom_y_m)
        wall_bottom_right_s = self.world_to_screen_pos(
            wall_right_x_m, wall_bottom_y_m)

        pygame.draw.line(self.screen, config.COLOR_WALLS,
                         wall_top_left_s, wall_top_right_s, wall_line_thickness_px)
        pygame.draw.line(self.screen, config.COLOR_WALLS, wall_bottom_left_s,
                         wall_bottom_right_s, wall_line_thickness_px)
        pygame.draw.line(self.screen, config.COLOR_WALLS,
                         wall_top_left_s, wall_bottom_left_s, wall_line_thickness_px)
        pygame.draw.line(self.screen, config.COLOR_WALLS, wall_top_right_s,
                         wall_bottom_right_s, wall_line_thickness_px)

    def draw_robot(self, robot_data, color):
        if robot_data and robot_data["pos"] and robot_data["angle"] is not None:
            x, y = robot_data["pos"]
            # robot_data["angle"] はシミュレータからの角度データ。
            # Pygameの描画はX軸正を0度、Y軸下向きが正で、CW正に回転します。
            # ここでは受信データをそのままPygameに渡すことで、
            # シミュレータの角度定義が「X軸正を0度、CW正」であれば正しく描画されます。
            angle_for_pygame_rad = math.radians(robot_data["angle"])

            robot_radius_px = int(params.ROBOT_RADIUS_M *
                                  self.current_pixels_per_meter)
            if robot_radius_px < 1:
                robot_radius_px = 1

            center_x_s, center_y_s = self.world_to_screen_pos(x, y)

            # ロボット本体 (塗りつぶし)
            pygame.draw.circle(self.screen, color, (center_x_s, center_y_s),
                               robot_radius_px)

            # ロボットの向きを示す線
            front_len = robot_radius_px * 0.8
            front_x = center_x_s + front_len * math.cos(angle_for_pygame_rad)
            front_y = center_y_s + front_len * math.sin(angle_for_pygame_rad)
            pygame.draw.line(self.screen, config.COLOR_ROBOT_FRONT, (center_x_s, center_y_s), (int(
                front_x), int(front_y)), config.ROBOT_OUTLINE_WIDTH_PX + 1)

            # ロボットID (白文字)
            id_surf = self.font.render(
                str(robot_data["id"]), True, config.COLOR_WHITE)
            id_rect = id_surf.get_rect(center=(center_x_s, center_y_s))
            self.screen.blit(id_surf, id_rect)

    def draw_ball(self, ball_pos):
        if ball_pos:
            x, y = ball_pos
            ball_radius_px = int(params.BALL_RADIUS_M *
                                 self.current_pixels_per_meter)
            if ball_radius_px < 1:
                ball_radius_px = 1

            center_x_s, center_y_s = self.world_to_screen_pos(x, y)
            pygame.draw.circle(self.screen, config.COLOR_BALL,
                               (center_x_s, center_y_s), ball_radius_px)

    def draw_robot_velocity_arrow(self, robot_data):
        """ロボットの目標速度を矢印で描画する"""
        if "target_move_angle" in robot_data and \
           "target_move_speed" in robot_data and \
           robot_data["pos"] is not None:

            vx = math.cos(math.radians(robot_data["target_move_angle"] + robot_data["angle"])) * \
                robot_data["target_move_speed"]
            vy = math.sin(math.radians(robot_data["target_move_angle"] + robot_data["angle"])) * \
                robot_data["target_move_speed"]

            # --- デバッグ出力 ---
            print(
                f"target_move_angle: {robot_data['target_move_angle']:.2f}°, target_move_speed: {robot_data['target_move_speed']:.2f} m/s")
            # print(
            #     f"Robot ID {robot_data.get('id', 'N/A')}: vx={vx:.5f}, vy={vy:.5f}")
            # --- ここまで ---

            # 速度がほぼゼロの場合は矢印を描画しない
            if abs(vx) < 1e-6 and abs(vy) < 1e-6:
                return

            robot_x_m, robot_y_m = robot_data["pos"]
            start_x_s, start_y_s = self.world_to_screen_pos(
                robot_x_m, robot_y_m)

            # 速度ベクトルの大きさをピクセルに変換
            velocity_magnitude_px = math.sqrt(
                vx**2 + vy**2) * self.current_pixels_per_meter * config.VELOCITY_ARROW_SCALE

            # 最小長を適用して、小さすぎる矢印を見えるようにする
            if velocity_magnitude_px < config.MIN_VELOCITY_ARROW_LENGTH_PX:
                velocity_magnitude_px = config.MIN_VELOCITY_ARROW_LENGTH_PX

            # --- デバッグ出力 ---
            print(f"  Calculated length: {velocity_magnitude_px:.5f}px")
            # --- ここまで ---

            # 矢印の方向をPygameの座標系に合わせて計算
            # atan2(y, x) はX軸正を0度、反時計回り正の角度を返す。
            # PygameのY軸は下向きが正なので、描画において数学的なCCW正の角度をそのまま使うと、
            # 描画上の回転が反転して見える (CW正になる)。
            # したがって、`atan2(vy, vx)`はPygameの描画において、
            # ワールド座標のX軸正を0度、CW正の方向として解釈される。
            arrow_angle_rad = math.atan2(vy, vx)

            # 矢印の終点
            end_x_s = start_x_s + velocity_magnitude_px * \
                math.cos(arrow_angle_rad)
            end_y_s = start_y_s + velocity_magnitude_px * \
                math.sin(arrow_angle_rad)

            # 矢印本体
            pygame.draw.line(self.screen, config.COLOR_DEBUG_VECTOR,
                             # 太さ2
                             (start_x_s, start_y_s), (int(end_x_s), int(end_y_s)), 2)

            # 矢印のヘッド
            arrowhead_size = 8  # 矢印ヘッドのサイズ（ピクセル）
            arrowhead_angle = math.pi / 6  # ヘッドの開き角度（30度）

            # 矢印の先端から少し戻った点を計算
            # これは矢印の頭を三角形で描画するための処理
            back_x = end_x_s - arrowhead_size * math.cos(arrow_angle_rad)
            back_y = end_y_s - arrowhead_size * math.sin(arrow_angle_rad)

            # 矢印ヘッドの2つのポイント
            # back_x, back_y から arrowhead_size の長さで、arrow_angle_rad から +/- arrowhead_angle の方向に伸びる点
            point1_x = end_x_s - arrowhead_size * \
                math.cos(arrow_angle_rad - arrowhead_angle)
            point1_y = end_y_s - arrowhead_size * \
                math.sin(arrow_angle_rad - arrowhead_angle)
            point2_x = end_x_s - arrowhead_size * \
                math.cos(arrow_angle_rad + arrowhead_angle)
            point2_y = end_y_s - arrowhead_size * \
                math.sin(arrow_angle_rad + arrowhead_angle)

            pygame.draw.polygon(self.screen, config.COLOR_DEBUG_VECTOR,
                                [(int(end_x_s), int(end_y_s)), (int(point1_x), int(point1_y)), (int(point2_x), int(point2_y))])

    def draw_match_state(self, yellow_robots, blue_robots, ball_pos):
        # Match State画面の描画
        self.draw_field()
        for robot_id, robot_data in yellow_robots.items():
            self.draw_robot(robot_data, config.COLOR_YELLOW_ROBOT)
            if self.show_debug_vectors:  # mキーが押されている場合のみ矢印を描画
                self.draw_robot_velocity_arrow(robot_data)
        for robot_id, robot_data in blue_robots.items():
            self.draw_robot(robot_data, config.COLOR_BLUE_ROBOT)
            if self.show_debug_vectors:  # mキーが押されている場合のみ矢印を描画
                self.draw_robot_velocity_arrow(robot_data)
        self.draw_ball(ball_pos)

    def draw_robot_states(self, yellow_robots, blue_robots):
        # Robot States画面の描画
        # トップバーの下から開始するためのYオフセット
        y_offset = self.content_start_y_px + 20  # コンテンツ開始Y座標からさらにマージン

        header_text = ["ID", "Team", "Pos (m)", "Angle (deg)", "Voltage (V)",
                       "Photo F", "Photo B", "Ball Rel Angle (deg)", "Ball Dist (m)"]
        col_widths = [50, 70, 150, 120, 100, 80, 80, 150, 100]  # カラムの幅

        # ヘッダーの描画
        x_offset = 10
        for i, header in enumerate(header_text):
            text_surf = self.font.render(header, True, config.COLOR_TEXT)
            self.screen.blit(text_surf, (x_offset + 5, y_offset + 5))
            x_offset += col_widths[i]

        y_offset += 30  # ヘッダーの高さ

        all_robots = []
        for robot_id_str, data in yellow_robots.items():
            all_robots.append(("yellow", data))
        for robot_id_str, data in blue_robots.items():
            all_robots.append(("blue", data))

        # ロボットデータをソート (ID順)
        all_robots.sort(key=lambda x: (x[0], int(x[1]["id"])))

        for team, robot_data in all_robots:
            x_offset = 10
            # データ行の描画
            id_str = str(robot_data.get("id", "N/A"))
            pos_str = f"({robot_data['pos'][0]:.2f}, {robot_data['pos'][1]:.2f})" if robot_data.get(
                "pos") else "N/A"
            # ロボットの角度は、シミュレータからのデータそのままの値で表示
            angle_str = f"{robot_data['angle']:.1f}" if robot_data.get(
                "angle") is not None else "N/A"
            voltage_str = f"{robot_data.get('voltage', 0.0):.2f}"
            photo_f_str = "ON" if robot_data.get("photo_front") else "OFF"
            photo_b_str = "ON" if robot_data.get("photo_back") else "OFF"
            ball_rel_angle_str = f"{robot_data.get('ball_relative_angle', 0.0):.1f}" if robot_data.get(
                'ball_relative_angle') is not None else "N/A"
            ball_dist_str = f"{robot_data.get('ball_relative_distance', 0.0):.2f}" if robot_data.get(
                'ball_relative_distance') is not None else "N/A"

            row_data = [id_str, team.capitalize(), pos_str, angle_str, voltage_str,
                        photo_f_str, photo_b_str, ball_rel_angle_str, ball_dist_str]

            for i, data_str in enumerate(row_data):
                text_surf = self.font.render(data_str, True, config.COLOR_TEXT)
                self.screen.blit(text_surf, (x_offset + 5, y_offset + 5))
                x_offset += col_widths[i]
            y_offset += 30

        # 最新のデータタイムスタンプ表示
        timestamp = self.udp_listener.latest_data["timestamp"]
        ts_text = f"Last Update: {timestamp / 1000:.2f} s" if timestamp > 0 else "Last Update: N/A"
        ts_surf = self.font.render(ts_text, True, config.COLOR_TEXT)
        self.screen.blit(ts_surf, (10, y_offset + 20))

    def draw_emergency_commands(self):
        # Emergency Commands画面の描画
        # トップバーの下から開始するためのYオフセット
        y_offset = self.content_start_y_px + 30

        # コマンドボタンの定義
        commands = [
            ("Stop All Robots", "stop_all_robots"),
            ("Reset Ball Position", "reset_ball"),
            ("Toggle Debug Vectors", "toggle_debug_vectors")
        ]

        button_x = (self.current_screen_width_px - 200) // 2  # 中央に配置
        button_cmd_width = 200
        button_cmd_height = 50
        button_cmd_spacing = 20

        for text, command_key in commands:
            cmd_rect = self.draw_button(
                text, button_x, y_offset, button_cmd_width, button_cmd_height, False)
            if self.is_mouse_over(cmd_rect):
                pygame.draw.rect(self.screen, (200, 200, 0),
                                 cmd_rect, 3)  # ホバーエフェクト

            y_offset += (button_cmd_height + button_cmd_spacing)

    def send_emergency_command(self, command_type):
        # 緊急コマンドをシミュレータに送信
        payload = {
            "type": "emergency_command",
            "timestamp": int(time.time() * 1000),
            "command": command_type
        }
        try:
            message = json.dumps(payload).encode('utf-8')
            self.emergency_sender_socket.sendto(
                message, (config.CONTROLLER_IP, config.EMERGENCY_COMMAND_SEND_PORT))
            print(f"Sent emergency command: {command_type}")
        except Exception as e:
            print(f"Error sending emergency command: {e}")

    def is_mouse_over(self, rect):
        # マウスが指定のRect上にあるか判定
        return rect.collidepoint(pygame.mouse.get_pos())

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE)
                    self._update_drawing_parameters()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # 左クリック
                        # トップバーのボタンクリック判定
                        start_x = self.button_spacing
                        for i, view_name in enumerate(self.views):
                            rect = pygame.Rect(start_x + i * (self.button_width + self.button_spacing),
                                               self.button_spacing,  # Y座標は画面上部からのマージン
                                               self.button_width,
                                               self.button_height)
                            if rect.collidepoint(event.pos):
                                self.current_view_index = i
                                break

                        # 緊急コマンド画面でのボタンクリック判定
                        if self.views[self.current_view_index] == 'Emergency Commands':
                            # y_offsetの計算はdraw_emergency_commandsと同じロジックを使う
                            y_offset = self.content_start_y_px + 30
                            button_x = (
                                self.current_screen_width_px - 200) // 2
                            button_cmd_width = 200
                            button_cmd_height = 50
                            button_cmd_spacing = 20

                            commands = [
                                ("Stop All Robots", "stop_all_robots"),
                                ("Reset Ball Position", "reset_ball"),
                                ("Toggle Debug Vectors", "toggle_debug_vectors")
                            ]
                            for text, command_key in commands:
                                cmd_rect = pygame.Rect(
                                    button_x, y_offset, button_cmd_width, button_cmd_height)
                                if cmd_rect.collidepoint(event.pos):
                                    self.send_emergency_command(command_key)
                                    break
                                y_offset += (button_cmd_height +
                                             button_cmd_spacing)
                elif event.type == pygame.KEYDOWN:  # キーボード入力の検出
                    if event.key == pygame.K_m:  # 'm' キーが押されたら
                        self.show_debug_vectors = not self.show_debug_vectors  # フラグをトグル
                        # 状態をコンソールに出力
                        print(
                            f"Debug vectors visibility: {self.show_debug_vectors}")

            # 画面クリア (全体を背景色で塗りつぶし)
            self.screen.fill(config.COLOR_BACKGROUND)

            # データ取得
            yellow_robots, blue_robots, ball_pos, _ = self.udp_listener.get_latest_robot_data()

            # 現在の表示モードに応じたコンテンツを描画
            # コンテンツ領域の背景を描画 (Match State以外)
            if self.views[self.current_view_index] != 'Match State':
                pygame.draw.rect(self.screen, config.COLOR_BACKGROUND,  # 背景色をそのまま使用
                                 (self.current_screen_padding_px,
                                  self.content_start_y_px,
                                  self.current_screen_width_px - 2 * self.current_screen_padding_px,
                                  self.current_screen_height_px - self.content_start_y_px - self.current_screen_padding_px))

            if self.views[self.current_view_index] == 'Match State':
                self.draw_match_state(yellow_robots, blue_robots, ball_pos)
            elif self.views[self.current_view_index] == 'Robot States':
                self.draw_robot_states(yellow_robots, blue_robots)
            elif self.views[self.current_view_index] == 'Emergency Commands':
                self.draw_emergency_commands()

            # トップバーを最後に描画 (コンテンツの上に重ねて表示)
            self.draw_top_bar()

            pygame.display.flip()
            self.clock.tick(config.FPS)

        self.cleanup()

    def cleanup(self):
        print("GUI shutting down...")
        self.udp_listener.stop()  # UDPリスナースレッドを停止
        self.emergency_sender_socket.close()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    gui = GUI()
    gui.run()
