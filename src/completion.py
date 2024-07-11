from enum import Enum
from dataclasses import dataclass
import openai
import json
from typing import Optional, List
from src.constants import (
    BOT_INSTRUCTIONS,
    BOT_NAME,
    EXAMPLE_CONVOS,
)
import discord
from src.base import Message, Prompt, Conversation
from src.utils import split_into_shorter_messages, logger
from datetime import datetime
from src.memory import (
    gpt3_response_embedding, 
    save_json,
    timestamp_to_datetime
    )

from uuid import uuid4
from time import time


MY_BOT_NAME = BOT_NAME
MY_BOT_EXAMPLE_CONVOS = EXAMPLE_CONVOS


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
    messages: List[Message], user: str
) -> CompletionData:
    try:
        timestamp = time()
        imestring = timestring = timestamp_to_datetime(timestamp)
        prompt = Prompt(
            header=Message(
                "System", f"Instructions for {MY_BOT_NAME}: {BOT_INSTRUCTIONS}"
            ),
            examples=MY_BOT_EXAMPLE_CONVOS,
            convo=Conversation(messages + [Message(f"{timestring} {MY_BOT_NAME}")]),
        )
        
        rendered = prompt.render()
        print(rendered)
        #response = openai.Completion.create(
            #model="text-davinci-003",
            #message=rendered,
            #temperature=1.0,
            #top_p=0.9,
            #max_tokens=512,
            #stop=["<|endoftext|>"],
            
         # You can rollback to using text-davincini-003 by swapping the active "response =" and "reply ="

        response = openai.ChatCompletion.create(
            model="gpt-4o-2024-05-13",
            messages=[{"role": "system", "content": rendered}])

        #reply = response.choices[0].text.strip()
        
        reply = response.choices[0].message['content'].strip()

        return CompletionData(
            status=CompletionResult.OK, reply_text=reply, status_text=None
        )
    except openai.error.InvalidRequestError as e:
        if "This model's maximum context length" in e.user_message:
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
                sent_message = await channel.send(r)

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
