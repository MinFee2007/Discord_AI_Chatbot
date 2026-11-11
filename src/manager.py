from src.bot_base import BaseBot
from src.system_log import LogSystem

class Manager:
    def __init__(self):
        self.bots:dict[str,BaseBot] = {}

    def add_bot(self,bot_name:str,bot_instance:BaseBot):
        self.bots[bot_name] = bot_instance

    def remove_bot(self,bot_name:str):
        if self.bots.get(bot_name) != None:
            self.bots.pop(bot_name)

    def run(self):
        LogSystem().clear()

        for bot_name, bot_instance in self.bots.items():
            LogSystem().write('n',f"Bot {bot_name} is starting")
            bot_instance.run()