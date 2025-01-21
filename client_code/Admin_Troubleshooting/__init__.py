from ._anvil_designer import Admin_TroubleshootingTemplate
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime

class Admin_Troubleshooting(Admin_TroubleshootingTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.

  def button_weather_retrieval_click(self, **event_args):
    """This method is called when the button is clicked"""
    # Clear the log
    self.rich_text_weather_retrieval_logging.content = ""
    
    try:
      # First check the cache
      self.log_message("Checking weather cache...")
      status, cached_data = anvil.server.call('check_weather_cache')
      self.log_message(status)
      
      if cached_data is None:
        # If no valid cached data, update weather from all sources
        self.log_message("Fetching fresh weather data...")
        status, weather_data = anvil.server.call('update_all_weather')
        self.log_message(status)
        Notification("Weather data has been retrieved and saved to the database.").show()
      else:
        Notification("Using cached weather data.").show()
    except Exception as e:
      error_msg = f"Error during weather retrieval: {str(e)}"
      self.log_message(error_msg)
      Notification(error_msg, style="danger").show()

  def log_message(self, message):
    """Helper function to add a message to the rich text box"""
    current_time = datetime.now().strftime("%H:%M:%S")
    if self.rich_text_weather_retrieval_logging.content:
      self.rich_text_weather_retrieval_logging.content += f"\n[{current_time}] {message}"
    else:
      self.rich_text_weather_retrieval_logging.content = f"[{current_time}] {message}"
