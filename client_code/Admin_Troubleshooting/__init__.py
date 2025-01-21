from ._anvil_designer import Admin_TroubleshootingTemplate
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server


class Admin_Troubleshooting(Admin_TroubleshootingTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.

  def button_weather_retrieval_click(self, **event_args):
    """This method is called when the button is clicked"""
    # First check the cache
    cached_data = anvil.server.call('check_weather_cache')
    if cached_data is None:
      # If no valid cached data, update weather from all sources
      weather_data = anvil.server.call('update_all_weather')
      Notification("Weather data has been retrieved and saved to the database.").show()
    else:
      Notification("Using cached weather data.").show()
