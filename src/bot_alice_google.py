import discord
import asyncio
import datetime
import requests
import os
import json
from google.genai import errors, types

from src.system_log import LogSystem
from src.bot_base import GoogleBot
from src.output_weather import WeatherRequest

class Alice(GoogleBot):
    # Any account whose id is one of these is able to use some specific commands on the bot.
    bot_permission:list[int] = [794061552545824769,1066379211780141126,893757479995973643,806098560121962553]

    def __init__(self):
        super().__init__(
            token_env_var="ALICE",
            bot_name="Alice Liddell",
            model_name="gemini-3.5-flash-lite",
            history_file="histories/history_alice.json",
            prompt_file="prompts/bot_alice_sysprompt.txt",
            message_limit = 60
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
            
            elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean room ') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean room '):
                # Clear chat history at specific channel id (can only be used by some people)
                await self.clear_history_id(message=message)

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean this room') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean this room'):
                # Clear chat history at specific channel where the command is in (can only be used by some people)
                await self.clear_history_this_channel(message=message)

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, clean the house') or message.content.startswith(f'<@!{self.discord_client.user.id}>, clean the house'):
                # Clear entire chat history (can only be used by me)
                await self.clear_history_all(message=message)

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, write a new diary') or message.content.startswith(f'<@!{self.discord_client.user.id}>, write a new diary'):
                # Clear bot log file (can only be used by me)
                await self.clear_log(message=message)

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, take a nap') or message.content.startswith(f'<@!{self.discord_client.user.id}>, take a nap'):
                # Put the bot into sleep mode (can only be used by me)
                await self.sleep(message=message)

            elif message.content.startswith(f'<@{self.discord_client.user.id}>, wake up') or message.content.startswith(f'<@!{self.discord_client.user.id}>, wake up'):
                # Put the bot out of sleep mode (can only be used by me)
                await self.wake(message=message)

            elif self.discord_client.user.mentioned_in(message):
                if self.is_sleeping:
                    await message.reply(f"zzz *{self.bot_name} is sleeping peacefully* zzz")
                    return
                if "weather" in message.content:
                    # Weather forecasting
                    await self.weather_forecast(message=message)
                else:
                    # Communicate with chatbot (can be used by everyone)
                    await self.chat(message=message)


    async def clear_history_id(self,message:discord.Message):
        """Clear chat history at specific channel id"""
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
                self.push_history_file()
                await message.reply(f"I have finished cleaning the room.")
                LogSystem().write('n', f"User {message.author.name} cleared history for channel {target_channel_id}")

            except Exception as e:
                await message.reply("Sorry, I couldn't clean the room.")
                LogSystem().write('e', f"User {message.author.name} got an error while clearing history for channel {target_channel_id}: {e}")
        else:
            await message.reply("Sorry, I can't do that for you.")

    async def clear_history_this_channel(self,message:discord.Message):
        """Clear chat history at specific channel where the command is in"""
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
                self.push_history_file()
                await message.reply(f"I have finished cleaning the room.")
                LogSystem().write('n', f"User {message.author.name} cleared history for channel {target_channel_id}")

            except Exception as e:
                await message.reply("Sorry, I couldn't clean this room.")
                LogSystem().write('e', f"User {message.author.name} got an error while clearing history for channel {target_channel_id}: {e}")
        else:
            await message.reply("Sorry, I can't do that for you.")

    async def clear_history_all(self,message:discord.Message):
        """Clear entire chat history"""
        if message.author.id == Alice.bot_permission[0]:
            try:
                self.chat_history.clear()
                self.chats.clear()
                self.push_history_file()
                await message.reply("I have finished cleaning the house.")
                LogSystem().write('n', f"User {message.author.name} cleared entire chat history.")
            except Exception as e:
                await message.reply("Sorry, I couldn't clean the house.")
                LogSystem().write('e', f"Error cleaning house: {e}")
        else:
            await message.reply("Sorry, I can't do that for you.")

    async def clear_log(self,message:discord.Message):
        """Clear bot log file"""
        if message.author.id == Alice.bot_permission[0]:
            LogSystem().clear()
            await message.reply("I have bought a new diary.")
        else:
            await message.reply("Sorry, I can't do that for you.")

    async def sleep(self,message:discord.Message):
        """Put the bot into sleep mode"""
        if message.author.id == Alice.bot_permission[0]:
            self.is_sleeping = True
            LogSystem().write('n',f"User {message.author.name} put {self.bot_name} into sleep")
            await message.reply("Goodnight!")
        else:
            await message.reply("Sorry, I can't do that for you.")

    async def wake(self,message:discord.Message):
        """Put the bot out of sleep mode"""
        if message.author.id == Alice.bot_permission[0]:
            self.is_sleeping = False
            LogSystem().write('n',f"User {message.author.name} woke {self.bot_name} up")
            await message.reply("Good morning!")
        else:
            await message.reply("Sorry, I can't do that for you.")

    def handle_user_message(self,message:discord.Message):
        """Handle user message"""
        # Replace the raw bot ping(s) with bot name call
        user_message = message.content.replace(f'<@{self.discord_client.user.id}>', self.bot_name).replace(f'<@!{self.discord_client.user.id}>', self.bot_name)
        if not user_message:
            raise Exception(f"Trouble with handling user's message")

        # Replace the raw user ping(s) with name call
        for member in message.mentions:
            if member.id == self.discord_client.user.id:
                continue
            user_message = user_message.replace(f"<@{member.id}>",f"{member.display_name}").replace(f"<@!{member.id}>",f"{member.display_name}")

        return user_message

    def format_history(self,channel_id:int):
        """Make a formatted history for Google GenAI chat creating function"""
        formatted_history = []
        if channel_id in self.chat_history:
            for msg in self.chat_history[channel_id]:
                role = "model" if msg["role"] == "assistant" else msg["role"]
                formatted_history.append({
                    "role": role,
                    "parts": [{"text":msg["content"]}]
                })

        else: self.chat_history[channel_id] = []

        return formatted_history

    def ensure_chat_session(self, channel_id: int):
        """Create new channel chat session if it does not exist yet"""
        if channel_id not in self.chats:
            formatted_history = self.format_history(channel_id)
            self.chats[channel_id] = self.genai_client.chats.create(
                model=self.model_name,
                config=self.config,
                history=formatted_history if formatted_history else None
            )

    async def get_response(self,user_prompt:str,channel_id:int,response_config:types.GenerateContentConfig|None=None):
        """Send a prompt to the model and get response"""
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
                    message=user_prompt,
                    config=response_config
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
        if response_config:
            return response.parsed
        return response.text

    def push_chat_history(self,channel_id:int,user_prompt:str,response:str):
        """Add user's and assistant's messages to chat history"""
        # Append user's message to chat history
        self.chat_history[channel_id].append({
            'role': 'user',
            'content': user_prompt
        })

        # Append assistant's message to chat history
        self.chat_history[channel_id].append({
            'role': 'assistant',
            'content': response
        })

        # Limit chat history length
        if len(self.chat_history[channel_id]) > self.message_limit:
            # Keep a specific number of earliest messages
            self.chat_history[channel_id] = self.chat_history[channel_id][-self.message_limit:]

    async def send_reply(self, message: discord.Message, text: str):
        """Send messages with guaranteed fragmentation for long message lengths."""
        max_len = 1950
        for i in range(0, len(text), max_len):
            chunk = text[i:i + max_len]
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)
    
    async def chat(self,message:discord.Message):
        """Communicate with chatbot"""
        try:
            # Get the channel ID
            channel_id = message.channel.id
            # Get the username
            user_id = message.author.id
            # Get the user's nickname
            user_nickname = message.author.display_name
            # Handle user message
            user_message = self.handle_user_message(message=message)

            # Format into prompt
            user_prompt = "At " + str(datetime.datetime.now()) + f", user with ID {user_id} and nickname {user_nickname} said: " + user_message
            LogSystem().write('m',user_prompt)

            # Create new channel chat history/chat session and add system prompt in it if it has not existed yet
            self.ensure_chat_session(channel_id=channel_id)

            async with message.channel.typing():
                # Send a prompt to the model and get response
                reply = await self.get_response(user_prompt=user_prompt, channel_id=channel_id)
                
                # Format the response
                formatted_reply = "At " + str(datetime.datetime.now()) + f", assistant {self.bot_name} said: " + reply
                LogSystem().write('m', formatted_reply)

                # Update chat history
                self.push_chat_history(channel_id=channel_id, user_prompt=user_prompt, response=reply)

                # Update history file
                self.push_history_file()
                
                # Send reply
                await self.send_reply(message=message,reply=reply)

        except Exception as e:
            LogSystem().write('e',f"{e}")
            await message.reply("Sorry, I’m having a bit of an issue.")

    async def extract_weather_request(self, user_prompt: str) -> WeatherRequest:
            """Extract structured WeatherRequest independently without polluting chat history"""
            extraction_prompt = (
                f"{user_prompt}\n\n"
                "Analyze the user's message above and extract the requested real-world destinations "
                "and number of forecast days (0 for current weather only, up to 3 days ahead). "
                "If the user is not actually asking for a weather report or forecast, return empty lists."
            )
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WeatherRequest,
            )
    
            attempt = 0
            max_retries = 3
            retry_delay = 2
    
            while attempt <= max_retries:
                try:
                    response = await asyncio.to_thread(
                        self.genai_client.models.generate_content,
                        model=self.model_name,
                        contents=extraction_prompt,
                        config=config
                    )
                    return response.parsed
                except errors.APIError as e:
                    if e.code not in (503, 429):
                        raise Exception(f"Unable to extract weather request: {e}")
                    if attempt < max_retries:
                        LogSystem().write('w', f"Model is having issue extracting weather request: {e}\nRetrying (attempt {attempt+1}/{max_retries}) in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        attempt += 1
                        retry_delay *= 2
                    else:
                        raise Exception(f"Timeout while extracting weather request: {e}")

    async def get_weather(self, weather_request:WeatherRequest):
        """Fetch and parse weather information from WeatherAPI"""
        weather_info:dict = {}
        weather_api_url = "https://api.weatherapi.com/v1/forecast.json"
        api_key = os.getenv("WEATHER_API_KEY")

        if not api_key:
            LogSystem().write('e', "WEATHER_API_KEY is not set in environment variables.")
            return weather_info

        count = min(len(weather_request.destinations), len(weather_request.forecast_days),3)

        for i in range(count):
            destination = weather_request.destinations[i]
            # WeatherAPI 'days' parameter requires at least 1 (1 = today only, 2 = today + tomorrow, etc.)
            req_days = max(0, min(weather_request.forecast_days[i], 3))
            api_days = 1 if req_days == 0 else req_days + 1
            
            # Retry mechanism config
            attempt = 0
            max_retries = 3
            retry_delay = 2

            # Parameters for HTTP request
            params = {
                'key': api_key,
                'q': destination,
                'days': api_days,
                'aqi': 'no',
                'alerts': 'no'
            }
            while attempt <= max_retries:
                try:
                    response = await asyncio.to_thread(
                        requests.get,
                        url=weather_api_url,
                        params=params,
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Extract data and format weather info
                    location_name = f"{data['location']['name']}, {data['location']['country']}"
                    city_data = {
                        "local_time": data["location"]["localtime"],
                        "current": {
                            "condition": data["current"]["condition"]["text"],
                            "temp_c": data["current"]["temp_c"],
                            "feelslike_c": data["current"]["feelslike_c"],
                            "humidity": data["current"]["humidity"],
                            "wind_kph": data["current"]["wind_kph"],
                            "uv": data["current"]["uv"]
                        }
                    }

                    # Include daily forecast details if the user asked for forecast days (> 0)
                    if req_days > 0 and "forecast" in data:
                        city_data["forecast"] = {}
                        for day_entry in data["forecast"]["forecastday"]:
                            date_str = day_entry["date"]
                            day_summary = day_entry["day"]
                            city_data["forecast"][date_str] = {
                                "condition": day_summary["condition"]["text"],
                                "maxtemp_c": day_summary["maxtemp_c"],
                                "mintemp_c": day_summary["mintemp_c"],
                                "avgtemp_c": day_summary["avgtemp_c"],
                                "avghumidity": day_summary["avghumidity"],
                                "daily_chance_of_rain": day_summary["daily_chance_of_rain"],
                                "maxwind_kph": day_summary["maxwind_kph"],
                                # Sample key 3-hour intervals to keep context concise
                                "hourly_highlights": {
                                    h["time"].split(" ")[1]: {
                                        "temp_c": h["temp_c"],
                                        "condition": h["condition"]["text"],
                                        "chance_of_rain": h["chance_of_rain"]
                                    }
                                    for h in day_entry.get("hour", [])
                                    if h["time"].endswith(("06:00", "09:00", "12:00", "15:00", "18:00", "21:00"))
                                }
                            }

                    weather_info[location_name] = city_data
                    break
                
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries:
                        LogSystem().write('w', f"Having issue getting weather info for {destination}: {e}\nRetrying (attempt {attempt+1}/{max_retries}) in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        attempt += 1
                        retry_delay *= 2
                        continue
                    else:
                        LogSystem().write('e', f"Failed to get weather info for {destination} after retries: {e}")
                        continue

        return weather_info

    async def weather_forecast(self,message:discord.Message):
        """Weather forecasting"""
        try:
            # Get the channel ID
            channel_id = message.channel.id
            # Get the username
            user_id = message.author.id
            # Get the user's nickname
            user_nickname = message.author.display_name
            # Handle user message
            user_message = self.handle_user_message(message=message)

            # Format into prompt
            user_prompt = "At " + str(datetime.datetime.now()) + f", user with ID {user_id} and nickname {user_nickname} said: " + user_message
            LogSystem().write('m',user_prompt)

            # Create new channel chat history/chat session and add system prompt in it if it has not existed yet
            self.ensure_chat_session(channel_id=channel_id)

            async with message.channel.typing():
                # Extract destinations and days without polluting chat history
                weather_request: WeatherRequest = await self.extract_weather_request(user_prompt=user_prompt)
                reply = None

                # Case where the user did not ask for weather information
                if not weather_request or len(weather_request.destinations) == 0:
                    reply = await self.get_response(user_prompt=user_prompt, channel_id=channel_id)

                # Case where the user did ask for weather information
                else:
                    # Fetch real weather data from WeatherAPI
                    weather_info = await self.get_weather(weather_request=weather_request)

                    # Build final prompt with weather context for bot
                    if weather_info:
                        weather_json = json.dumps(weather_info, ensure_ascii=False, indent=2)
                        final_prompt = (
                            f"{user_prompt}\n\n"
                            f"[System Weather Data]:\n{weather_json}\n\n"
                            f"System Instruction: Use the real-time weather data above to answer the user naturally in your persona as {self.bot_name}. "
                            "Mention temperatures in Celsius (and optionally Fahrenheit if helpful), weather conditions, and relevant forecast details clearly."
                        )
                    else:
                        final_prompt = (
                            f"{user_prompt}\n\n"
                            "System Instruction: The system tried to look up the weather for the requested location(s), "
                            "but could not find valid weather data or the weather service is currently unavailable. "
                            f"Apologize politely in character as {self.bot_name} and ask them to double-check the location name."
                        )
                    # Send prompt to model and get response based on system instruction
                    reply = await self.get_response(user_prompt=final_prompt, channel_id=channel_id)

                # Log, save history, reply
                formatted_reply = f"At {datetime.datetime.now()}, assistant {self.bot_name} said: {reply}"
                LogSystem().write('m', formatted_reply)

                self.push_chat_history(channel_id=channel_id, user_prompt=user_prompt, response=reply)
                self.push_history_file()

                await self.send_reply(message=message,reply=reply)

        except Exception as e:
            LogSystem().write('e',f"{e}")
            await message.reply("Sorry, I’m having a bit of an issue.")