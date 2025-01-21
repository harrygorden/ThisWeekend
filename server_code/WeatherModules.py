import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.secrets
import anvil.server
import requests

#  This module runs on an Anvil server in the server environment.
#  It is not run in the user's browser.  All functions defined in this
#  module should be callable with @anvil.server.callable.

@anvil.server.callable
def get_weather_openweathermap():
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat=35.1495&lon=-90.049&appid={anvil.secrets.get_secret('OpenWeatherMap_Key')}"

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    weather_data = response.json()  # Parse JSON response
    
    # Add new row to weatherdata table with current timestamp and weather data
    app_tables.weatherdata.add_row(
        timestamp=tables.now(),
        weatherdata_openweathermap=weather_data
    )
    
    return weather_data