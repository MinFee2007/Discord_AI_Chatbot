import datetime

class TimeSystem:
    time = "N/A"
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance
    
    def get_time(self):
        TimeSystem.time = str(datetime.datetime.now())
        return TimeSystem.time