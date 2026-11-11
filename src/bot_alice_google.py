import discord
import asyncio

from src.system_log import LogSystem
from src.system_time import TimeSystem
from src.bot_base import GoogleBot

class Alice(GoogleBot):
    def __init__(self):
        super().__init__(
            token_env_var="ALICE",
            bot_name="Alice Liddell",
            model_name="gemini-3.6-flash",
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

            if message.content.startswith('Where is Alice?'):
                await message.channel.send(f"I'm here, {message.author.mention}!")

            if self.discord_client.user.mentioned_in(message):
                try:
                    # Get the channel ID
                    channel_id = message.channel.id
                    # Get the username
                    user_name = message.author.name

                    # Handle user message
                    user_prompt = message.content.replace(f'<@{self.discord_client.user.id}>', '').strip()
                    if not user_prompt:
                        raise Exception(f"Trouble with handling user's message")
                    
                    user_prompt = "At " + TimeSystem().get_time() + f", user {user_name} said: " + user_prompt
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
                        max_retries = 3
                        retry_delay = 2
                        response = None

                        # Generate a response in another thread with a retry mechanism
                        for attempt in range(max_retries):
                            try:
                                response = await asyncio.to_thread(
                                    chat_session.send_message,
                                    user_prompt
                                )
                                break
                            except Exception as e:
                                if attempt < max_retries - 1:
                                    LogSystem().write('w', f"Model is having issue responding: {e} (Attempt {attempt+1}/{max_retries}). Retrying in {retry_delay}s... Error: {e}")
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= 2
                                    continue
                                else:
                                    raise e
                        
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
                        if len(self.chat_history[channel_id]) > 30:
                            # Keep the system prompt and 18 earliest messages
                            self.chat_history[channel_id] = self.chat_history[channel_id][-30:]

                        # Update history file
                        self.push_history()
                        
                        # Send reply
                        await message.channel.send(reply)

                except Exception as e:
                    LogSystem().write('e',f"{e}")
                    await message.channel.send("Sorry, I’m having a bit of an issue.")