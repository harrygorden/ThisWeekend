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
    # Call the server function to get and save weather data
    weather_data = anvil.server.call('get_weather_openweathermap')
    Notification("Weather data has been retrieved and saved to the database.").show()
