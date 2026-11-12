import json
import os
import discord
from google import genai
from google.genai import types, chats

from src.system_log import LogSystem

class BaseBot:
    def __init__(self, token_env_var=None, bot_name=None, model_name=None, history_file=None, prompt_file=None):
        self.token_env_var = token_env_var
        self.bot_name = bot_name
        self.model_name = model_name
        self.history_file = history_file
        self.prompt_file = prompt_file
        self.chat_history: dict[int, list[dict[str, str]]] = {}
        self.sleep = False

        # Configure intents and initialize the client as an instance attribute
        intents = discord.Intents.default()
        intents.message_content = True
        self.discord_client = discord.Client(intents=intents)
        
        # Load previous chat history
        self.pull_history()

    def push_history(self):
        if not self.history_file:
            LogSystem().write('e',"Bot's history file has not been initialized yet.")
            return
        # Automatically create history file
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w') as file:
            json.dump(self.chat_history,indent=4,fp=file)
    
    def pull_history(self):
        if not self.history_file:
            LogSystem().write('e',"Bot's history file has not been initialized yet.")
            return
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as file:
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

    def __del__(self):
        try:
            self.push_history()
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
    def __init__(self, token_env_var=None, bot_name=None, model_name=None, history_file=None, prompt_file=None):
        super().__init__(
            token_env_var,
            bot_name,
            model_name,
            history_file,
            prompt_file
        )
        self.genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.config = None
        with open(self.prompt_file,'r') as file:
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