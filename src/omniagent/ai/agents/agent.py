from typing import Callable, List

from omniagent.ai.tools.tools import Tool
from omniagent.types.state import State


class Agent:
    def __init__(
        self,
        name: str,
        description: str,
        instructions: str,
        tools: List[Tool] | None = None,
        current_state: State | None = None,
        before_model_callback: Callable | None = None,
        after_model_callback: Callable | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.instructions = instructions
        self.tools = tools or []
        self.current_state = current_state
        self.before_model_callback = before_model_callback
        self.after_model_callback = after_model_callback
