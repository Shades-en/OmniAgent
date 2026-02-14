from abc import ABC, ABCMeta, abstractmethod
from typing import List, Any
from pydantic import BaseModel

from openinference.semconv.trace import OpenInferenceSpanKindValues

from omniagent.utils.tracing import trace_method
from omniagent.types.tools import ToolArguments


class RequireArgClassMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace):
        if name != "Tool":  # Don't enforce on the abstract class itself
            if "Arguments" not in namespace or not isinstance(namespace["Arguments"], type):
                raise TypeError(f"{name} must define an inner pydantic class named 'Arguments'")
        return super().__new__(mcs, name, bases, namespace)

class Tool(ABC, metaclass=RequireArgClassMeta):
    def __init__(self, name: str, description: str) -> None:
        self.name: str = name
        self.description: str = description
        self.arguments: List[ToolArguments] = self._parse_arguments()

    class Arguments(BaseModel):
        pass

    @classmethod
    def _parse_arguments(cls) -> List[ToolArguments]:
        args = []
        arguments = cls.Arguments.model_json_schema()
        properties = arguments["properties"]
        for property_name, property_schema in properties.items():
            args.append(ToolArguments(
                name=property_name,
                description=property_schema["description"],
                required=property_name in arguments.get("required", []),
                type=property_schema["type"],
            ))
        return args

    @trace_method(
        kind=OpenInferenceSpanKindValues.TOOL,
        graph_node_id=lambda self: f"tool_{self.name}",
        capture_input=True,
        capture_output=True
    )
    @abstractmethod
    async def __call__(self, arguments: Arguments) -> Any:
        """
        Execute the tool with given arguments.
        
        Traced as TOOL span with dynamic node ID based on tool name.
        Captures input arguments and output result for debugging.
        """
        pass
