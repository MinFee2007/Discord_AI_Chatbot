import discord

from src.system_log import LogSystem
from src.bot_base import GoogleBot

class Alice(GoogleBot):

    def __init__(self):
        super().__init__(
            token_env_var="ALICE",
            bot_name="Alice Liddell",
            model_name="gemini-3.5-flash-lite",
            history_filepath="histories/history_alice.json",
            prompt_filepath="prompts/bot_alice_sysprompt.txt",
            permission_filepath="permission/bot_alice_permission_cmd.txt",
            forbidden_channels_filepath="permission/bot_alice_forbidden_channel.txt",
            forbidden_users_filepath="permission/bot_alice_forbidden_user.txt",
            message_limit=60
        )

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

            elif self.discord_client.user.mentioned_in(message):
                if message.content.startswith(f'<@{self.discord_client.user.id}>, clean room ') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean room '):
                    # Clear chat history at specific channel id (can only be used by some people)
                    if (message.author.id in self.bot_permission_users) and (message.author.id not in self.forbidden_users):
                        try:
                            # Split the chat into 2 parts, the channel id would be in the second part
                            parts = message.content.split('clean room ')
                            arg = parts[1].strip() if len(parts) > 1 else ""
                            target_channel_id = None
                            if arg.isdigit():
                                target_channel_id = int(parts[1].strip())
                            else:
                                raise Exception("Unable to find channel ID")
                            # Clear chat history
                            self.clear_history_id(target_channel_id=target_channel_id)
                
                            # Notify
                            await message.reply(f"I have finished cleaning the room.")
                            LogSystem().write('n', f"User {message.author.name} cleared history for channel {target_channel_id}")
                
                        except Exception as e:
                            await message.reply("Sorry, I couldn't clean the room.")
                            LogSystem().write('e', f"User {message.author.name} got an error while clearing history for channel {target_channel_id}: {e}")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean this room') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean this room'):
                    # Clear chat history at specific channel where the command is in (can only be used by some people)
                    if (message.author.id in self.bot_permission_users) and (message.author.id not in self.forbidden_users):
                        try:
                            # Get channel id
                            target_channel_id = message.channel.id
                
                            # Clear chat history
                            self.clear_history_id(target_channel_id=target_channel_id)
                
                            # Notify
                            await message.reply(f"I have finished cleaning the room.")
                            LogSystem().write('n', f"User {message.author.name} cleared history for channel {target_channel_id}")
                
                        except Exception as e:
                            await message.reply("Sorry, I couldn't clean this room.")
                            LogSystem().write('e', f"User {message.author.name} got an error while clearing history for channel {target_channel_id}: {e}")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean the house') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean the house'):
                    # Clear entire chat history (can only be used by me)
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        try:
                            self.clear_history_all()
                            await message.reply("I have finished cleaning the house.")
                            LogSystem().write('n', f"User {message.author.name} cleared entire chat history.")
                        except Exception as e:
                            await message.reply("Sorry, I couldn't clean the house.")
                            LogSystem().write('e', f"Error cleaning house: {e}")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, write a new diary') or message.content.startswith(f'<@!{self.discord_client.user.id}>, write a new diary'):
                    # Clear bot log file (can only be used by me)
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        LogSystem().clear()
                        await message.reply("I have bought a new diary.")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, take a nap') or message.content.startswith(f'<@!{self.discord_client.user.id}>, take a nap'):
                    # Put the bot into sleep mode (can only be used by me)
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        self.is_sleeping = True
                        LogSystem().write('n',f"User {message.author.name} put {self.bot_name} into sleep")
                        await message.reply("Goodnight!")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, wake up') or message.content.startswith(f'<@!{self.discord_client.user.id}>, wake up'):
                    # Put the bot out of sleep mode (can only be used by me)
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        self.is_sleeping = False
                        LogSystem().write('n',f"User {message.author.name} woke {self.bot_name} up")
                        await message.reply("Good morning!")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, do not come in ') or message.content.startswith(f'<@!{self.discord_client.user.id}>, do not come in '):
                    # Add a channel into forbidden channels (the command can be either "do not come in here" or "do not come in <channel_id>")
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        try:
                            # Get target channel id
                            target_channel_id = None
                            parts = message.content.split("in ",1)
                            arg = parts[1].strip if len(parts) > 1 else ""
                            if arg == 'here':
                                target_channel_id = message.channel.id
                            elif arg.isdigit():
                                target_channel_id = int(arg)
                            else:
                                raise Exception(f"Unable to find channel ID from message: {message.content}")
                            # Abadon channel
                            self.abandon_channel(channel_id=target_channel_id)
                            await message.reply("Understood.")

                        except Exception as e:
                            await message.reply("Sorry, can you repeat that?")
                            LogSystem().write('e', f"Error adding forbidden channel: {e}")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, you can come in ') or message.content.startswith(f'<@!{self.discord_client.user.id}>, you can come in '):
                    # Remove a channel from forbidden channels (the command can be either "you can come in here" or "you can come in <channel_id>")
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        try:
                            # Get target channel id
                            target_channel_id = None
                            parts = message.content.split("in ",1)
                            arg = parts[1].strip if len(parts) > 1 else ""
                            if arg == 'here':
                                target_channel_id = message.channel.id
                            elif arg.isdigit():
                                target_channel_id = int(parts[1].strip())
                            else:
                                raise Exception(f"Unable to find channel ID from message: {message.content}")
                            # Removing channel from forbidden channels
                            self.unabandon_channel(channel_id=target_channel_id)
                            await message.reply("Understood.")

                        except Exception as e:
                            await message.reply("Sorry, can you repeat that?")
                            LogSystem().write('e', f"Error removing forbidden channel: {e}")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif message.content.startswith(f'<@{self.discord_client.user.id}>, stay away from ') or message.content.startswith(f'<@!{self.discord_client.user.id}>, stay away from '):
                    # Add a user into forbidden users ("stay away from <user_id>")
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        try:
                            # Get target user id
                            target_user_id = None
                            parts = message.content.split("from ")
                            if len(parts) > 1 and parts[1].strip().isdigit():
                                target_user_id = int(parts[1].strip())
                            else:
                                raise Exception(f"Unable to find user ID from message: {message.content}")
                            # Ban user
                            self.ban_user(target_user_id)
                            await message.reply("Understood.")

                        except Exception as e:
                            await message.reply("Sorry, can you repeat that?")
                            LogSystem().write('e', f"Error banning user: {e}")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")

                elif (" is a friend" in message.content) and (message.content.startswith(f'<@{self.discord_client.user.id}>, ') or message.content.startswith(f'<@!{self.discord_client.user.id}>, ')):
                    # Remove a user from forbidden users ("user_id is a friend")
                    if len(self.bot_permission_users) == 0 or (message.author.id == self.bot_permission_users[0]):
                        try:
                            parts = message.content.split(f"{self.discord_client.user.id}>, ")
                            if len(parts) > 1: parts = parts[1].split(" is a friend")
                            else: raise Exception(f"Unable to find user id from message: {message.content}")
                            if parts[0].strip().isdigit():
                                self.unban_user(user_id=int(parts[0].strip()))
                                await message.reply("Understood.")
                            else: raise Exception(f"Unable to find user id from message: {message.content}")

                        except Exception as e:
                            await message.reply("Sorry, can you repeat that?")
                            LogSystem().write('e', f"Error unbanning user: {e}")
                    else:
                        if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                            return
                        await message.reply("Sorry, I can't do that for you.")
                else:
                    # Botchat features
                    if (message.author.id in self.forbidden_users) or (message.channel.id in self.forbidden_channels):
                        return
                    if self.is_sleeping:
                        await message.reply(f"zzz *{self.bot_name} is sleeping peacefully* zzz")
                        return
                    if " weather " in message.content.lower():
                        # Weather forecasting
                        try:
                            await self.weather_forecast(message=message)
                        except Exception as e:
                            LogSystem().write('e',f"{e}")
                            await message.reply("Sorry, I’m having a bit of an issue.")
                    else:
                        # Communicate with chatbot (can be used by everyone)
                        try:
                            await self.chat(message=message)
                        
                        except Exception as e:
                            LogSystem().write('e',f"{e}")
                            await message.reply("Sorry, I’m having a bit of an issue.")