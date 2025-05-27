
class PassBall:
    def __init__(self, state, basic_move):
        self.state = state
        self.basic_move = basic_move
    def pass_to_target(self, target_robot_id):
        print(f"[PassBall] Pass to robot {target_robot_id}")
        return {"cmd": {"kick": True, "kick_power": 50}} # Dummy command
