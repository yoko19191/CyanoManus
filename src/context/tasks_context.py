""" 

"""

import asyncio
from dataclasses import dataclass
from typing import List

@dataclass
class TaskContext:
    task_uid : int
    messages : List[dict]
    next_agent : str


