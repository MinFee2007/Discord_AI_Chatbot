from pydantic import BaseModel, Field

class WeatherRequest(BaseModel):
    destinations: list[str] = Field(description="List of destinations which the user asked how the weather was in. only real locations may be entered. If the user was not asking for weather information but only talking about the topic of weather, just leave an empty list. Maximum is 3 destinations")
    forecast_days: list[int] = Field(description="The number of days in advance for which the user wants to know the weather forecast in each destination; enter 0 if they are only asking about the current weather. Maximum is 3 days")