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
    try:
        # Get the most recent weather data entry
        recent_weather = app_tables.weatherdata.search(
            tables.order_by("timestamp", ascending=False)
        )
        
        if recent_weather and len(recent_weather) > 0:
            most_recent = recent_weather[0]
            current_time = datetime.now(timezone.utc)
            cache_age = current_time - most_recent['timestamp']
            minutes_old = int(cache_age.total_seconds() / 60)
            
            # Format the creation time in a readable format (convert from UTC to local time)
            creation_time = most_recent['timestamp'].replace(tzinfo=timezone.utc).astimezone()
            creation_time_str = creation_time.strftime("%Y-%m-%d %H:%M:%S %Z")
            
            status_lines = [
                f"Entry creation time: {creation_time_str}",
                f"Entry age: {minutes_old} minutes",
            ]
            
            # If the cache is still valid (less than WeatherDataCacheExpiration minutes old)
            if cache_age < timedelta(minutes=CoreServerModule.WeatherDataCacheExpiration):
                status_lines.append("Expiration not reached, using cached data")
                return "\n".join(status_lines), most_recent['weatherdata_openweathermap']
            else:
                status_lines.append("Expiration reached, requesting updated information")
                return "\n".join(status_lines), None
        
        return "No existing weather data found in cache", None
    except Exception as e:
        error_msg = f"Error checking weather cache: {str(e)}"
        print(f"Server Error in check_weather_cache: {str(e)}")  # Server-side logging
        return error_msg, None

@anvil.server.callable
def update_all_weather():
    """
    Updates weather data from all available weather sources.
    Currently only fetches from OpenWeatherMap, but is designed to be extended
    for additional weather data sources in the future.
    Returns a tuple of (status_message, weather_data)
    """
    try:
        status, data = get_weather_openweathermap()
        if data is None:
            return f"Failed to update weather data: {status}", None
        return f"Updated weather data from all sources:\n{status}", data
    except Exception as e:
        error_msg = f"Error in update_all_weather: {str(e)}"
        print(f"Server Error in update_all_weather: {str(e)}")  # Server-side logging
        return error_msg, None

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
        if response.status_code != 200:
            error_msg = f"OpenWeatherMap API returned status code {response.status_code}"
            print(f"Server Error in get_weather_openweathermap: {error_msg}")  # Server-side logging
            return error_msg, None
            
        weather_data = response.json()  # Parse JSON response
        
        # Add new row to weatherdata table with current timestamp and weather data
        app_tables.weatherdata.add_row(
            timestamp=datetime.now(timezone.utc),
            weatherdata_openweathermap=weather_data
        )
        
        return "Successfully retrieved and stored OpenWeatherMap data", weather_data
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error while fetching OpenWeatherMap data: {str(e)}"
        print(f"Server Error in get_weather_openweathermap: {str(e)}")  # Server-side logging
        return error_msg, None
    except Exception as e:
        error_msg = f"Error fetching OpenWeatherMap data: {str(e)}"
        print(f"Server Error in get_weather_openweathermap: {str(e)}")  # Server-side logging
        return error_msg, None