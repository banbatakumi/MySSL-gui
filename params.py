import math

# --- ロボット物理パラメータ ---
ROBOT_DIAMETER_M = 0.18  # ロボットの直径 (メートル)
ROBOT_RADIUS_M = ROBOT_DIAMETER_M * 0.5  # ロボットの半径 (メートル)

BALL_DIAMETER_M = 0.042  # ボールの直径 (メートル)
BALL_RADIUS_M = BALL_DIAMETER_M * 0.5  # ボールの半径 (メートル)

SENSOR_FOV_HALF_ANGLE_RAD = math.radians(20)  # センサーの視野角の半分 (ラジアン)

# --- コートと壁のパラメータ ---


# --- DivAのパラメータ ---
# COURT_WIDTH_M = 12  # コートの幅 (メートル) - 白線間の距離
# COURT_HEIGHT_M = 9  # コートの高さ (メートル) - 白線間の距離
# CENTER_CIRCLE_RADIUS_M = 0.5  # センターサークルの半径 (メートル)
# GOAL_AREA_WIDTH_M = 3.6  # ゴールエリアの幅 (メートル)
# GOAL_AREA_HEIGHT_M = 1.8  # ゴールエリアの高さ (メートル)
# GOAL_WIDTH = 1.8
# GOAL_HEIGHT = 0.2


# --- DivBのパラメータ ---
COURT_WIDTH_M = 9  # コートの幅 (メートル) - 白線間の距離
COURT_HEIGHT_M = 6  # コートの高さ (メートル) - 白線間の距離
CENTER_CIRCLE_RADIUS_M = 0.5  # センターサークルの半径 (メートル)
GOAL_AREA_WIDTH_M = 2  # ゴールエリアの幅 (メートル)
GOAL_AREA_HEIGHT_M = 1  # ゴールエリアの高さ (メートル)
GOAL_WIDTH = 1
GOAL_HEIGHT = 0.2

# COURT_WIDTH_M = 1.5  # コートの幅 (メートル) - 白線間の距離
# COURT_HEIGHT_M = 1  # コートの高さ (メートル) - 白線間の距離
# CENTER_CIRCLE_RADIUS_M = 0.3  # センターサークルの半径 (メートル)
# GOAL_AREA_WIDTH_M = 0.5  # ゴールエリアの幅 (メートル)
# GOAL_AREA_HEIGHT_M = 0.25  # ゴールエリアの高さ (メートル)
# GOAL_WIDTH = 0.25
# GOAL_HEIGHT = 0.1


WALL_OFFSET_M = 0.30  # コートの白線から壁までのオフセット距離 (メートル)
