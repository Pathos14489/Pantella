print("Loading character_manager.py...")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in character_manager.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

Manager_Types = {}

# Get all Managers from src/conversation_managers/ and add them to Manager_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "character_managers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned memory manager: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.character_managers")
        module = importlib.import_module(f"src.character_managers.{module_name}")
        Manager_Types[module.manager_slug] = module    
logging.info("Imported all character_managers to Manager_Types, ready to create a character_manager object!")
# print available character_managers
logging.config(f"Available character_managers: {Manager_Types.keys()}")

# Create Manager object using the config provided
    
def create_character_manager(config):
    if config.character_manager_type != "auto": # if a specific manager is specified
        logging.info(f"Creating Character Manager[{config.character_manager_type}]")
        logging.config(f"Creating Character Manager[{config.character_manager_type}] object")
        if config.character_manager_type not in Manager_Types:
            logging.error(f"Could not find manager: {config.character_manager_type}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find manager: {config.character_manager_type}! Please check your config.json file and try again!")
        module = Manager_Types[config.character_manager_type]
        if config.game_id not in module.valid_games:
            logging.error(f"Game '{config.game_id}' not supported by manager '{module.manager_slug}'.")
            input("Press enter to continue...")
            raise ValueError(f"Game '{config.game_id}' not supported by manager '{module.manager_slug}'.")
        manager = module.Character
        return manager
    else: # if no specific character_manager is specified
        logging.config(f"Creating Character Manager[{config.interface_configs[config.game_id]['character_manager']}] (auto) object")
        module = Manager_Types[config.interface_configs[config.game_id]['character_manager']]
        manager = module.Character
        return manager