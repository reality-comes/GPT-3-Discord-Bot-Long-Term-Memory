from enum import Enum
from dataclasses import dataclass
import openai
from typing import Optional, List

from src.botType import GPTDiscordClient
from src.db import db
from src.constants import (
    DEFAULT_MODEL,
    DEFAULT_BOT_NAME,
    DEFAULT_TEMPERATURE,
    DEFAULT_FREQUENCY_PENALTY,
    DEFAULT_PRESENCE_PENALTY,
    BOT_DEFAULT_PROMPT,
    BOT_POST_INSTRUCTIONS,
)
import discord
from src.base import Message, Prompt, Conversation
from src.utils import split_into_shorter_messages, logger

from uuid import uuid4
from time import time

gptClient = openai.Client()

BOT_NAME = DEFAULT_BOT_NAME

class CompletionResult(Enum):
    OK = 0
    TOO_LONG = 1
    INVALID_REQUEST = 2
    OTHER_ERROR = 3


@dataclass
class CompletionData:
    status: CompletionResult
    reply_text: Optional[str]
    status_text: Optional[str]

async def generate_completion_response(
    messages: List[Message], bot: GPTDiscordClient
) -> CompletionData:
    try:
        conn = bot.db
        personality_prompt = db.get_config(conn, "prompt", default=BOT_DEFAULT_PROMPT)
        full_prompt = f"{personality_prompt}\n{BOT_POST_INSTRUCTIONS}"

        prompt = Prompt(
            header=Message(
                "System", f"Instructions: {full_prompt}"
            ),
            convo=Conversation(messages, bot.BOT_NAME),
        )

        rendered = prompt.render()

        print(rendered)
        model = db.get_config(conn, "model", DEFAULT_MODEL)
        temperature = db.get_float_config(conn, "temperature", default=DEFAULT_TEMPERATURE)
        frequency_penalty = db.get_float_config(conn, "frequency_penalty", default=DEFAULT_FREQUENCY_PENALTY)
        presence_penalty = db.get_float_config(conn, "presence_penalty", default=DEFAULT_PRESENCE_PENALTY)

        response = gptClient.chat.completions.create(
            messages=rendered,
            model=model,
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
        
        reply = response.choices[0].message.content.strip()

        return CompletionData(
            status=CompletionResult.OK, reply_text=reply, status_text=None
        )

    except openai.BadRequestError as e:
        
        if hasattr(e, 'user_message') and "This model's maximum context length" in e.user_message:
            return CompletionData(
                status=CompletionResult.TOO_LONG, reply_text=None, status_text=str(e)
            )
        else:
            logger.exception(e)
            return CompletionData(
                status=CompletionResult.INVALID_REQUEST,
                reply_text=None,
                status_text=str(e),
            )
    except Exception as e:
        logger.exception(e)
        return CompletionData(
            status=CompletionResult.OTHER_ERROR, reply_text=None, status_text=str(e)
        )


async def process_response(
    user: str, channel: discord.TextChannel, response_data: CompletionData
):
    status = response_data.status
    reply_text = response_data.reply_text
    status_text = response_data.status_text
    if status is CompletionResult.OK:
        sent_message = None
        if not reply_text:
            sent_message = await channel.send(
                embed=discord.Embed(
                    description=f"**Invalid response** - empty response",
                    color=discord.Color.yellow(),
                )
            )
        else:
            shorter_response = split_into_shorter_messages(reply_text)
            for r in shorter_response:
                sent_message = await channel.send(r, allowed_mentions=discord.AllowedMentions(users=True))

    elif status is CompletionResult.INVALID_REQUEST:
        await channel.send(
            embed=discord.Embed(
                description=f"**Invalid request** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
    else:
        await channel.send(
            embed=discord.Embed(
                description=f"**Error** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
