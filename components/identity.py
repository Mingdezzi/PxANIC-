from dataclasses import dataclass

@dataclass
class Identity:
    name: str = "Unknown"
    role: str = "CITIZEN"
    sub_role: str = None # FARMER, MINER, FISHER
    group_id: str = "BOT" # PLAYER, BOT, SPECTATOR
    is_player: bool = False
