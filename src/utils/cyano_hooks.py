"""Project hooks for better observe life-cycle of agents

Hooks(class):
- class CyanoAgentHooks(AgentHooks)


"""
from agents import AgentHooks, RunHooks, RunContextWrapper, Agent, Tool

from typing import Any, override

from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown


class CyanoAgentHooks(AgentHooks):
    """Friendly printing various lifecycle events callback from a specific running agent.
    Using this hooks when you need to observe the life-cycle of an agent for general purpose.
    Args:
        title(str): title to display in hook outputs
        show_tools_result(bool): show tool raw content return
    Usage:
        Agent(
            ...
            hooks=CyanoAgentHooks(title=..)
        )
    """
    def __init__(self, title: str = "", show_tools_result: bool = False):
        self.event_counter = 0
        self.title = title
        self.show_tools_result = show_tools_result
        self.console = Console()

    def _get_emoji_for_event(self, event_type: str) -> str:
        """Map event type to emoji."""
        emoji_map = {
            "on_start": "🤖",
            "on_end": "✅",
            "on_handoff": "🤝",
            "on_tool_start": "🛠️",
            "on_tool_end": "🔍"
        }
        return emoji_map.get(event_type, "💡")
    
    def _truncate_text(self, text: str, max_length: int = 20, placeholder: str ="...") -> str:
        """Truncate a text to a maximum length."""    
        return text if len(text) <= max_length else text[:max_length - len(placeholder)] + placeholder

    async def on_start(self, context: RunContextWrapper, agent : Agent) -> None:
        """Call this everytime the agent is invoked.
        """
        self.event_counter += 1
        event_emoji = self._get_emoji_for_event("on_start")
            
        text = Text.assemble(
            (f"<{self.title}> ", "dim"),
            (f"{event_emoji} AGENT START: ", "bold"),
            (f"{agent.name}", "bold cyan"),
            (" invoked.", "bold"),
            (f" ({self.event_counter})", "")
        )
        self.console.print(text)


    async def on_end(self, context: RunContextWrapper, agent : Agent, output: Any) -> None:
        """Call this everytime the agent produces a final output.
        """
        self.event_counter += 1
        event_emoji = self._get_emoji_for_event("on_end")

        # Use plain text for the header
        header_text = Text.assemble(
            (f"<{self.title}> ", "dim"),
            (f"{event_emoji} AGENT COMPLETE: ", "bold"),
            (f"{agent.name}", "bold cyan"),
            (" finished.", "bold"),
            (f" ({self.event_counter})", "")
        )    
        
        self.console.print(header_text)

        # Use Markdown for the output
        self.console.print(Markdown(str(output)))



    async def on_handoff(self, context: RunContextWrapper, agent: Agent, source: Agent) -> None:
        """Call this everytime the agent is being handoff to. The `source` is the agent that is handing
        off to this agent.
        """
        self.event_counter += 1
        event_emoji = self._get_emoji_for_event("on_handoff")

        text = Text.assemble(
            ((f"<{self.title}> ", "dim")),
            (f"{event_emoji} HANDOFF INVOKED: ", "bold"),
            (f"{agent.name}", "bold cyan"),
            (" ➡️ ", ""),
            (f"{source.name}", "bold yellow"),
            (f" ({self.event_counter})", "")
        )

        self.console.print(text)


    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        """Call this everytime the tool is being used.
        """
        self.event_counter += 1
        event_emoji = self._get_emoji_for_event("on_tool_start")
        text = Text.assemble(
            (f"<{self.title}> ", "dim"),
            (f"{event_emoji} TOOL START: ", "bold"),
            (f"{agent.name} ", "bold cyan"),
            ("using ", ""),
            (f"{tool.name} ", "bold yellow"),
            (f"{self._truncate_text(f"{tool.description}")}", "dim italic"),
            (f" ({self.event_counter})", "")
        )
        self.console.print(text)

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        """Call this everytime the tool return result.
        """
        self.event_counter += 1
        event_emoji = self._get_emoji_for_event("on_tool_end")

        main_text = Text.assemble(
            (f"<{self.title}> ", "dim"),
            (f"{event_emoji} TOOL COMPLETE: ", "bold"),
            (f"{agent.name}", "bold cyan"),
            (" finished ", ""),
            (f"{tool.name}", "bold yellow"),
            (f" ({self.event_counter})", "")
        )

        self.console.print(main_text)

        # Only show tool results when show_tools_result is True
        if self.show_tools_result:
            result_text = Text(result)
            self.console.print(Text("Tool Result:", style="dim"))
            self.console.print(result_text)




# # 
# class ReflectAgentHooks(CyanoAgentHooks):
#     @override
#     def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
#         return await super().on_tool_end(context, agent, tool, result)