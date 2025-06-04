print("Loading game_interface.py...")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in game_interface.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

Interface_Types = {}

# Get all Interfaces from src/conversation_managers/ and add them to Interface_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "game_interfaces/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned memory manager: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.game_interfaces")
        if module_name != "base_interface" and module_name.strip() != "":
            module = importlib.import_module(f"src.game_interfaces.{module_name}")
            Interface_Types[module.interface_slug] = module
logging.info("Imported all game interfaces to Interface_Types, ready to create a game interface object!")
# print available game interfaces
logging.config(f"Available game interfaces: {Interface_Types.keys()}")

# Create Interface object using the config provided
    
def create_game_interface(conversation_manager):
    """Creates a game interface object based on the config provided"""
    config = conversation_manager.config
    config.manager_types["game_interface"] = Interface_Types.keys() # Add conversation manager types to config
    if config.interface_type != "auto": # if a specific interface is specified
        if config.interface_type not in Interface_Types:
            logging.error(f"Could not find interface: {config.interface_type}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find interface: {config.interface_type}! Please check your config.json file and try again!")
        module = Interface_Types[config.interface_type]
        if config.game_id not in module.valid_games:
            logging.error(f"Game '{config.game_id}' not supported by interface '{module.interface_slug}'.")
            input("Press enter to continue...")
            raise ValueError(f"Game '{config.game_id}' not supported by interface '{module.interface_slug}'.")
        manager = module.GameInterface(conversation_manager)
        return manager
    else: # if no specific game interface is specified
        interface_config = config.interface_configs[config.game_id]
        module = Interface_Types[interface_config['interface_type']]
        manager = module.GameInterface(conversation_manager)
        return manager