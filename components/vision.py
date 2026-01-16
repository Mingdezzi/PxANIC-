from dataclasses import dataclass

@dataclass
class Vision:
    view_radius: float = 12.0
    fov_angle: float = 60.0
    is_blind: bool = False
