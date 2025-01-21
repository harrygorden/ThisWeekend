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
      except Exception as e:
        self.log_message(f"Error checking cache: {str(e)}")
        return
      
      if cached_data is None:
        # If no valid cached data, update weather from all sources
        self.log_message("Fetching fresh weather data...")
        try:
          # Launch the background task
          task = anvil.server.call('update_all_weather')
          if task is None:
            self.log_message("Failed to launch weather update task")
            return
            
          # Monitor the task's progress
          while not task.is_completed():
            state = task.get_state()
            if 'status' in state:
              self.log_message(f"Status: {state['status']}")
            anvil.server.call('sleep', 0.2)  # Wait 200ms before checking again
            
          # Check for errors
          if 'error' in task.get_state():
            self.log_message(f"Error: {task.get_state()['error']}")
            return
            
          # Get the results
          state = task.get_state()
          if 'formatted_weather' in state:
            formatted_weather = state['formatted_weather']
            self.log_message("Weather data successfully updated")
          else:
            self.log_message("No weather data received from task")
            return
            
        except Exception as e:
          self.log_message(f"Error fetching fresh data: {str(e)}")
          return
      else:
        self.log_message("Using cached weather data.")
      
      # Display the formatted weather data
      if formatted_weather:
        self.rich_text_weather_retrieval_output.content = formatted_weather
      else:
        self.log_message("No weather data available to display")
      
    except Exception as e:
      self.log_message(f"Error retrieving weather data: {str(e)}")

  def button_weather_analysis_click(self, **event_args):
    """This method is called when the button is clicked"""
    # Clear the logs
    self.rich_text_weather_analysis_logging.content = ""
    self.rich_text_weather_analysis_output.content = ""
    
    try:
      # First check the weather cache
      self.log_message("Checking weather cache...")
      try:
        status, weather_data, _ = anvil.server.call('check_weather_cache')
        self.log_message(status)
      except Exception as e:
        self.log_message(f"Error checking weather cache: {str(e)}")
        return
      
      # If weather data is expired or missing, update it
      if weather_data is None:
        self.log_message("Fetching fresh weather data...")
        try:
          task = anvil.server.call('update_all_weather')
          if task is None:
            self.log_message("Failed to launch weather update task")
            return
            
          # Wait for the task to complete
          while not task.is_completed():
            anvil.server.call('sleep', 0.2)
            
          # Get the task results
          state = task.get_state()
          if 'error' in state:
            self.log_message(f"Error updating weather: {state['error']}")
            return
            
          weather_data = state.get('weather_data')
          if not weather_data:
            self.log_message("No weather data received from update task")
            return
            
        except Exception as e:
          self.log_message(f"Error updating weather: {str(e)}")
          return
      
      # Now check the analysis cache
      self.log_message("Checking analysis cache...")
      try:
        status, analysis = anvil.server.call('check_weather_analysis_cache')
        self.log_message(status)
      except Exception as e:
        self.log_message(f"Error checking analysis cache: {str(e)}")
        return
      
      # If analysis is expired or missing, generate new analysis
      if analysis is None:
        self.log_message("Generating new weather analysis...")
        try:
          analysis = anvil.server.call('generate_weather_analysis', weather_data)
          if not analysis:
            self.log_message("Failed to generate weather analysis")
            return
        except Exception as e:
          self.log_message(f"Error generating analysis: {str(e)}")
          return
      
      # Display the analysis
      self.rich_text_weather_analysis_output.content = analysis
      
    except Exception as e:
      self.log_message(f"Unexpected error: {str(e)}")

  def log_message(self, message):
    """Helper function to add a message to the rich text box"""
    current_time = datetime.now().strftime("%H:%M:%S")
    if self.rich_text_weather_retrieval_logging.content:
      self.rich_text_weather_retrieval_logging.content += f"\n[{current_time}] {message}"
    else:
      self.rich_text_weather_retrieval_logging.content = f"[{current_time}] {message}"
