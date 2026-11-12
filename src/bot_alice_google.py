import discord
import asyncio
from google.genai import errors

from src.system_log import LogSystem
from src.system_time import TimeSystem
from src.bot_base import GoogleBot

class Alice(GoogleBot):
    # Any account whose id is one of these is able to use some specific commands on the bot.
    bot_permission:list[int] = [794061552545824769,893757479995973643,1199361438460936405,806098560121962553]

    def __init__(self):
        super().__init__(
            token_env_var="ALICE",
            bot_name="Alice Liddell",
            model_name="gemini-3.5-flash-lite",
            history_file="histories/history_alice.json",
            prompt_file="prompts/bot_alice_sysprompt.txt"
        )

        # Configure intents and initialize the client as an instance attribute
        intents = discord.Intents.default()
        intents.message_content = True
        self.discord_client = discord.Client(intents=intents)

        # Register events for client
        @self.discord_client.event
        async def on_ready():
            LogSystem().write('n',f'Successfully logged in as: {self.discord_client.user}')

        @self.discord_client.event
        async def on_message(message:discord.Message):
            if message.author == self.discord_client.user:
                return

            if message.content.startswith(f'Where is Alice?'):
                await message.reply(f"I'm here, {message.author.mention}!")
            
            elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean room ') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean room '):
                # Clear chat history at specific channel id (can only used by some people)
                if message.author.id in Alice.bot_permission:
                    try:
                        # Split the chat into 2 parts, the channel id would be in the second part
                        parts = message.content.split('clean room ')
                        target_channel_id = 0
                        if len(parts) > 1 and parts[1].strip().isdigit():
                            target_channel_id = int(parts[1].strip())
                        
                        # Clean chat history in cache
                        if target_channel_id in self.chat_history:
                            self.chat_history[target_channel_id] = []
                        if target_channel_id in self.chats:
                            del self.chats[target_channel_id]
                        
                        # Update history file
                        self.push_history()
                        await message.reply(f"I have finished cleaning the room.")
                        LogSystem().write('n', f"User {message.author.name} cleared history for channel {target_channel_id}")

                    except Exception as e:
                        await message.reply("Sorry, I couldn't clean the room.")
                        LogSystem().write('e', f"User {message.author.name} got an error while clearing history for channel {target_channel_id}: {e}")
                else:
                    await message.reply("Sorry, I can't do that for you.")

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean this room') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean this room'):
                # Clear chat history at specific channel where the command is in (can only be used by some people)
                if message.author.id in Alice.bot_permission:
                    try:
                        # Get channel id
                        target_channel_id = message.channel.id

                        # Clean chat history in cache
                        if target_channel_id in self.chat_history:
                            self.chat_history[target_channel_id] = []
                        if target_channel_id in self.chats:
                            del self.chats[target_channel_id]

                        # Update history file
                        self.push_history()
                        await message.reply(f"I have finished cleaning the room.")
                        LogSystem().write('n', f"User {message.author.name} cleared history for channel {target_channel_id}")

                    except Exception as e:
                        await message.reply("Sorry, I couldn't clean this room.")
                        LogSystem().write('e', f"User {message.author.name} got an error while clearing history for channel {target_channel_id}: {e}")
                else:
                    await message.reply("Sorry, I can't do that for you.")

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean the house') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean the house'):
                # Clear entire chat history (can only used by me)
                if message.author.id == Alice.bot_permission[0]:
                    try:
                        self.chat_history.clear()
                        self.chats.clear()
                        self.push_history()
                        await message.reply("I have finished cleaning the house.")
                        LogSystem().write('n', f"Master {message.author.name} cleared entire chat history.")
                    except Exception as e:
                        await message.reply("Sorry, I couldn't clean the house.")
                        LogSystem().write('e', f"Error cleaning house: {e}")
                else:
                    await message.reply("Sorry, I can't do that for you.")

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, take a nap') or message.content.startswith(f'<@!{self.discord_client.user.id}>, take a nap'):
                # Clear bot log file (can only used by me)
                if message.author.id == Alice.bot_permission[0]:
                    LogSystem().clear()
                    await message.reply("Goodnight!")
                else:
                    await message.reply("Sorry, I can't do that for you.")

            elif self.discord_client.user.mentioned_in(message):
                try:
                    # Get the channel ID
                    channel_id = message.channel.id
                    # Get the username
                    user_name = message.author.name
                    # Get the user's nickname
                    user_nickname = message.author.display_name

                    # Handle user message
                    # Replace the raw bot ping(s) with bot name call
                    user_message = message.content.replace(f'<@{self.discord_client.user.id}>', self.bot_name).replace(f'<@!{self.discord_client.user.id}>', self.bot_name)
                    if not user_message:
                        raise Exception(f"Trouble with handling user's message")

                    # Replace the raw user ping(s) with name call
                    for member in message.mentions:
                        if member.id == self.discord_client.user.id:
                            continue
                        user_message = user_message.replace(f"<@{member.id}>",f"{member.display_name}").replace(f"<@!{member.id}>",f"{member.display_name}")
                    
                    user_prompt = "At " + TimeSystem().get_time() + f", username {user_name} with nickname {user_nickname} said: " + user_message
                    LogSystem().write('m',user_prompt)

                    # Create new channel chat history/chat session and add system prompt in it if it has not existed yet
                    if channel_id not in self.chats:
                        # Make a formatted history for Google GenAI chat creating function
                        formatted_history = []
                        if channel_id in self.chat_history:
                            for msg in self.chat_history[channel_id]:
                                role = "model" if msg['role'] == "assistant" else msg['role']
                                if role in ["user","model"]:
                                    formatted_history.append({
                                        "role": role,
                                        "parts": [{"text":msg['content']}]
                                    })
                        else:
                            self.chat_history[channel_id] = []

                        self.chats[channel_id] = self.genai_client.chats.create(
                            model=self.model_name,
                            config=self.config,
                            history=formatted_history if formatted_history else None
                        )

                    async with message.channel.typing():
                        # Get chat session based on channel id
                        chat_session = self.chats[channel_id]

                        # Retry mechanism config
                        attempt = 0
                        max_retries = 3
                        retry_delay = 2
                        response = None

                        # Generate a response in another thread with a retry mechanism
                        while attempt <= max_retries:
                            try:
                                response = await asyncio.to_thread(
                                    chat_session.send_message,
                                    user_prompt
                                )
                                break
                            except errors.APIError as e:
                                if e.code not in (503,429):
                                    raise Exception(f"Unable to get response from {self.bot_name}: {e}")
                                if attempt < max_retries:
                                    LogSystem().write('w', f"Model is having issue responding: {e}\nRetrying (attempt {attempt+1}/{max_retries}) in {retry_delay}s...")
                                    await asyncio.sleep(retry_delay)
                                    attempt += 1
                                    retry_delay *= 2
                                    continue
                                else:
                                    raise Exception(f"Timeout while getting response from {self.bot_name}: {e}")
                        
                        # Get the response content
                        reply = response.text
                        formatted_reply = "At " + TimeSystem().get_time() + f", assistant {self.bot_name} said: " + reply
                        LogSystem().write('m',formatted_reply)

                        # Add user's and assistant's messages to chat history
                        self.chat_history[channel_id].append({
                            'role': 'user',
                            'content': user_prompt
                        })
                        self.chat_history[channel_id].append({
                            'role': 'assistant',
                            'content': reply
                        })

                        # Limit chat history length
                        if len(self.chat_history[channel_id]) > 40:
                            # Keep the system prompt and 18 earliest messages
                            self.chat_history[channel_id] = self.chat_history[channel_id][-40:]

                        # Update history file
                        self.push_history()
                        
                        # Send reply
                        await message.reply(reply)

                except Exception as e:
                    LogSystem().write('e',f"{e}")
                    await message.reply("Sorry, I’m having a bit of an issue.")