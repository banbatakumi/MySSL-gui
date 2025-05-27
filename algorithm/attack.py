
class Attack:
    def __init__(self, state, basic_move):
        self.state = state
        self.basic_move = basic_move
    def attack(self):
        print(f"[Attack] Attacking")
        return {"cmd": {"kick": True}} # Dummy command
