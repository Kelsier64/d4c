import discord
from discord.ui import View, Select, Modal, TextInput

class CustomInputModal(Modal):
    def __init__(self, title: str, view: View, interaction_message: discord.Message, on_answer):
        super().__init__(title=title)
        self.view_instance = view
        self.interaction_message = interaction_message
        self.on_answer = on_answer

        self.answer_input = TextInput(
            label="Your Answer",
            style=discord.TextStyle.paragraph,
            placeholder="Type your answer here...",
            required=True
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Disable the view components
        for item in self.view_instance.children:
            if hasattr(item, "disabled"):
                setattr(item, "disabled", True)
        
        # Edit the original message to reflect the choice
        await self.interaction_message.edit(view=self.view_instance)
        
        # Respond to the modal submission
        await interaction.response.send_message(f"Answer submitted: {self.answer_input.value}", ephemeral=True)
        
        # Call the callback with the custom answer
        if self.on_answer:
            await self.on_answer([self.answer_input.value])


class QuestionSelect(Select):
    def __init__(self, options_data: list[dict], multiple: bool, on_answer):
        self.on_answer_callback = on_answer
        
        max_values = len(options_data) if multiple else 1
        if max_values < 1:
            max_values = 1
            
        select_options = []
        for opt in options_data:
            label = opt.get("label", "Option")
            # Discord limits label to 100 chars
            if len(label) > 100:
                label = label[:97] + "..."
            
            value = opt.get("value", label)
            # Discord limits value to 100 chars
            if len(value) > 100:
                value = value[:100]
                
            description = opt.get("description", None)
            if description and len(description) > 100:
                description = description[:97] + "..."
                
            select_options.append(discord.SelectOption(label=label, value=value, description=description))
            
        super().__init__(
            placeholder="Choose an option...",
            min_values=1,
            max_values=max_values,
            options=select_options
        )

    async def callback(self, interaction: discord.Interaction):
        if not self.view or not interaction.message:
            return

        # Check if 'custom' is selected
        is_custom = any("custom" in val.lower() or "自行輸入答案" in val for val in self.values)
        
        if is_custom:
            # We need to send the modal
            modal = CustomInputModal(
                title="Custom Answer",
                view=self.view,
                interaction_message=interaction.message,
                on_answer=self.on_answer_callback
            )
            await interaction.response.send_modal(modal)
        else:
            # Normal selection
            for item in self.view.children:
                if hasattr(item, "disabled"):
                    setattr(item, "disabled", True)
            
            # Edit message to disable components
            await interaction.response.edit_message(view=self.view)
            
            # Send the answers back via callback
            if self.on_answer_callback:
                await self.on_answer_callback(self.values)


class OpenCodeView(View):
    def __init__(self, options_data: list[dict], multiple: bool, on_answer):
        super().__init__(timeout=None)
        self.add_item(QuestionSelect(options_data, multiple, on_answer))
