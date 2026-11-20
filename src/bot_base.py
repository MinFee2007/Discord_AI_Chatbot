import json
import datetime
import os
import discord
import asyncio
import requests
from google import genai
from google.genai import types, chats, errors

from src.output_weather import WeatherRequest
from src.system_log import LogSystem

class BaseBot:
    def __init__(self, token_env_var=None, bot_name=None, model_name=None, history_filepath=None, prompt_filepath=None, permission_filepath=None, forbidden_channels_filepath=None, forbidden_users_filepath=None, message_limit=60):
        self.token_env_var = token_env_var
        self.bot_name = bot_name
        self.model_name = model_name
        self.history_filepath = history_filepath
        self.prompt_filepath = prompt_filepath
        self.permission_filepath = permission_filepath
        self.forbidden_channels_filepath = forbidden_channels_filepath
        self.forbidden_users_filepath = forbidden_users_filepath
        self.message_limit = message_limit
        self.chat_history: dict[int, list[dict[str, str]]] = {}
        self.is_sleeping = False
        self.bot_permission_users:list[int] = []
        self.forbidden_channels:list[int] = []
        self.forbidden_users:list[int] = []

        # Configure intents and initialize the client as an instance attribute
        intents = discord.Intents.default()
        intents.message_content = True
        self.discord_client = discord.Client(intents=intents)
        
        # Load previous chat history
        self.pull_history_file()

        # Get user(s) with command permission
        with open(self.permission_filepath,"r") as file:
            for id in file:
                self.bot_permission_users.append(int(id.strip()))

        # Get forbidden channels which the bot are not allowed to operate in
        with open(self.forbidden_channels_filepath,"r") as file:
            for id in file:
                self.forbidden_channels.append(int(id.strip()))

        # Get forbidden user(s)
        with open(self.forbidden_users_filepath,"r") as file:
            for id in file:
                self.forbidden_users.append(int(id.strip()))

    def push_history_file(self):
        if not self.history_filepath:
            LogSystem().write('e',"Bot's history file has not been initialized yet.")
            return
        # Automatically create history file
        dir_name = os.path.dirname(self.history_filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(self.history_filepath, 'w', encoding='utf-8') as file:
            json.dump(self.chat_history,indent=4,ensure_ascii=False,fp=file)
    
    def pull_history_file(self):
        if not self.history_filepath:
            LogSystem().write('e',"Bot's history file has not been initialized yet.")
            return
        if os.path.exists(self.history_filepath):
            try:
                with open(self.history_filepath, 'r', encoding='utf-8') as file:
                    raw_data = json.load(file)
                    self.chat_history = {int(k): v for k, v in raw_data.items()}
            except Exception as e:
                LogSystem().write('e', f"Error loading history file: {e}")
                self.chat_history = {}
        else:
            LogSystem().write('e', "Unable to find history file")
            self.chat_history = {}

    def run(self):
        if not self.token_env_var:
            LogSystem().write('e',"Bot's token environment variable has not been initialized yet")
            return
        token = os.getenv(self.token_env_var)
        if token:
            self.discord_client.run(token)
        else:
            LogSystem().write('e',f"Unable to find environment variable {self.token_env_var}")

    def clear_history_id(self,target_channel_id:int):
        """Clear chat history at specific channel id"""
        # Clean chat history in cache
        if target_channel_id in self.chat_history:
            self.chat_history[target_channel_id] = []
        
        # Update history file
        self.push_history_file()

    def clear_history_all(self):
        """Clear entire chat history"""
        self.chat_history.clear()
        self.push_history_file()

    def abandon_channel(self, channel_id:int):
        """Add a channel into forbidden channels"""
        if channel_id not in self.forbidden_channels:
            self.forbidden_channels.append(channel_id)
            with open(self.forbidden_channels_filepath,"a") as file:
                file.write(f"{channel_id}\n")

    def unabandon_channel(self, channel_id:int):
        """Remove a channel from forbidden channels"""
        if channel_id in self.forbidden_channels:
            self.forbidden_channels.remove(channel_id)
            with open(self.forbidden_channels_filepath,"w") as file:
                for id in self.forbidden_channels:
                    file.write(f"{id}\n")

    def ban_user(self, user_id:int):
        """Add a user into forbidden users"""
        if user_id not in self.forbidden_users:
            self.forbidden_users.append(user_id)
            with open(self.forbidden_users_filepath,"a") as file:
                file.write(f"{user_id}\n")

    def unban_user(self, user_id:int):
        """Remove a user from forbidden users"""
        if user_id in self.forbidden_users:
            self.forbidden_users.remove(user_id)
            with open(self.forbidden_users_filepath,"w") as file:
                for id in self.forbidden_users:
                    file.write(f"{id}\n")

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

    def ensure_chat_session(self, channel_id: int):
        """Create new channel/chat session if it does not exist yet"""
        if channel_id not in self.chat_history:
            self.chat_history[channel_id] = []

    async def get_response(self, user_prompt: str, channel_id: int):
        """Send a prompt to the model and get response"""
        pass

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
            await self.send_reply(message=message,text=reply)

    async def weather_forecast(self,message:discord.Message):
        """Weather forecasting"""
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

            await self.send_reply(message=message,text=reply)

    def __del__(self):
        try:
            if self.bot_name:
                LogSystem().write('n',f"Bot {self.bot_name} has stopped working")
        except Exception:
            pass

class OllamaBot(BaseBot):
    def __init__(self, token_env_var=None, bot_name=None, model_name=None, history_file=None, prompt_file=None):
        super().__init__(
            token_env_var,
            bot_name, model_name,
            history_file,
            prompt_file
        )

class GoogleBot(BaseBot):
    def __init__(self, token_env_var=None, bot_name=None, model_name=None, history_filepath=None, prompt_filepath=None, permission_filepath=None, forbidden_channels_filepath=None, forbidden_users_filepath=None, message_limit=60):
        super().__init__(
            token_env_var,
            bot_name,
            model_name,
            history_filepath,
            prompt_filepath,
            permission_filepath,
            forbidden_channels_filepath,
            forbidden_users_filepath,
            message_limit
        )
        self.genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.config = None
        with open(self.prompt_filepath,'r') as file:
            sysprompt = file.read()
            self.config = types.GenerateContentConfig(
                system_instruction=sysprompt,
                safety_settings=[
                    types.SafetySetting(
                        category='HARM_CATEGORY_HATE_SPEECH',
                        threshold='BLOCK_ONLY_HIGH'
                    )
                ]
            )
        self.chats: dict[int,chats.Chat] = {}

    def clear_history_id(self,target_channel_id:int):
        """Clear chat history at specific channel id"""
        super().clear_history_id(target_channel_id=target_channel_id)
        if target_channel_id in self.chats:
            del self.chats[target_channel_id]

    def clear_history_all(self):
        """Clear entire chat history"""
        super().clear_history_all()
        self.chats.clear()

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

                    # Include daily forecast
                    if "forecast" in data:
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
                        raise Exception(f"Failed to get weather info for {destination} after retries: {e}")

        return weather_info