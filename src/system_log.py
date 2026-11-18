import datetime

class LogSystem:
    log_file_path = "bot.log"
    msg_types = {
        'e': 'Error',
        'w': 'Warning',
        'n': 'Notification',
        'm': 'Message'
    }
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance
    
    def clear(self):
        open(LogSystem.log_file_path, 'w').close()

    def write(self, type:str, content:str):
        with open(LogSystem.log_file_path,"a") as log:
            msgtype = "Unknown message type"
            time = str(datetime.datetime.now())
            if type in LogSystem.msg_types:
                msgtype = LogSystem.msg_types[type]
            log.write(f"{time} - {msgtype}: {content}\n")