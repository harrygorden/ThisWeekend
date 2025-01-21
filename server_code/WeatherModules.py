import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.secrets
import anvil.server
import requests
from datetime import datetime, timedelta
from . import CoreServerModule

def check_weather_cache():
    """
    Check if we have recent weather data within the cache expiration window.
    Returns the most recent weather data if valid, None if we need to fetch new data.
    """
    # Get the most recent weather data entry
    recent_weather = app_tables.weatherdata.search(
        tables.order_by("timestamp", ascending=False)
    )
    
    if recent_weather and len(recent_weather) > 0:
        most_recent = recent_weather[0]
        cache_age = datetime.now() - most_recent['timestamp']
        
        # If the cache is still valid (less than WeatherDataCacheExpiration minutes old)
        if cache_age < timedelta(minutes=CoreServerModule.WeatherDataCacheExpiration):
            return most_recent['weatherdata_openweathermap']
    
    return None

@anvil.server.callable
def get_weather_openweathermap():
    cached_weather = check_weather_cache()
    if cached_weather is not None:
        return cached_weather
    
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat=35.1495&lon=-90.049&appid={anvil.secrets.get_secret('OpenWeatherMap_Key')}"

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    weather_data = response.json()  # Parse JSON response
    
    # Add new row to weatherdata table with current timestamp and weather data
    app_tables.weatherdata.add_row(
        timestamp=datetime.now(),
        weatherdata_openweathermap=weather_data
    )
    
    return weather_data