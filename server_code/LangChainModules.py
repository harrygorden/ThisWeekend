import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.secrets
import anvil.server
from langchain_text_splitters import RecursiveJsonSplitter
from . import CoreServerModule

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

@anvil.server.background_task
def split_json_data(json_data, max_chunk_size=1000, convert_lists=True):
    """
    Background task that splits JSON data into smaller chunks using LangChain's RecursiveJsonSplitter.
    
    Args:
        json_data (dict or str): The JSON data to split. Can be either a dictionary or a JSON string.
        max_chunk_size (int, optional): Maximum size of each chunk in characters. Defaults to 1000.
        convert_lists (bool, optional): Whether to convert lists to dictionaries with index:item pairs. 
                                      This helps manage chunk sizes when lists are present. Defaults to True.
    
    Returns:
        list: A list of JSON chunks as strings, each under max_chunk_size characters
              (when convert_lists=True)
    """
    try:
        anvil.server.task_state['status'] = 'Initializing JSON splitter'
        
        # Initialize the splitter with specified chunk size
        splitter = RecursiveJsonSplitter(max_chunk_size=max_chunk_size)
        
        anvil.server.task_state['status'] = 'Splitting JSON data'
        # Split the JSON data into text chunks
        chunks = splitter.split_text(json_data=json_data, convert_lists=convert_lists)
        
        # Log some information about the chunks
        chunk_sizes = [len(chunk) for chunk in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        max_size = max(chunk_sizes) if chunk_sizes else 0
        
        print(f"[{CoreServerModule.get_current_time_formatted()}] Split JSON data into {len(chunks)} chunks:")
        print(f"[{CoreServerModule.get_current_time_formatted()}] - Average chunk size: {avg_size:.0f} characters")
        print(f"[{CoreServerModule.get_current_time_formatted()}] - Maximum chunk size: {max_size:.0f} characters")
        
        anvil.server.task_state['status'] = f'Completed splitting into {len(chunks)} chunks'
        return chunks
        
    except Exception as e:
        error_msg = f"Error splitting JSON data: {str(e)}"
        print(f"[{CoreServerModule.get_current_time_formatted()}] Error: {error_msg}")
        anvil.server.task_state['status'] = f'Error: {error_msg}'
        raise Exception(error_msg)
