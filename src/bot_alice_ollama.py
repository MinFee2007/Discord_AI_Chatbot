# import discord
# import ollama
# import asyncio

# from src.system_log import LogSystem
# from src.system_time import TimeSystem
# from src.bot_base import OllamaBot

# class Alice(OllamaBot):
#     def __init__(self):
#         super().__init__(
#             token_env_var="ALICE",
#             bot_name="Alice Liddel",
#             model_name="llama3.1:8b",
#             history_file="histories/history_alice.json",
#             prompt_file="prompts/bot_alice_sysprompt.txt"
#         )

#         # Register events for client
#         @self.discord_client.event
#         async def on_ready():
#             LogSystem().write('n',f'Successfully logged in as: {self.discord_client.user}')

#         @self.discord_client.event
#         async def on_message(message:discord.Message):
#             if message.author == self.discord_client.user:
#                 return

#             if message.content.startswith('Where is Alice?'):
#                 await message.channel.send(f"I'm here, {message.author.mention}!")

#             if self.discord_client.user.mentioned_in(message):
#                 try:
#                     # Get the channel ID
#                     channel_id = message.channel.id
#                     # Get the username
#                     user_name = message.author.name
#                     # Get the user's nickname
#                     user_nickname = message.author.display_name

#                     # Handle prompt from user
#                     # Replace the raw bot ping(s) with bot name call
#                     user_message = message.content.replace(f'<@{self.discord_client.user.id}>',self.bot_name)
#                     if not user_message:
#                         raise Exception(f"Trouble with handling user's message")

#                     # Replace the raw user ping(s) with name call
#                     for member in message.mentions:
#                         if member.id == self.discord_client.user.id:
#                             continue
#                         user_message = user_message.replace(f"<@{member.id}>",f"{user_nickname}")
#                         user_message = user_message.replace(f"<@!{member.id}>",f"{user_nickname}")
                    
#                     user_prompt = "At " + TimeSystem().get_time() + f", username {user_name} with nickname {user_nickname} said: " + user_message
#                     LogSystem().write('m',user_prompt)

#                     # Create new channel chat history and add system prompt in it if it has not existed yet
#                     file = open(self.prompt_file,'r')
#                     if not file:
#                         raise Exception(f"Unable to find {self.bot_name} system prompt file")
#                     system_prompt = file.read()
#                     file.close()
                    
#                     if channel_id not in self.chat_history:
#                         self.chat_history[channel_id] = [
#                             {
#                                 'role': 'system',
#                                 'content': system_prompt
#                             }
#                         ]

#                     # Add user's message to chat history
#                     self.chat_history[channel_id].append({
#                         'role': 'user',
#                         'content': user_prompt
#                     })

#                     # Limit chat history length
#                     if len(self.chat_history[channel_id]) > 31:
#                         # Keep the system prompt and 18 earliest messages
#                         self.chat_history[channel_id] = [self.chat_history[channel_id][0]] + self.chat_history[channel_id][-28:]

#                     async with message.channel.typing():
#                         # Generate a response in another thread
#                         response = await asyncio.to_thread(
#                             ollama.chat,
#                             model=self.model_name,
#                             messages=self.chat_history[channel_id]
#                         )

#                         # Get the response content
#                         reply = response['message']['content']
#                         formatted_reply = "At " + TimeSystem().get_time() + f", assistant {self.bot_name} said: " + reply
#                         LogSystem().write('m',formatted_reply)

#                         # Add the assistant's reply into the chat history
#                         self.chat_history[channel_id].append({
#                             'role': 'assistant',
#                             'content': reply
#                         })

#                         # Update history file
#                         self.push_history()
                        
#                         # Send reply
#                         await message.channel.send(reply)

#                 except Exception as e:
#                     LogSystem().write('e',f"{e}")
#                     await message.channel.send("Sorry, I’m having a bit of an issue.")