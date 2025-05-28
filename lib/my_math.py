
def NormalizeDeg180(angle):
    angle = angle % 360
    if angle > 180:
        angle -= 360
    return angle

def NormalizeDeg360(angle):
    return angle % 360
