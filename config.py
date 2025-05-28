# --- UDP 通信設定 ---
CONTROLLER_IP = "127.0.0.1"

# GUIがロボットの状態データを受信するポート (GUI側がリッスン)
GUI_LISTEN_PORT = 50040  # 追加
# 緊急コマンドをシミュレータに送信するポート (シミュレータ側がリッスン)
EMERGENCY_COMMAND_SEND_PORT = 50041  # 追加

COURT_WIDTH_M = 1.5  # コートの幅 (メートル)
COURT_HEIGHT_M = 1  # コートの高さ (メートル)

# 受信バッファサイズ
BUFFER_SIZE = 65536

# --- 初期描画定数 (ウィンドウサイズ変更時に更新) ---
# その他の設定 (既存のものがあればそのまま)
INITIAL_SCREEN_WIDTH_PX = 1000
INITIAL_SCREEN_HEIGHT_PX = 700
INITIAL_PIXELS_PER_METER = 80
INITIAL_SCREEN_PADDING_PX = 20

# フィールドの描画設定
FIELD_MARKING_WIDTH_PX = 3
WALL_LINE_WIDTH_PX = 5
ROBOT_OUTLINE_WIDTH_PX = 1  # ロボットの線の太さ（塗りつぶしなのでここでは内部の線の太さを示す）

FIELD_MARKING_WIDTH_PX = 2
ROBOT_OUTLINE_WIDTH_PX = 2
WALL_LINE_WIDTH_PX = 4

# General Colors
COLOR_BACKGROUND = (20, 20, 20)     # 全体の背景色 (最も暗い)
COLOR_TOP_BAR_BG = (40, 40, 40)     # トップバーの背景色
COLOR_CONTENT_BG = (30, 30, 30)     # コンテンツ領域の背景色 (フィールドや表の背景)
COLOR_TEXT = (230, 230, 230)        # 一般的なテキスト色
COLOR_WHITE = (255, 255, 255)       # 白


# Field Colors
COLOR_FIELD_LINES = (120, 120, 120)  # フィールドラインのグレー
COLOR_WALLS = (60, 60, 60)          # 壁の濃いグレー

# Robot Colors
COLOR_YELLOW_ROBOT = (255, 200, 0)  # 明るい黄色
COLOR_BLUE_ROBOT = (0, 150, 255)    # 明るい青
COLOR_ROBOT_FRONT = (255, 50, 50)   # ロボットの向きを示す線の色 (明るい赤)

# Ball Color
COLOR_BALL = (255, 165, 0)          # ボールの色 (オレンジ)

# GUI Element Colors
COLOR_BUTTON_NORMAL = (70, 70, 70)      # 通常時のボタン色
COLOR_BUTTON_SELECTED = (110, 110, 110)  # 選択時のボタン色
COLOR_BUTTON_HOVER = (255, 220, 0)      # ホバー/枠線のアクセント色 (明るい黄)

# Table Row Colors (for Robot States)
COLOR_ROW_EVEN = (35, 35, 35)       # ロボットステータス表の偶数行背景
COLOR_ROW_ODD = (30, 30, 30)        # ロボットステータス表の奇数行背景

# Debugging Visuals
COLOR_DEBUG_VECTOR = (0, 255, 255)  # デバッグ矢印の色 (シアン)
VELOCITY_ARROW_SCALE = 0.3        # 速度矢印の長さスケール (m/s -> ピクセル長)
MIN_VELOCITY_ARROW_LENGTH_PX = 3  # 速度矢印の最小長さ（ピクセル）

FPS = 60
