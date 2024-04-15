print("Importing chat_manager.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in chat_manager.py")

Manager_Types = {}

# Get all Managers from src/chat_managers/ and add them to Manager_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "chat_managers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name != "base_chat_manager":
            module = importlib.import_module(f"src.chat_managers.{module_name}")
            Manager_Types[module.chat_manager_slug] = module    
logging.info("Imported all chat managers to Manager_Types, ready to create a chat manager object!")

# Create Manager object using the config provided
    
def create_manager(conversation_manager):
    config = conversation_manager.config
    if config.chat_manager != "auto": # if a specific chat manager is specified
        if config.chat_manager not in Manager_Types:
            logging.error(f"Could not find chat manager: {config.chat_manager}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find chat manager: {config.chat_manager}! Please check your config.json file and try again!")
        module = Manager_Types[config.chat_manager]
        if config.game_id not in module.valid_games:
            logging.error(f"Game '{config.game_id}' not supported by chat manager {module.chat_manager_slug}")
            input("Press enter to continue...")
            raise ValueError(f"Game '{config.game_id}' not supported by chat manager {module.chat_manager_slug}")
        manager = module.ChatManager(conversation_manager)
        return manager
    else: # if no specific chat manager is specified
        game_config = config.game_configs[config.game_id]
        module = Manager_Types[game_config['chat_manager']]
        manager = module.ChatManager(conversation_manager)
        return manager