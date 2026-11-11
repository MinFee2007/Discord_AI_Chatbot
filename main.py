from dotenv import load_dotenv

from src.manager import Manager
from src.bot_alice_google import Alice

if __name__=="__main__":
    load_dotenv()
    manager = Manager()
    manager.add_bot("Alice",Alice())
    manager.run()
    