import sys
import pygame
import time
import json
import socket

import config
import params
from udp_listener import GUIUDPListener
from gui_renderer import GUIRenderer


class GUI:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.current_screen_width_px = config.INITIAL_SCREEN_WIDTH_PX
        self.current_screen_height_px = config.INITIAL_SCREEN_HEIGHT_PX
        self.current_screen_padding_px = config.INITIAL_SCREEN_PADDING_PX

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

        # デバッグ表示フラグ (mキーで切り替え)
        self.show_debug_vectors = True

        # UDPリスナーの初期化と開始
        self.udp_listener = GUIUDPListener(
            config.CONTROLLER_IP, config.GUI_LISTEN_PORT)
        self.udp_listener.start()

        # 緊急コマンド送信用のUDPソケット
        self.sender_socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)

        # レンダラーの初期化
        self.renderer = GUIRenderer(self.screen, self.font)
        self._update_drawing_parameters()  # レンダラーに初期パラメータを設定

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
        world_display_width_m = params.COURT_WIDTH_M + 2 * params.WALL_OFFSET_M
        world_display_height_m = params.COURT_HEIGHT_M + 2 * params.WALL_OFFSET_M

        current_pixels_per_meter = 1.0
        if world_display_width_m > 0 and world_display_height_m > 0 and effective_width_px > 0 and effective_height_px > 0:
            ppm_w = effective_width_px / world_display_width_m
            ppm_h = effective_height_px / world_display_height_m
            current_pixels_per_meter = min(ppm_w, ppm_h)
        else:
            current_pixels_per_meter = 1.0  # フォールバック値

        if current_pixels_per_meter <= 0:
            current_pixels_per_meter = 1.0  # フォールバック値

        # コート中央寄せのためのXオフセットを計算
        world_drawing_width_px = world_display_width_m * current_pixels_per_meter
        x_offset_for_centering_px = (
            effective_width_px - world_drawing_width_px) / 2.0
        if x_offset_for_centering_px < 0:  # 画面がワールド描画領域より狭い場合はオフセットしない
            x_offset_for_centering_px = 0

        # レンダラーの描画コンテキストを更新
        self.renderer.update_drawing_context(
            current_pixels_per_meter,
            self.current_screen_padding_px,
            self.content_start_y_px,
            x_offset_for_centering_px
        )

        # ボタンの幅を画面サイズに合わせて再計算
        num_buttons = len(self.views)
        total_spacing_width = (num_buttons + 1) * self.button_spacing
        available_width = self.current_screen_width_px - total_spacing_width
        self.button_width = max(1, available_width // num_buttons)

    def draw_button(self, text, x, y, width, height, is_selected):
        # ボタンの描画
        color = config.COLOR_BUTTON_NORMAL if not is_selected else config.COLOR_BUTTON_SELECTED
        pygame.draw.rect(self.screen, color, (x, y, width, height))
        pygame.draw.rect(self.screen, config.COLOR_WHITE,
                         (x, y, width, height), 2)  # 枠線

        text_surf = self.font.render(text, True, config.COLOR_TEXT)
        text_rect = text_surf.get_rect(center=(x + width / 2, y + height / 2))
        self.screen.blit(text_surf, text_rect)
        return pygame.Rect(x, y, width, height)

    def draw_top_bar(self):
        # トップバー領域の背景を描画
        pygame.draw.rect(self.screen, config.COLOR_TOP_BAR_BG,
                         (0, 0, self.current_screen_width_px, self.top_bar_total_height_px))

        # トップバーのボタンを描画
        start_x = self.button_spacing
        for i, view_name in enumerate(self.views):
            button_rect = self.draw_button(view_name,
                                           start_x + i *
                                           (self.button_width +
                                            self.button_spacing),
                                           self.button_spacing,
                                           self.button_width,
                                           self.button_height,
                                           i == self.current_view_index)
            # ホバーエフェクト
            if not (i == self.current_view_index) and self.is_mouse_over(button_rect):
                pygame.draw.rect(
                    self.screen, config.COLOR_BUTTON_HOVER, button_rect, 2)

        # 上部バーとコートの間に白い線を描画
        line_y = self.top_bar_total_height_px
        pygame.draw.line(self.screen, config.COLOR_WHITE, (0, line_y),
                         (self.current_screen_width_px, line_y), 1)

    def draw_match_state(self, yellow_robots, blue_robots, ball_pos):
        # Match State画面の描画はGUIRendererに委譲
        self.renderer.draw_field()
        for robot_id, robot_data in yellow_robots.items():
            self.renderer.draw_robot(robot_data, config.COLOR_YELLOW_ROBOT)
            if self.show_debug_vectors:
                self.renderer.draw_robot_velocity_arrow(robot_data)
        for robot_id, robot_data in blue_robots.items():
            self.renderer.draw_robot(robot_data, config.COLOR_BLUE_ROBOT)
            if self.show_debug_vectors:
                self.renderer.draw_robot_velocity_arrow(robot_data)
        self.renderer.draw_ball(ball_pos)

    def draw_robot_states(self, yellow_robots, blue_robots):
        # Robot States画面の描画
        # トップバーの下から開始するためのYオフセット
        y_offset = self.content_start_y_px + 20  # コンテンツ開始Y座標からさらにマージン

        header_text = ["ID", "Team", "Pos (m)", "Angle (deg)", "Voltage (V)",
                       "Photo F", "Photo B"]
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
        print(f"Total robots: {len(all_robots)}")

        # ロボットデータをソート (ID順)
        all_robots.sort(key=lambda x: (x[0], int(x[1]["id"])))

        for team, robot_data in all_robots:
            x_offset = 10
            # データ行の描画
            id_str = str(robot_data.get("id", "N/A"))
            pos_str = f"({robot_data['pos'][0]:.2f}, {robot_data['pos'][1]:.2f})" if robot_data.get(
                "pos") else "N/A"
            angle_str = f"{robot_data['angle']:.1f}" if robot_data.get(
                "angle") is not None else "N/A"
            voltage_str = f"{robot_data.get('voltage', 0.0):.2f}"
            photo_f_str = "ON" if robot_data.get("photo_front") else "OFF"
            photo_b_str = "ON" if robot_data.get("photo_back") else "OFF"

            row_data = [id_str, team.capitalize(), pos_str, angle_str, voltage_str,
                        photo_f_str, photo_b_str]

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
            ("Stop All Robots", "stop_all_robots")
        ]

        button_x = (self.current_screen_width_px - 200) // 2  # 中央に配置
        button_cmd_width = 200
        button_cmd_height = 50
        button_cmd_spacing = 20

        for text, command_key in commands:
            cmd_rect = self.draw_button(
                text, button_x, y_offset, button_cmd_width, button_cmd_height, False)
            if self.is_mouse_over(cmd_rect):
                pygame.draw.rect(self.screen, config.COLOR_BUTTON_HOVER,
                                 cmd_rect, 3)  # ホバーエフェクト

            y_offset += (button_cmd_height + button_cmd_spacing)

    def send_command(self, command_type):
        # 緊急コマンドをシミュレータに送信
        payload = {
            "type": "gui_command",
            "timestamp": int(time.time() * 1000),
            "command": command_type
        }
        try:
            message = json.dumps(payload).encode('utf-8')
            self.sender_socket.sendto(
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
                    self._update_drawing_parameters()  # レンダラーのパラメータも更新
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # 左クリック
                        # トップバーのボタンクリック判定
                        start_x = self.button_spacing
                        for i, view_name in enumerate(self.views):
                            rect = pygame.Rect(start_x + i * (self.button_width + self.button_spacing),
                                               self.button_spacing,
                                               self.button_width,
                                               self.button_height)
                            if rect.collidepoint(event.pos):
                                self.current_view_index = i
                                break

                        # 緊急コマンド画面でのボタンクリック判定
                        if self.views[self.current_view_index] == 'Emergency Commands':
                            y_offset = self.content_start_y_px + 30
                            button_x = (
                                self.current_screen_width_px - 200) // 2
                            button_cmd_width = 200
                            button_cmd_height = 50
                            button_cmd_spacing = 20

                            commands = [
                                ("Stop All Robots", "stop_all_robots")
                            ]
                            for text, command_key in commands:
                                cmd_rect = pygame.Rect(
                                    button_x, y_offset, button_cmd_width, button_cmd_height)
                                if cmd_rect.collidepoint(event.pos):
                                    self.send_command(command_key)
                                    break
                                y_offset += (button_cmd_height +
                                             button_cmd_spacing)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:
                        self.show_debug_vectors = not self.show_debug_vectors
                        print(
                            f"Debug vectors visibility: {self.show_debug_vectors}")

            # 画面クリア
            self.screen.fill(config.COLOR_BACKGROUND)

            # データ取得
            yellow_robots, blue_robots, ball_pos, _ = self.udp_listener.get_latest_robot_data()

            # コンテンツ領域の背景を描画 (Match State以外)
            if self.views[self.current_view_index] != 'Match State':
                pygame.draw.rect(self.screen, config.COLOR_CONTENT_BG,
                                 (self.current_screen_padding_px,
                                  self.content_start_y_px,
                                  self.current_screen_width_px - 2 * self.current_screen_padding_px,
                                  self.current_screen_height_px - self.content_start_y_px - self.current_screen_padding_px))

            # 現在の表示モードに応じたコンテンツを描画
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
        self.udp_listener.stop()
        self.sender_socket.close()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    gui = GUI()
    gui.run()
