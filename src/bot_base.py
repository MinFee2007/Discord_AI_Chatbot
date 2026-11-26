import json
import datetime
import os
import discord
import asyncio
import requests
import chess
import re
import random
from google import genai
from google.genai import types, chats, errors

from src.system_log import LogSystem
from src.output_weather import WeatherRequest
from src.output_chess import ChessGameSetup, ChessResponse
from src.manager_chess import ChessManager

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
        self.active_chess_game:dict[int,dict] = {} # {channel_id:{"manager":ChessManager(), "player_id": int, "bot_color":chess.BLACK|chess.WHITE}}

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

    def handle_user_message(self,message:discord.Message) -> str:
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

    def parse_chess_turn_message(self, raw_content: str, bot_id: int) -> tuple[str | None, str]:
        """
        Extract (move_str, user_comment) from user message:
        move: <UCI/SAN move>
        <user_comment>
        """
        # Delete bot tag
        cleaned = (
            raw_content
            .replace(f"<@{bot_id}>", "")
            .replace(f"<@!{bot_id}>", "")
            .strip()
        )
        # Extract
        pattern = r"^move\s*:\s*([^\r\n]+)(?:\r?\n(.*))?$"
        match = re.match(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)

        if not match:
            return None, cleaned  # Wrong syntax "move: ..."

        move_str = match.group(1).strip()
        user_comment = match.group(2).strip() if match.group(2) else ""
        return move_str, user_comment

    async def check_chess_over(self, message:discord.Message, bot_turn:bool) -> bool:
        """Check if the chess game is over, and handle it (return True on game over, False on vice versa)"""
        manager: ChessManager = self.active_chess_game[message.channel.id]["manager"]
        bot_color: chess.Color = self.active_chess_game[message.channel.id]["bot_color"]
        outcome: chess.Outcome = manager.get_outcome()
        if outcome:
            if outcome.winner is None:
                # Draw
                LogSystem().write('n',f"The result of the chess game between {message.author.id} and {self.bot_name} in channel {message.channel.id} is a draw")
                reply = await self.get_response("System Notification: This game of chess is a draw. Say something to your opponent.", message.channel.id)
                await self.send_reply(message, reply)
                del self.active_chess_game[message.channel.id]
                return True
            elif outcome.winner == bot_color:
                # Winner is bot
                LogSystem().write('n',f"The winner of the chess game between {message.author.id} and {self.bot_name} in channel {message.channel.id} is {self.bot_name}")
                reply = await self.get_response("System Notification: You won the chess game. Say something to your opponent.", message.channel.id)
                await self.send_reply(message, reply)
                del self.active_chess_game[message.channel.id]
                return True
            else:
                # Winner is user
                LogSystem().write('n',f"The winner of the chess game between {message.author.id} and {self.bot_name} in channel {message.channel.id} is {message.author.id}")
                reply = await self.get_response("System Notification: You lost the chess game. Say something to your opponent.", message.channel.id)
                await self.send_reply(message, reply)
                del self.active_chess_game[message.channel.id]
                return True
        else:
            # The game is still in progress
            return False

    async def generate_chess_move(self, channel_id:int, user_id:int, user_nickname:str, first_move:bool, user_move:str, user_comment:str|None) -> ChessResponse:
        """Generate the bot move"""
        # Ensure chat session is existed
        self.ensure_chat_session(channel_id)
        # Get chess manager of the channel
        chess_manager: ChessManager = self.active_chess_game[channel_id]["manager"]
        # Bot side
        bot_color = "white" if self.active_chess_game[channel_id]["bot_color"] == chess.WHITE else "black"
        # Handled user comment
        comment_part = f"and said: {user_comment}" if user_comment else "without saying anything."
        # Getting best moves recommended for bot
        best_moves = await asyncio.to_thread(
            chess_manager.get_best_move,
            time_limit_ns=500_000_000,
            top_k=3
        )
        # Format into the best moves list
        formatted_best_moves = []
        for move, score in best_moves:
            formatted_best_moves.append(f"(move: {move.uci()}, score: {score})")

        # Build prompt
        if first_move:
            prompt = "At " + str(datetime.datetime.now()) + f", user with ID {user_id} and nickname {user_nickname} invited you to play a chess game {comment_part}"
        else:
            prompt = "At " + str(datetime.datetime.now()) + f", user with ID {user_id} and nickname {user_nickname} made a move ({user_move}) {comment_part}"
        prompt += (f"\nSystem Instruction:\nHere's the state of the board based on Forsyth-Edwards Notation (FEN) format: {chess_manager.board_to_fen(None)}\n"
                    f"Make your move as " + bot_color + "\n"
                    f"Recommended best move(s):\n" + "".join(move_str + "\n" for move_str in formatted_best_moves))
        # Config
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ChessResponse
        )
        return await self.get_response(prompt, channel_id, config)

    async def play_bot_turn(self, message:discord.Message, first_move:bool, user_move:str, user_comment:str|None):
        chess_manager:ChessManager = self.active_chess_game[message.channel.id]["manager"]
        bot_response:ChessResponse = await self.generate_chess_move(message.channel.id, message.author.id, message.author.display_name, first_move, user_move, user_comment)
        bot_comment = bot_response.comment if bot_response.comment else "Your turn"
        bot_color = self.active_chess_game[message.channel.id]["bot_color"]
        try:
            # Bot makes the move
            bot_move = chess_manager.make_move(bot_response.move)
        except ValueError:
            # Bot made an illegal move, rerun the move finding algorithm and get the best move
            fallback_moves = await asyncio.to_thread(
                chess_manager.get_best_move,
                time_limit_ns=100_000_000,
                top_k=1
            )
            bot_move:chess.Move = fallback_moves[0][0]
            chess_manager.board.push(bot_move)

        # Create the board image for the player
        board_img_bytestream = await asyncio.to_thread(
            chess_manager.render_board_image,
            last_move=bot_move,
            flipped=True if bot_color==chess.WHITE else False
        )
        board_img = discord.File(fp=board_img_bytestream, filename="board.png")

        # Reply
        await message.reply(bot_comment, file=board_img)

    async def start_chess(self, message:discord.Message):
        """Start a chess game with a player"""
        LogSystem().write('n',f"User {message.author.name} started a chess game with {self.bot_name}")
        
        # Build the starting setup
        game_setup:ChessGameSetup = await self.build_initial_chess_setup(message=message)
        # First side to get first move
        first_color = game_setup.board_setup.split(" ")[1]
        # Give the first turn to a random side if it has not been given yet
        if game_setup.first_turn == None:
            game_setup.first_turn = random.choice([True, False])
        # Get bot color based on first side to get first turn
        if first_color == "w":
            bot_color = chess.WHITE if game_setup.first_turn else chess.BLACK
        elif first_color == "b":
            bot_color = chess.BLACK if game_setup.first_turn else chess.WHITE
        else:
            raise Exception("Unable to identify the bot's side")

        # Initialize the chess game
        self.active_chess_game[message.channel.id] = {
            "manager": ChessManager(),
            "player_id": message.author.id,
            "bot_color": bot_color
        }
        # Process user message
        user_comment = self.handle_user_message(message)

        # Set up the board
        chess_manager: ChessManager = self.active_chess_game[message.channel.id]["manager"]
        try:
            chess_manager.fen_to_board(None, game_setup.board_setup)
        except ValueError:
            del self.active_chess_game[message.channel.id]
            raise Exception(f"User {message.author.id} was unable to set up initial chess board in channel {message.channel.id} with FEN format: {game_setup.board_setup}")
        
        async with message.channel.typing():
            if game_setup.first_turn:
                # Bot gets the first turn, move and show chess board, wait for user's reply
                await self.play_bot_turn(message, True, None, user_comment)
                if await self.check_chess_over(message, True):
                    return
            else:
                # User gets the first turn, show chess board, wait for user's reply
                self.ensure_chat_session(message.channel.id)
                comment_part = self.handle_user_message(message)
                prompt = "At " + str(datetime.datetime.now()) + f", user with ID {message.author.id} and nickname {message.author.display_name} invited you to play a chess game and said: {comment_part}"
                bot_response = await self.get_response(prompt, message.channel.id)
                board_img_bytestream = await asyncio.to_thread(
                    chess_manager.render_board_image,
                    None,
                    True if bot_color==chess.WHITE else False
                )
                board_img = discord.File(fp=board_img_bytestream, filename="board.png")
                await message.reply(bot_response, file=board_img)

    async def play_chess_turn(self, message:discord.Message):
        """Handle user's chess turn"""
        # Extract move and comment from the message
        move_str, user_comment = self.parse_chess_turn_message(message.content, self.discord_client.user.id)
        
        if not move_str:
            await message.reply("I don't think that is a legal move. Can you try again?")
            return
        
        chess_manager:ChessManager = self.active_chess_game[message.channel.id]["manager"]
        try:
            # Make the move
            chess_manager.make_move(move_str)
        except ValueError:
            await message.reply("I don't think that is a legal move. Can you try again?")
            return

        if await self.check_chess_over(message, False):
            return
        async with message.channel.typing():
            await self.play_bot_turn(message, False, move_str, user_comment)
            if await self.check_chess_over(message, True):
                return

    async def chess_surrender(self, message:discord.Message):
        """Handle user's surrender in chess"""
        self.ensure_chat_session(message.channel.id)
        del self.active_chess_game[message.channel.id]
        reply = await self.get_response("System Notification: Your opponent surrendered the chess game. Say something to them.", message.channel.id)
        await self.send_reply(message, reply)

    async def show_board(self, message:discord.Message):
        """Reveal the board without making a move"""
        chess_manager: ChessManager = self.active_chess_game[message.channel.id]["manager"]
        bot_color = self.active_chess_game[message.channel.id]["bot_color"]
        bot_move: chess.Move = chess_manager.get_last_move()
        board_img_bytestream = await asyncio.to_thread(
            chess_manager.render_board_image,
            last_move=bot_move,
            flipped=True if bot_color==chess.WHITE else False
        )
        board_img = discord.File(fp=board_img_bytestream, filename="board.png")
        await message.reply(file=board_img)

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
            response_schema=WeatherRequest
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

    async def build_initial_chess_setup(self, message:discord.Message):
        """Build the starting setup of a chess game based on user's message"""
        prompt = str(f"{message.content}\n\n"
                     f"Analyze this text and determine the starting setup for the chess game.")
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ChessGameSetup
        )
        attempt = 0
        max_retries = 3
        retry_delay = 2

        while attempt <= max_retries:
            try:
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                return response.parsed
            except errors.APIError as e:
                if e.code not in (503, 429):
                    raise Exception(f"Unable to extract board setup: {e}")
                if attempt < max_retries:
                    LogSystem().write('w', f"Model is having issue extracting board setup: {e}\nRetrying (attempt {attempt+1}/{max_retries}) in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    attempt += 1
                    retry_delay *= 2
                else:
                    raise Exception(f"Timeout while extracting board setup: {e}")