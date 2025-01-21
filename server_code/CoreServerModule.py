import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.secrets
import anvil.server
from datetime import datetime, timedelta, timezone

# Constants
WeatherDataCacheExpiration = 60  # Weather data cache expiration time in minutes

# This is a server module. It runs on the Anvil server,
# rather than in the user's browser.
#
# To allow anvil.server.call() to call functions here, we mark
# them with @anvil.server.callable.
# Here is an example - you can replace it with your own:
#
# @anvil.server.callable
# def say_hello(name):
#   print("Hello, " + name + "!")
#   return 42
#

def timestamp_to_local(ts):
    """
    Convert Unix timestamp to Central time string
    Args:
        ts: Unix timestamp in seconds
    Returns:
        String formatted as HH:MM AM/PM in Central time
    """
    utc_time = datetime.fromtimestamp(ts, timezone.utc)
    central = timezone(timedelta(hours=-6))  # Central Standard Time (UTC-6)
    local_time = utc_time.astimezone(central)
    return local_time.strftime("%I:%M %p")

def get_current_time_formatted():
    """
    Get current time formatted in 24-hour Central time
    Returns:
        String formatted as HH:MM:SS
    """
    utc_time = datetime.now(timezone.utc)
    central = timezone(timedelta(hours=-6))  # Central Standard Time (UTC-6)
    local_time = utc_time.astimezone(central)
    return local_time.strftime("%H:%M:%S")
