import discord
from discord.ext import commands
import os
from src.constants import (
    ALLOWED_SERVER_IDS,
    DEFAULT_BOT_NAME,
)
from src.db import (
    db,
    get_config,
)

class GPTDiscordClient(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = db.init()
        self.BOT_NAME = get_config(self.db, "bot_name", DEFAULT_BOT_NAME)
        # convert to snowflake from int
        self.GUILD_ID = discord.Object(ALLOWED_SERVER_IDS[0])
        self.PURGE_OLDER_THAN = None  
        self.should_respond_next = False
    
    async def setup_hook(self):
        for thing in os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), "cogs")):
            if thing.endswith('.py'):
                cog_name = f"src.cogs.{thing[:-3]}"
                print(f"Loading cog: {cog_name}")
                await self.load_extension(cog_name)

        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=self.GUILD_ID)
        await self.tree.sync(guild=self.GUILD_ID)