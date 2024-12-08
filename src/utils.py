from src.constants import (
    ALLOWED_SERVER_IDS,
)
import logging

logger = logging.getLogger(__name__)
from src.base import Message
from discord import Message as DiscordMessage
from typing import Optional, List
import discord

from src.constants import MAX_CHARS_PER_REPLY_MSG

def discord_message_to_message(message: DiscordMessage) -> Optional[Message]:
    if message.content:
        return Message(user=message.author.name, text=message.content)
    return None


def split_into_shorter_messages(message: str) -> List[str]:
    return [
        message[i : i + MAX_CHARS_PER_REPLY_MSG]
        for i in range(0, len(message), MAX_CHARS_PER_REPLY_MSG)
    ]


def is_last_message_stale(
    interaction_message: DiscordMessage, last_message: DiscordMessage, bot_id: str
) -> bool:
    return (
        last_message
        and last_message.id != interaction_message.id
        and last_message.author
        and last_message.author.id != bot_id
    )

def should_block(guild: Optional[discord.Guild]) -> bool:
    if guild is None:
        # dm's not supported
        logger.info(f"DM not supported")
        return True

    if guild.id and guild.id not in ALLOWED_SERVER_IDS:
        # not allowed in this server
        logger.info(f"Guild {guild} not allowed")
        return True
    return False


def should_deterministically_respond(message: DiscordMessage, bot_name, bot_id) -> bool:
    containsNameInMessage = bot_name.lower() in message.content.lower()
    isMentionedInMessage = any([ member.id == bot_id for member in message.mentions])
    return containsNameInMessage or isMentionedInMessage 