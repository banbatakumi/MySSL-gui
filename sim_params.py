import math

# --- ロボット物理パラメータ ---
ROBOT_DIAMETER_M = 0.18  # ロボットの直径 (メートル)
ROBOT_RADIUS_M = ROBOT_DIAMETER_M * 0.5  # ロボットの半径 (メートル)

BALL_DIAMETER_M = 0.042  # ボールの直径 (メートル)
BALL_RADIUS_M = BALL_DIAMETER_M * 0.5  # ボールの半径 (メートル)

SENSOR_FOV_HALF_ANGLE_RAD = math.radians(20)  # センサーの視野角の半分 (ラジアン)

# --- コートと壁のパラメータ ---
WALL_OFFSET_M = 0.20  # コートの白線から壁までのオフセット距離 (メートル)
