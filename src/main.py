import random
import discord

from discord import  (
    Message as DiscordMessage,
  )

from discord.ext import commands

import logging
import asyncio
import json
import os
from uuid import uuid4
from time import time
from datetime import datetime
from src.base import Message, Conversation
from src.constants import (
    ALLOWED_SERVER_IDS,
    BOT_INVITE_URL,
    DEFAULT_BOT_NAME,
    DISCORD_BOT_TOKEN,
    SECONDS_DELAY_RECEIVING_MSG,
)
import atexit

from src.utils import (
    logger,
    should_block,
    is_last_message_stale,
    should_deterministically_respond,
)
from src.botType import GPTDiscordClient
from src import completion
from src.completion import generate_completion_response, process_response
from src.memory import (
    save_json, 
    load_convo,
    timestamp_to_datetime
)

logging.basicConfig(
    format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s", level=logging.INFO
)

intents = discord.Intents.default()
intents.message_content = True


client = GPTDiscordClient(command_prefix=[], intents=intents)

@client.event
async def on_ready():
    logger.info(f"We have logged in as {client.user}. Invite URL: {BOT_INVITE_URL}")
    completion.BOT_NAME = client.user.name


# calls for each message
@client.event
async def on_message(message: DiscordMessage):
    channel = message.channel
    try:
        # block servers not in allow list
        if should_block(guild=message.guild):
            return

        # ignore messages from the bot
        if message.author == client.user or message.author.bot:
            return

        # save message as embedding, vectorize
        timestamp = int(time())
        timestring = timestring = timestamp_to_datetime(timestamp)
        user = message.author.name
        extracted_message = message.content
        info = {
            'speaker': user,
            'timestamp': timestamp,
            'uuid': str(uuid4()),
            'message': extracted_message,
            'timestring': timestring,
        }

        if message.attachments:
            info['attachments'] = [a.proxy_url for a in message.attachments if a.size < 2_000_000]

        logger.info(
            f"incoming channel message to process - {message.author.nick}: {message.content[:50]}"
        )

        filename = 'log_%s_user' % timestamp
        save_json(f'./src/chat_logs/{filename}.json', info)

        # check if bot should respond
        shouldRandomlyRespond = random.random() < 0.01 # 1% chance to respond randomly
        should_respond = should_deterministically_respond(message, client.BOT_NAME, client.user.id) or shouldRandomlyRespond or client.should_respond_next
        if not should_respond:
            return
        
        # wait a bit in case user has more messages
        if SECONDS_DELAY_RECEIVING_MSG > 0:
            client.should_respond_next = True
            await asyncio.sleep(SECONDS_DELAY_RECEIVING_MSG)
            if is_last_message_stale(
                interaction_message=message,
                last_message=channel.last_message,
                bot_id=client.user.id,
            ):
                # there is another message, so ignore this one, but let's make sure we still respond
                logger.info(f"last message is stale, but set response flag")
                return

        logger.info(
            f"channel message to process - {message.author}: {message.content[:50]} - {channel.name} {channel.jump_url}"
        )

        # load past conversations
        history = load_convo()

        channel_messages = [x for x in history if x is not None]
        channel_messages.reverse()

        # generate the response
        async with channel.typing():
            response_data = await generate_completion_response(
                messages=channel_messages, bot=client
            )
            timestamp = int(time())
            timestring = timestamp_to_datetime(timestamp)
            user = client.user.name
            extracted_message = response_data.reply_text
            info = {'speaker': 'bot', 'timestamp': timestamp,'uuid': str(uuid4()), 'message': extracted_message, 'timestring': timestring}
            filename = 'log_%s_bot' % timestamp
            save_json(f'./src/chat_logs/{filename}.json', info)


        # send response
        await process_response(
            channel=message.channel, user=message.author, response_data=response_data
        )
        client.should_respond_next = False
        logger.info(f"unsetting response flag")
    except Exception as e:
        logger.exception(e)


def exit_handler():
    logger.info("Exiting")
    client.db.close()

if __name__ == "__main__":
    atexit.register(exit_handler)
    client.run(DISCORD_BOT_TOKEN)