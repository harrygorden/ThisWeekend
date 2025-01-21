import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.secrets
import anvil.server
import requests
from datetime import datetime, timedelta, timezone
from . import CoreServerModule

#  This module is full of functions used to fetch weather data from external APIs.
#  As of now, it only supports OpenWeatherMap, but it's extensible to other APIs.
#  To add a new weather source:
#  1. Add a new column to the weatherdata table
#  2. Create a new background task function that fetches and formats the data
#  3. Create a callable wrapper function to launch the task
#  4. Add appropriate error handling and progress updates via task_state
#  5. Update update_all_weather() to include the new source
#
#  See get_weather_openweathermap_task() for an example implementation.

def format_weather_data(weather_data):
    """
    Formats the OpenWeatherMap JSON data into a human-readable string
    """
    try:
        current = weather_data.get('current', {})
        daily = weather_data.get('daily', [{}, {}])  # Get today and tomorrow's forecast
        hourly = weather_data.get('hourly', [])  # Get hourly forecast
        today = daily[0]
        tomorrow = daily[1] if len(daily) > 1 else {}
        
        # Convert temperature from Kelvin to Fahrenheit
        def k_to_f(k):
            return round((k - 273.15) * 9/5 + 32, 1)
        
        # Current time from the API data
        current_time = CoreServerModule.timestamp_to_local(current.get('dt', 0))
        
        current_temp = k_to_f(current.get('temp', 0))
        feels_like = k_to_f(current.get('feels_like', 0))
        humidity = current.get('humidity', 0)
        wind_speed = round(current.get('wind_speed', 0) * 2.237, 1)  # Convert m/s to mph
        
        # Get today's high/low and conditions
        today_high = k_to_f(today.get('temp', {}).get('max', 0))
        today_low = k_to_f(today.get('temp', {}).get('min', 0))
        today_weather = today.get('weather', [{}])[0]
        today_description = today_weather.get('description', 'No description available').capitalize()
        
        # Get tomorrow's high/low and conditions
        tomorrow_high = k_to_f(tomorrow.get('temp', {}).get('max', 0))
        tomorrow_low = k_to_f(tomorrow.get('temp', {}).get('min', 0))
        tomorrow_weather = tomorrow.get('weather', [{}])[0]
        tomorrow_description = tomorrow_weather.get('description', 'No description available').capitalize()
        
        # Get current weather description
        current_weather = current.get('weather', [{}])[0]
        current_description = current_weather.get('description', 'No description available').capitalize()
        
        # Format the main weather information
        formatted_weather = [
            f"Weather Report as of {current_time}:",
            "",
            "Current Weather Conditions:",
            f"Temperature: {current_temp}°F (Feels like: {feels_like}°F)",
            f"Conditions: {current_description}",
            f"Humidity: {humidity}%",
            f"Wind Speed: {wind_speed} mph",
            "",
            "Today's Forecast:",
            f"Conditions: {today_description}",
            f"High: {today_high}°F",
            f"Low: {today_low}°F",
            "",
            "Tomorrow's Forecast:",
            f"Conditions: {tomorrow_description}",
            f"High: {tomorrow_high}°F",
            f"Low: {tomorrow_low}°F",
            "",
            "3-Hour Forecast:",
        ]
        
        # Add next 24 hours of forecast in 3-hour intervals
        for i in range(0, 9):  # 8 3-hour intervals = 24 hours
            if i < len(hourly):
                hour_data = hourly[i * 3]  # Get every 3rd hour
                time = CoreServerModule.timestamp_to_local(hour_data.get('dt', 0))
                temp = k_to_f(hour_data.get('temp', 0))
                weather = hour_data.get('weather', [{}])[0]
                description = weather.get('description', 'No description available').capitalize()
                formatted_weather.append(
                    f"{time}: {temp}°F - {description}"
                )
        
        return "\n".join(formatted_weather)
    except Exception as e:
        return f"Error formatting weather data: {str(e)}"

@anvil.server.callable
def check_weather_cache():
    """
    Check if we have recent weather data within the cache expiration window.
    Returns a tuple of (status_message, weather_data, formatted_weather) where weather_data may be None if cache is invalid
    """
    try:
        # Get the most recent weather data entry
        recent_weather = app_tables.weatherdata.search(
            tables.order_by("timestamp", ascending=False)
        )
        
        if recent_weather and len(recent_weather) > 0:
            most_recent = recent_weather[0]
            
            # Delete any older entries
            if len(recent_weather) > 1:
                for old_entry in recent_weather[1:]:
                    old_entry.delete()
            
            current_time = datetime.now(timezone.utc)
            cache_age = current_time - most_recent['timestamp']
            minutes_old = int(cache_age.total_seconds() / 60)
            
            # Convert creation time to Central time
            central = timezone(timedelta(hours=-6))  # Central Standard Time (UTC-6)
            creation_time = most_recent['timestamp'].replace(tzinfo=timezone.utc).astimezone(central)
            creation_time_str = creation_time.strftime("%Y-%m-%d %H:%M:%S CST")
            
            # Calculate expiration time in Central time
            expiration_time = most_recent['timestamp'] + timedelta(minutes=CoreServerModule.WeatherDataCacheExpiration)
            expiration_time_central = expiration_time.replace(tzinfo=timezone.utc).astimezone(central)
            expiration_time_str = expiration_time_central.strftime("%H:%M:%S")
            
            status_lines = [
                f"Entry creation time: {creation_time_str}",
                f"    Entry age: {minutes_old} minutes",
                f"    Once weather data is requested, after {expiration_time_str}, it will be updated from external sources."
            ]
            
            weather_data = most_recent['weatherdata_openweathermap']
            formatted_weather = format_weather_data(weather_data)
            
            # If the cache is still valid (less than WeatherDataCacheExpiration minutes old)
            if cache_age < timedelta(minutes=CoreServerModule.WeatherDataCacheExpiration):
                status_lines.append("    Expiration not reached, using cached data")
                return "\n".join(status_lines), weather_data, formatted_weather
            else:
                status_lines.append("    Expiration reached, requesting updated information")
                return "\n".join(status_lines), None, None
        
        return "No existing weather data found in cache", None, None
    except Exception as e:
        error_msg = f"Error checking weather cache: {str(e)}"
        print(f"Server Error in check_weather_cache: {str(e)}")  # Server-side logging
        return error_msg, None, None

@anvil.server.background_task
def get_weather_openweathermap_task():
    """
    Background task that fetches weather data from OpenWeatherMap API.
    Updates task_state with progress and results
    """
    try:
        anvil.server.task_state['status'] = 'Starting OpenWeatherMap data fetch'
        print(f"[{CoreServerModule.get_current_time_formatted()}] Starting OpenWeatherMap data fetch...")
        url = f"https://api.openweathermap.org/data/3.0/onecall?lat=35.1495&lon=-90.049&appid={anvil.secrets.get_secret('OpenWeatherMap_Key')}"

        payload = {}
        headers = {}

        anvil.server.task_state['status'] = 'Making API request to OpenWeatherMap'
        print(f"[{CoreServerModule.get_current_time_formatted()}] Making API request to OpenWeatherMap...")
        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code != 200:
            error_msg = f"OpenWeatherMap API returned status code {response.status_code}"
            print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {error_msg}")
            anvil.server.task_state['error'] = error_msg
            return
            
        weather_data = response.json()  # Parse JSON response
        
        # Format the data for display
        anvil.server.task_state['status'] = 'Formatting weather data for display'
        print(f"[{CoreServerModule.get_current_time_formatted()}] Formatting weather data for display...")
        formatted_weather = format_weather_data(weather_data)
        
        print(f"[{CoreServerModule.get_current_time_formatted()}] Weather data fetch completed successfully")
        anvil.server.task_state['status'] = 'Complete'
        anvil.server.task_state['weather_data'] = weather_data
        anvil.server.task_state['formatted_weather'] = formatted_weather
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error while fetching OpenWeatherMap data: {str(e)}"
        print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {error_msg}")
        anvil.server.task_state['error'] = error_msg
    except Exception as e:
        error_msg = f"Error fetching OpenWeatherMap data: {str(e)}"
        print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {error_msg}")
        anvil.server.task_state['error'] = error_msg

@anvil.server.callable
def update_all_weather():
    """
    Updates weather data from all available weather sources.
    Currently only fetches from OpenWeatherMap, but is designed to be extended
    for additional weather data sources in the future.
    Returns the background task that will eventually provide the weather data
    """
    try:
        # Get OpenWeatherMap data
        task = get_weather_openweathermap()
        if task is None:
            error_msg = "Failed to launch weather update task"
            print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {error_msg}")
            return None
            
        # Wait for the OpenWeatherMap task to complete
        while not task.is_completed():
            anvil.server.call('sleep', 0.2)
        
        # Check for errors
        state = task.get_state()
        if 'error' in state:
            print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {state['error']}")
            return None
            
        # Get the weather data
        if 'weather_data' not in state:
            print(f"[{CoreServerModule.get_current_time_formatted()}] Error: No weather data received")
            return None
            
        # Create a new row with data from all sources
        print(f"[{CoreServerModule.get_current_time_formatted()}] Storing weather data from all sources...")
        app_tables.weatherdata.add_row(
            timestamp=datetime.now(timezone.utc),
            weatherdata_openweathermap=state['weather_data']
            # Future weather sources would be added here as new columns
        )
        
        # Return the task for the client to get the formatted weather
        return task
            
    except Exception as e:
        error_msg = f"Error updating weather data: {str(e)}"
        print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {error_msg}")
        return None

@anvil.server.callable
def get_weather_openweathermap():
    """
    Launches a background task to fetch weather data from OpenWeatherMap API.
    Returns the background task object that will eventually return a tuple of (status_message, weather_data, formatted_weather)
    """
    try:
        # Launch the background task and return it immediately
        return anvil.server.launch_background_task('get_weather_openweathermap_task')
    except Exception as e:
        error_msg = f"Error launching weather update task: {str(e)}"
        print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {error_msg}")
        return None