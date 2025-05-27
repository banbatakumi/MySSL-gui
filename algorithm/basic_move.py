
class BasicMove:
    def __init__(self, state):
        self.state = state
    def move_to_target(self, target_pos, target_angle):
        print(f"[BasicMove] Move to {target_pos} face {target_angle}")
        return {"cmd": {"move_speed": 0}} # Dummy command
    def turn_to_angle(self, target_angle):
        print(f"[BasicMove] Turn to {target_angle}")
        return {"cmd": {"face_angle": target_angle}} # Dummy command
