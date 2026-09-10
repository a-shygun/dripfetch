import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Drop:
    x: int
    head_y: int = -1
    speed: float = 50
    length: int = 5
    color: str = "#FFFFFF"
    path: deque = field(default_factory=deque)
    redirect_target: int | None = None
    active: bool = True
    last_move: float = field(default_factory=time.monotonic)
