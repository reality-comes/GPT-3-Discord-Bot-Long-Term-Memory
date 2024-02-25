import discord
from discord import Message as DiscordMessage
import logging
import asyncio
import json
import os
from uuid import uuid4
from time import time
from datetime import datetime
from src.base import Message, Conversation
from src.constants import (
    BOT_INVITE_URL,
    DISCORD_BOT_TOKEN,
    EXAMPLE_CONVOS,
    MAX_MESSAGE_HISTORY,
    SECONDS_DELAY_RECEIVING_MSG,
)

from src.utils import (
    logger,
    should_block,
    is_last_message_stale,
    discord_message_to_message,
)
from src import completion
from src.completion import generate_completion_response, process_response
from src.memory import (
    gpt3_embedding,
    gpt3_response_embedding, 
    save_json, 
    load_convo,
    add_notes,
    notes_history,
    fetch_memories,
    summarize_memories,
    load_memory,
    load_context,
    open_file,
    gpt3_completion,
    timestamp_to_datetime
)


logging.basicConfig(
    format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s", level=logging.INFO
)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


@client.event
async def on_ready():
    logger.info(f"We have logged in as {client.user}. Invite URL: {BOT_INVITE_URL}")
    completion.MY_BOT_NAME = client.user.name
    completion.MY_BOT_EXAMPLE_CONVOS = []
    for c in EXAMPLE_CONVOS:
        messages = []
        for m in c.messages:
            if m.user == client.user.name:
                messages.append(Message(user=client.user.name, text=m.text))
            else:
                messages.append(m)
        completion.MY_BOT_EXAMPLE_CONVOS.append(Conversation(messages=messages))
    await tree.sync()


# /chat message:
@tree.command(name="chat", description="Talk to the bot")
@discord.app_commands.checks.has_permissions(send_messages=True)
@discord.app_commands.checks.has_permissions(view_channel=True)
@discord.app_commands.checks.bot_has_permissions(send_messages=True)
@discord.app_commands.checks.bot_has_permissions(view_channel=True)
@discord.app_commands.checks.bot_has_permissions(manage_threads=True)
async def chat_command(int: discord.Interaction, message: str, channel: discord.TextChannel):
    try:
        # block servers not in allow list
        if should_block(guild=int.guild):
            return

        user = int.user
        logger.info(f"Chat command by {user} {message[:20]}")
        try:
            embed = discord.Embed(
                description=f"<@{user.id}> wants to chat! 🤖💬",
                color=discord.Color.green(),
            )
            embed.add_field(name=user.name, value=message)
            await int.response.send_message(embed=embed)
            response = await int.original_response()
        except Exception as e:
            logger.exception(e)
            await int.response.send_message(
                f"Failed to start chat {str(e)}", ephemeral=True
            )
            return

        async with channel.typing():
            # fetch completion
            messages = [Message(user=user.name, text=message)]
            response_data = await generate_completion_response(
                messages=messages, user=user
            )
            # send the result
            await process_response(
                user=user, channel=channel, response_data=response_data
            )
    except Exception as e:
        logger.exception(e)
        await int.response.send_message(
            f"Failed to start chat {str(e)}", ephemeral=True
        )
        

# calls for each message
@client.event
async def on_message(message: DiscordMessage):
    channel = message.channel
    try:
        # block servers not in allow list
        if should_block(guild=message.guild):
            return

        logger.info(f"message.channel: {message.channel}, message.author: {message.author}, client.user: {client.user}, message.content: {message.content}")

        mentioned = False

        # The bot should respond to messages that are replies to it
        if message.reference is not None:
            if message.reference.cached_message is None:
                # Fetching the message
                #channel = bot.get_channel(message.reference.channel_id)
                msg = await channel.fetch_message(message.reference.message_id)

            else:
                msg = message.reference.cached_message
            
            if msg.author == client.user:
                logger.info(f"{msg.author} == {client.user}")
                mentioned = True

        username = client.user.name.split("#")[0].lower().split(" ")
        username.append(f"<@{str(client.user.id)}>")
        for word in username:
            if word in message.content.lower():
                mentioned = True
        # ignore messages unless we are mentioned
        if (not mentioned):
            return

        # ignore messages from the bot
        if message.author == client.user:
            logger.info(f"{message.author} == {client.user}")
            return

        # save message as embedding, vectorize
        vector = gpt3_embedding(message)
        timestamp = time()
        timestring = timestring = timestamp_to_datetime(timestamp)
        user = message.author.name
        extracted_message = '%s: %s - %s' % (user, timestring, message.content)
        info = {'speaker': user, 'timestamp': timestamp,'uuid': str(uuid4()), 'vector': vector, 'message': extracted_message, 'timestring': timestring}
        filename = 'log_%s_user' % timestamp
        save_json(f'./src/chat_logs/{filename}.json', info)

        # load past conversations
        history = load_convo()

        # fetch memories (histroy + current input)

        memories = fetch_memories(vector, history, 5)

        # create notes from memories

        current_notes, vector = summarize_memories(memories)

        print(current_notes)
        print('-------------------------------------------------------------------------------')

        add_notes(current_notes)

        if len(notes_history) >= 2:
            print(notes_history[-2])
        else:
            print("The list does not have enough elements to access the second-to-last element.")


        # create a Message object from the notes
        message_notes = Message(user='memories', text=current_notes)
        
        # create a Message object from the notes_history for context

        context_notes = None
        
        if len(notes_history) >= 2:
            context_notes = Message(user='context', text=notes_history[-2])
        else:
            print("The list does not have enough elements create context")


        # wait a bit in case user has more messages
        if SECONDS_DELAY_RECEIVING_MSG > 0:
            await asyncio.sleep(SECONDS_DELAY_RECEIVING_MSG)
            if is_last_message_stale(
                interaction_message=message,
                last_message=channel.last_message,
                bot_id=client.user.id,
            ):
                # there is another message, so ignore this one
                return

        logger.info(
            f"channel message to process - {message.author}: {message.content[:50]} - {channel.name} {channel.jump_url}"
        )

        channel_messages = [
            discord_message_to_message(message)
            async for message in channel.history(limit=MAX_MESSAGE_HISTORY)
        ]
        channel_messages = [x for x in channel_messages if x is not None]
        channel_messages.reverse()
        channel_messages.insert(0, message_notes)
        if context_notes:
            channel_messages.insert(0, context_notes)


        # generate the response
        async with channel.typing():
            response_data = await generate_completion_response(
                messages=channel_messages, user=message.author
            )
            vector = gpt3_response_embedding(response_data)
            timestamp = time()
            timestring = timestring = timestamp_to_datetime(timestamp)
            user = client.user.name
            extracted_message = '%s: %s - %s' % (user, timestring, response_data.reply_text)
            info = {'speaker': user, 'timestamp': timestamp,'uuid': str(uuid4()), 'vector': vector, 'message': extracted_message, 'timestring': timestring}
            filename = 'log_%s_bot' % timestamp
            save_json(f'./src/chat_logs/{filename}.json', info)


        # send response
        await process_response(
            channel=message.channel, user=message.author, response_data=response_data
        )
    except Exception as e:
        logger.exception(e)


client.run(DISCORD_BOT_TOKEN)
