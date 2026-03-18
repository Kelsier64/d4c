import discord
from typing import List, Dict, Any

class ProgressEmbedManager:
    """
    Maintains state of recent tool executions and generates Discord embeds
    representing their progress.
    """
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        # Each item is a dictionary with structure:
        # { "id": str, "tool": str, "status": "running" | "done" | "error", "details": str }
        self.history: List[Dict[str, Any]] = []

    def update_task(self, task_id: str, tool: str, status: str, details: str = ""):
        """
        Updates an existing task or adds a new one to the history.
        """
        # Find if the task exists
        found = False
        for task in self.history:
            if task["id"] == task_id:
                task["status"] = status
                if details:
                    task["details"] = details
                found = True
                break

        if not found:
            self.history.append({
                "id": task_id,
                "tool": tool,
                "status": status,
                "details": details
            })

        # Keep only the most recent `max_history` items
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def build_embed(self) -> discord.Embed:
        """
        Builds a discord.Embed representing the current state of tool executions.
        Colors:
        - Yellow (0xFFFF00): Running
        - Green (0x00FF00): Done
        - Red (0xFF0000): Error
        """
        # Determine the color based on the status of the most recent item, or overall running status
        color = 0x00FF00 # Default to Green (Done)
        
        has_running = any(task["status"] == "running" for task in self.history)
        has_error = any(task["status"] == "error" for task in self.history)
        
        if has_error:
            color = 0xFF0000 # Red
        elif has_running:
            color = 0xFFFF00 # Yellow

        embed = discord.Embed(title="Task Progress", color=color)

        if not self.history:
            embed.description = "No recent tasks."
            return embed

        for task in reversed(self.history):
            status_emoji = "🔄"
            if task["status"] == "done":
                status_emoji = "✅"
            elif task["status"] == "error":
                status_emoji = "❌"

            tool_name = task["tool"].capitalize()
            value = task["details"] if task["details"] else f"Status: {task['status']}"
            embed.add_field(
                name=f"{status_emoji} {tool_name}",
                value=value,
                inline=False
            )

        return embed
