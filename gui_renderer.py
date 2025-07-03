import pygame
import math
import config  # config.pyから設定をインポート
import params  # sim_params.pyから物理パラメータをインポート


class GUIRenderer:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        # 描画パラメータはGUIクラスから更新される
        self.current_pixels_per_meter = 1.0
        self.current_screen_padding_px = 0
        self.content_start_y_px = 0
        self.x_offset_for_centering_px = 0

    def update_drawing_context(self, pixels_per_meter, screen_padding_px, content_start_y_px, x_offset_for_centering_px):
        """描画に必要なコンテキストパラメータを更新する"""
        self.current_pixels_per_meter = pixels_per_meter
        self.current_screen_padding_px = screen_padding_px
        self.content_start_y_px = content_start_y_px
        self.x_offset_for_centering_px = x_offset_for_centering_px

    def world_to_screen_pos(self, x_m: float, y_m: float) -> tuple[int, int]:
        """
        ワールド座標(Y軸上向き)をスクリーン座標(Y軸下向き)に変換する。
        GUIクラスの同名メソッドをここに移動し、selfのパラメータを使用するように変更。
        """
        # フィールド全体の描画領域の左下端のワールド座標を計算
        world_display_width_m = params.COURT_WIDTH_M + 2 * params.WALL_OFFSET_M
        world_display_height_m = params.COURT_HEIGHT_M + 2 * params.WALL_OFFSET_M

        world_origin_x_m = -(world_display_width_m / 2.0)
        world_origin_y_m = -(world_display_height_m / 2.0)

        # スクリーン座標のX位置: 左端パディング + 中央寄せオフセット + (ワールド座標からの相対位置) * ppm
        screen_x = self.current_screen_padding_px + self.x_offset_for_centering_px + \
            (x_m - world_origin_x_m) * self.current_pixels_per_meter

        # スクリーン座標のY位置: コンテンツ領域上端 + コンテンツ描画高さ - (ワールド座標からの相対位置) * ppm
        content_drawing_height = self.screen.get_height() - \
            self.content_start_y_px - self.current_screen_padding_px
        screen_y = self.content_start_y_px + content_drawing_height - \
            (y_m - world_origin_y_m) * self.current_pixels_per_meter

        return int(screen_x), int(screen_y)

    def draw_field(self):
        """フィールドの描画"""
        hw_m, hh_m = params.COURT_WIDTH_M / 2.0, params.COURT_HEIGHT_M / 2.0

        # フィールドラインの左上スクリーン座標
        field_tl_x_m = -hw_m
        field_tl_y_m = hh_m
        tl_lines_sx, tl_lines_sy = self.world_to_screen_pos(
            field_tl_x_m, field_tl_y_m)

        field_lines_w_px = max(
            1, int(params.COURT_WIDTH_M * self.current_pixels_per_meter))
        field_lines_h_px = max(
            1, int(params.COURT_HEIGHT_M * self.current_pixels_per_meter))

        if field_lines_w_px > 0 and field_lines_h_px > 0:
            pygame.draw.rect(self.screen, config.COLOR_FIELD_LINES,
                             (tl_lines_sx, tl_lines_sy,
                              field_lines_w_px, field_lines_h_px),
                             config.FIELD_MARKING_WIDTH_PX)

       # センターサークル
        cx_s, cy_s = self.world_to_screen_pos(0, 0)  # 中心点
        cc_r_px = int(params.CENTER_CIRCLE_RADIUS_M *
                      self.current_pixels_per_meter)
        if cc_r_px >= config.FIELD_MARKING_WIDTH_PX:
            pygame.draw.circle(self.screen, config.COLOR_FIELD_LINES,
                               (cx_s, cy_s), cc_r_px, config.FIELD_MARKING_WIDTH_PX)
        elif cc_r_px > 0:  # 線幅が太すぎる場合は塗りつぶし
            pygame.draw.circle(
                self.screen, config.COLOR_FIELD_LINES, (cx_s, cy_s), cc_r_px)

        # センターライン
        cl_top_s = self.world_to_screen_pos(0, hh_m)
        cl_bot_s = self.world_to_screen_pos(0, -hh_m)
        pygame.draw.line(self.screen, config.COLOR_FIELD_LINES,
                         cl_top_s, cl_bot_s, config.FIELD_MARKING_WIDTH_PX)
        cl_left_s = self.world_to_screen_pos(hw_m, 0)
        cl_right_s = self.world_to_screen_pos(-hw_m, 0)
        pygame.draw.line(self.screen, config.COLOR_FIELD_LINES,
                         cl_left_s, cl_right_s, config.FIELD_MARKING_WIDTH_PX)

        # ゴールエリア（白色）
        goal_area_w = params.GOAL_AREA_WIDTH_M
        goal_area_h = params.GOAL_AREA_HEIGHT_M

        # 左ゴールエリア
        ga_left_x1 = -params.COURT_WIDTH_M / 2
        ga_left_x2 = ga_left_x1 + goal_area_h
        ga_y1 = goal_area_w / 2
        ga_y2 = -goal_area_w / 2
        ga_left_rect_topleft = self.world_to_screen_pos(ga_left_x1, ga_y1)
        ga_left_rect_bottomright = self.world_to_screen_pos(ga_left_x2, ga_y2)
        pygame.draw.rect(
            self.screen,
            config.COLOR_FIELD_LINES,
            pygame.Rect(
                min(ga_left_rect_topleft[0], ga_left_rect_bottomright[0]),
                min(ga_left_rect_topleft[1], ga_left_rect_bottomright[1]),
                abs(ga_left_rect_bottomright[0] - ga_left_rect_topleft[0]),
                abs(ga_left_rect_bottomright[1] - ga_left_rect_topleft[1])
            ),
            config.FIELD_MARKING_WIDTH_PX
        )

        # 右ゴールエリア
        ga_right_x2 = params.COURT_WIDTH_M / 2
        ga_right_x1 = ga_right_x2 - goal_area_h
        ga_right_rect_topleft = self.world_to_screen_pos(ga_right_x1, ga_y1)
        ga_right_rect_bottomright = self.world_to_screen_pos(
            ga_right_x2, ga_y2)
        pygame.draw.rect(
            self.screen,
            config.COLOR_FIELD_LINES,
            pygame.Rect(
                min(ga_right_rect_topleft[0], ga_right_rect_bottomright[0]),
                min(ga_right_rect_topleft[1], ga_right_rect_bottomright[1]),
                abs(ga_right_rect_bottomright[0] - ga_right_rect_topleft[0]),
                abs(ga_right_rect_bottomright[1] - ga_right_rect_topleft[1])
            ),
            config.FIELD_MARKING_WIDTH_PX
        )

        # ゴール（黒色）
        goal_w = params.GOAL_WIDTH   # ゴールの幅（Y方向）
        goal_h = params.GOAL_HEIGHT  # ゴールの厚み（X方向）

        # 左ゴール
        left_goal_center_x = -params.COURT_WIDTH_M / 2 - goal_h / 2
        left_goal_rect_topleft = self.world_to_screen_pos(
            left_goal_center_x - goal_h / 2,  goal_w / 2)
        left_goal_rect_bottomright = self.world_to_screen_pos(
            left_goal_center_x + goal_h / 2, -goal_w / 2)
        pygame.draw.rect(
            self.screen,
            config.COLOR_GOAL,
            pygame.Rect(
                min(left_goal_rect_topleft[0], left_goal_rect_bottomright[0]),
                min(left_goal_rect_topleft[1], left_goal_rect_bottomright[1]),
                abs(left_goal_rect_bottomright[0] - left_goal_rect_topleft[0]),
                abs(left_goal_rect_bottomright[1] - left_goal_rect_topleft[1])
            )
        )

        # 右ゴール
        right_goal_center_x = params.COURT_WIDTH_M / 2 + goal_h / 2
        right_goal_rect_topleft = self.world_to_screen_pos(
            right_goal_center_x - goal_h / 2,  goal_w / 2)
        right_goal_rect_bottomright = self.world_to_screen_pos(
            right_goal_center_x + goal_h / 2, -goal_w / 2)
        pygame.draw.rect(
            self.screen,
            config.COLOR_GOAL,
            pygame.Rect(
                min(right_goal_rect_topleft[0],
                    right_goal_rect_bottomright[0]),
                min(right_goal_rect_topleft[1],
                    right_goal_rect_bottomright[1]),
                abs(right_goal_rect_bottomright[0] -
                    right_goal_rect_topleft[0]),
                abs(right_goal_rect_bottomright[1] -
                    right_goal_rect_topleft[1])
            )
        )

        # 壁
        wall_line_thickness_px = config.WALL_LINE_WIDTH_PX
        wall_top_y_m = params.COURT_HEIGHT_M / 2.0 + params.WALL_OFFSET_M
        wall_bottom_y_m = - (params.COURT_HEIGHT_M /
                             2.0 + params.WALL_OFFSET_M)
        wall_left_x_m = - (params.COURT_WIDTH_M / 2.0 +
                           params.WALL_OFFSET_M)
        wall_right_x_m = params.COURT_WIDTH_M / 2.0 + params.WALL_OFFSET_M

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
        """ロボットの描画"""
        if robot_data and robot_data["pos"] and robot_data["angle"] is not None:
            x, y = robot_data["pos"]
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

            self.screen.blit(id_surf, id_rect)

            # ボールを持っている場合、前方3mに線を表示
            if robot_data.get("photo_front"):
                line_end_x = x + 2 * \
                    math.cos(angle_for_pygame_rad)  # 前方3mのX座標
                line_end_y = y + -2 * \
                    math.sin(angle_for_pygame_rad)  # 前方3mのY座標
                line_start_s = self.world_to_screen_pos(x, y)
                line_end_s = self.world_to_screen_pos(line_end_x, line_end_y)
                pygame.draw.line(
                    self.screen, config.COLOR_WHITE, line_start_s, line_end_s, 2)

           # x座標に応じた回転速度
            max_x = params.COURT_WIDTH_M / 2  # フィールドの最大x座標
            normalized_x = (x + max_x) / (2 * max_x)  # x座標を0～1に正規化
            rotation_speed = max(1, min(normalized_x * 5, 5))  # 回転速度を0.5～5に制限

            # ロボットの周りに回転する円
            time_elapsed = pygame.time.get_ticks() / 1000.0  # 経過時間 (秒)
            orbit_radius_px = robot_radius_px * 1.5  # 回転する円の半径

            color = (255, 0, 0) if robot_data.get(
                "photo_front") else config.COLOR_DEBUG_VECTOR

            for i in range(20):  # 複数の円を描画
                orbit_angle_rad = time_elapsed * rotation_speed + i * math.pi / 50  # 回転角度
                orbit_x = center_x_s + orbit_radius_px * \
                    math.cos(orbit_angle_rad)
                orbit_y = center_y_s + orbit_radius_px * \
                    math.sin(orbit_angle_rad)

                pygame.draw.circle(self.screen, color,
                                   (int(orbit_x), int(orbit_y)), 1)  # 回転する円の描画

            for i in range(20):  # 複数の円を描画
                orbit_angle_rad = time_elapsed * rotation_speed + \
                    i * math.pi / 50 + math.pi * 0.5  # 回転角度
                orbit_x = center_x_s + orbit_radius_px * \
                    math.cos(orbit_angle_rad)
                orbit_y = center_y_s + orbit_radius_px * \
                    math.sin(orbit_angle_rad)

                pygame.draw.circle(self.screen, color,
                                   (int(orbit_x), int(orbit_y)), 1)  # 回転する円の描画
            for i in range(20):  # 複数の円を描画
                orbit_angle_rad = time_elapsed * rotation_speed + \
                    i * math.pi / 50 + math.pi * 1  # 回転角度
                orbit_x = center_x_s + orbit_radius_px * \
                    math.cos(orbit_angle_rad)
                orbit_y = center_y_s + orbit_radius_px * \
                    math.sin(orbit_angle_rad)

                pygame.draw.circle(self.screen, color,
                                   (int(orbit_x), int(orbit_y)), 1)  # 回転する円の描画
            for i in range(20):  # 複数の円を描画
                orbit_angle_rad = time_elapsed * rotation_speed + \
                    i * math.pi / 50 + math.pi * 1.5  # 回転角度
                orbit_x = center_x_s + orbit_radius_px * \
                    math.cos(orbit_angle_rad)
                orbit_y = center_y_s + orbit_radius_px * \
                    math.sin(orbit_angle_rad)

                pygame.draw.circle(self.screen, color,
                                   (int(orbit_x), int(orbit_y)), 1)  # 回転する円の描画

    def draw_ball(self, ball_pos):
        """ボールの描画"""
        if ball_pos:
            x, y = ball_pos
            ball_radius_px = int(params.BALL_RADIUS_M *
                                 self.current_pixels_per_meter)
            if ball_radius_px < 1:
                ball_radius_px = 1

            center_x_s, center_y_s = self.world_to_screen_pos(x, y)
            pygame.draw.circle(self.screen, config.COLOR_BALL,
                               (center_x_s, center_y_s), ball_radius_px)

            pygame.draw.circle(self.screen, config.COLOR_BALL,
                               (center_x_s, center_y_s), ball_radius_px*20, 1)

    def draw_robot_velocity_arrow(self, robot_data):
        """ロボットの目標速度を矢印で描画する"""
        if "target_move_angle" in robot_data and \
           "target_move_speed" in robot_data and \
           robot_data["pos"] is not None:

            vx = math.cos(math.radians(robot_data["target_move_angle"] + robot_data["angle"])) * \
                robot_data["target_move_speed"]
            vy = math.sin(math.radians(robot_data["target_move_angle"] + robot_data["angle"])) * \
                robot_data["target_move_speed"]

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

            # 矢印の方向をPygameの座標系に合わせて計算
            arrow_angle_rad = math.atan2(vy, vx)

            # 矢印の終点
            end_x_s = start_x_s + velocity_magnitude_px * \
                math.cos(arrow_angle_rad)
            end_y_s = start_y_s + velocity_magnitude_px * \
                math.sin(arrow_angle_rad)

            # 矢印本体
            pygame.draw.line(self.screen, config.COLOR_DEBUG_VECTOR,
                             (start_x_s, start_y_s), (int(end_x_s), int(end_y_s)), 2)
