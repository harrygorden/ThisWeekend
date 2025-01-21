import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.secrets
import anvil.server
import requests
from datetime import datetime, timedelta, timezone
from . import CoreServerModule

@anvil.server.callable
def check_weather_cache():
    """
    Check if we have recent weather data within the cache expiration window.
    Returns a tuple of (status_message, weather_data) where weather_data may be None if cache is invalid
    """
    # Get the most recent weather data entry
    recent_weather = app_tables.weatherdata.search(
        tables.order_by("timestamp", ascending=False)
    )
    
    if recent_weather and len(recent_weather) > 0:
        most_recent = recent_weather[0]
        current_time = datetime.now(timezone.utc)
        cache_age = current_time - most_recent['timestamp']
        
        # If the cache is still valid (less than WeatherDataCacheExpiration minutes old)
        if cache_age < timedelta(minutes=CoreServerModule.WeatherDataCacheExpiration):
            minutes_old = int(cache_age.total_seconds() / 60)
            return f"Found valid cached weather data ({minutes_old} minutes old)", most_recent['weatherdata_openweathermap']
    
    return "No valid cached weather data found", None

@anvil.server.callable
def update_all_weather():
    """
    Updates weather data from all available weather sources.
    Currently only fetches from OpenWeatherMap, but is designed to be extended
    for additional weather data sources in the future.
    Returns a tuple of (status_message, weather_data)
    """
    status, data = get_weather_openweathermap()
    return f"Updated weather data from all sources:\n{status}", data

@anvil.server.callable
def get_weather_openweathermap():
    """
    Fetches weather data from OpenWeatherMap API and stores it in the database.
    Returns a tuple of (status_message, weather_data)
    """
    try:
        url = f"https://api.openweathermap.org/data/3.0/onecall?lat=35.1495&lon=-90.049&appid={anvil.secrets.get_secret('OpenWeatherMap_Key')}"

        payload = {}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)
        weather_data = response.json()  # Parse JSON response
        
        # Add new row to weatherdata table with current timestamp and weather data
        app_tables.weatherdata.add_row(
            timestamp=datetime.now(timezone.utc),
            weatherdata_openweathermap=weather_data
        )
        
        return "Successfully retrieved and stored OpenWeatherMap data", weather_data
    except Exception as e:
        error_msg = f"Error fetching OpenWeatherMap data: {str(e)}"
        return error_msg, None