print("Importing conversation_manager.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in conversation_manager.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

Manager_Types = {}
# Get all Managers from src/conversation_managers/ and add them to Manager_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "conversation_managers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        logging.info(f"Importing {module_name} from src.conversation_managers")
        if module_name in banned_modules:
            logging.warning(f"Skipping banned conversation manager: {module_name}")
            continue
        if module_name != "base_conversation_manager":
            module = importlib.import_module(f"src.conversation_managers.{module_name}")
            Manager_Types[module.manager_slug] = module    
logging.info("Imported all conversation managers to Manager_Types, ready to create a conversation manager object!")
# print available conversation managers
logging.info(f"Available conversation managers: {Manager_Types.keys()}")

# Create Manager object using the config provided
    
def create_manager(config, initialize=True):
    if config.conversation_manager_type != "auto": # if a specific conversation manager is specified
        if config.conversation_manager_type not in Manager_Types:
            logging.error(f"Could not find conversation manager: {config.conversation_manager_type}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find conversation manager: {config.conversation_manager_type}! Please check your config.json file and try again!")
        module = Manager_Types[config.conversation_manager_type]
        if config.game_id not in module.valid_games:
            logging.error(f"Game '{config.game_id}' not supported by conversation manager {module.manager_slug}")
            input("Press enter to continue...")
            raise ValueError(f"Game '{config.game_id}' not supported by conversation manager {module.manager_slug}")
        manager = module.ConversationManager(config, initialize)
        return manager
    else: # if no specific conversation manager is specified
        game_config = config.game_configs[config.game_id]
        module = Manager_Types[game_config['conversation_manager']]
        manager = module.ConversationManager(config, initialize)
        return manager