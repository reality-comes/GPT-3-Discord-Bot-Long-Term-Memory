from typing import List
import discord
from discord import app_commands
from discord.ext import commands

from src.constants import (
    CONFIG,
    PROMPT_PRESET_KEYS,
)
from src.main import GPTDiscordClient
from src.db import (
  get_config, 
  set_config,
)

CONFIG_KEYS = [
    'temperature',
    'frequency_penalty',
    'presence_penalty',
]

class PromptModal(discord.ui.Modal, title="Set Custom Prompt"):
    def __init__(self, bot: GPTDiscordClient):
        super().__init__()
        self.bot = bot

    name = discord.ui.TextInput(label="Name", placeholder="Enter the name", required=True, max_length=100)
    prompt = discord.ui.TextInput(label="Prompt", style=discord.TextStyle.long, required=True, placeholder="Enter the prompt", max_length=512)

    async def on_submit(self, interaction: discord.Interaction):
        name = self.name.value
        capitalized_name = name.replace("_", " ").title()
        prompt = self.prompt.value
        set_config(self.bot.db, "bot_name", capitalized_name)
        set_config(self.bot.db, "prompt", prompt)
        self.bot.BOT_NAME = name
        await interaction.response.send_message(f"Set name to '{capitalized_name}' & prompt to '{prompt}'", ephemeral=True)


class Config(commands.GroupCog, name="config"):
    def __init__(self, bot: GPTDiscordClient) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="get")
    @app_commands.choices(key=[
        app_commands.Choice(name=key, value=key) for key in CONFIG_KEYS
    ] + [app_commands.Choice(name="model", value="model")])
    async def get_conf(self, interaction: discord.Interaction, key: str) -> None:
        """Get value of bot's configuration"""
        value = get_config(self.bot.db, key)
        await interaction.response.send_message(f"Value of {key}: {value}", ephemeral=True)


    @app_commands.command(name="set")
    @app_commands.choices(key=[
        app_commands.Choice(name=key, value=key) for key in CONFIG_KEYS
    ])
    async def set_conf(self, interaction: discord.Interaction, key: str, value: float) -> None:
        """Set value of bot's configuration, 0 to 1, inclusive"""
        if value < 0 or value > 1:
            await interaction.response.send_message("Value must be between 0 and 1, inclusive", ephemeral=True)
            return
        
        set_config(self.bot.db, key, value)
        await interaction.response.send_message(f"Set {key} to {value}", ephemeral=False)

    @app_commands.command(name="prompt")
    async def get_prompt(self, interaction: discord.Interaction) -> None:
        """Get the current prompt being used"""
        value = get_config(self.bot.db, "prompt")
        await interaction.response.send_message(f"Current prompt: {value}", ephemeral=True)

    @app_commands.command(name="setprompt")
    async def set_prompt(self, interaction: discord.Interaction, value: str) -> None:
        """Set the prompt to use"""
        set_config(self.bot.db, "prompt", value)
        await interaction.response.send_message(f"Set prompt to {value}", ephemeral=False)


    @app_commands.command(name="setprompt-preset")
    @app_commands.choices(prompt=[
        app_commands.Choice(name=prompt, value=prompt) for prompt in PROMPT_PRESET_KEYS   
    ])
    async def set_prompt_preset(self, interaction: discord.Interaction, prompt: str) -> None:
        """Set the prompt to a preset"""
        prompt_str = getattr(CONFIG.presets, prompt)
        capitalized_name = prompt.replace("_", " ").title()
        set_config(self.bot.db, "bot_name", capitalized_name)
        self.bot.BOT_NAME = capitalized_name
        await interaction.response.send_message(f"Set name to '{capitalized_name}' & prompt to '{prompt_str}'", ephemeral=False)

    @app_commands.command(name="setprompt-custom")
    async def set_prompt_custom(self, interaction: discord.Interaction) -> None:
        """Open a modal to set a custom prompt"""
        await interaction.response.send_modal(PromptModal(bot=self.bot))


async def setup(bot: GPTDiscordClient) -> None:
    await bot.add_cog(Config(bot), guilds=[discord.Object(id=bot.GUILD_ID.id)])
