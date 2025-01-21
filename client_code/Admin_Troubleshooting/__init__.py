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
    # Clear the logs
    self.rich_text_weather_retrieval_logging.content = ""
    self.rich_text_weather_retrieval_output.content = ""
    
    try:
      # First check the cache
      self.log_message("Checking weather cache...")
      try:
        status, cached_data, formatted_weather = anvil.server.call('check_weather_cache')
        self.log_message(status)
      except anvil.server.NoServerFunctionError:
        self.log_message("Error: Server function 'check_weather_cache' not found. Please ensure the server code is up to date.")
        return
      except anvil.server.ConnectionError:
        self.log_message("Error: Could not connect to the server. Please check your internet connection.")
        return
      except Exception as e:
        self.log_message(f"Error checking cache: {str(e)}")
        return
      
      if cached_data is None:
        # If no valid cached data, update weather from all sources
        self.log_message("Fetching fresh weather data...")
        try:
          status, weather_data, formatted_weather = anvil.server.call('update_all_weather')
          self.log_message(status)
          if weather_data is None:
            self.log_message("Failed to retrieve weather data. Check the log for details.")
            return
        except anvil.server.ConnectionError:
          self.log_message("Error: Could not connect to the server while fetching fresh data.")
          return
        except Exception as e:
          self.log_message(f"Error fetching fresh data: {str(e)}")
          return
      else:
        self.log_message("Using cached weather data.")
      
      # Display the formatted weather data
      self.rich_text_weather_retrieval_output.content = formatted_weather
      
    except Exception as e:
      self.log_message(f"Error retrieving weather data: {str(e)}")

  def log_message(self, message):
    """Helper function to add a message to the rich text box"""
    current_time = datetime.now().strftime("%H:%M:%S")
    if self.rich_text_weather_retrieval_logging.content:
      self.rich_text_weather_retrieval_logging.content += f"\n[{current_time}] {message}"
    else:
      self.rich_text_weather_retrieval_logging.content = f"[{current_time}] {message}"
