print("src/behavior_manager.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in behavior_manager.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

Manager_Types = {}
# Get all Managers from src/behavior_managers/ and add them to Manager_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "behavior_managers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned behavior manager: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.behavior_managers")
        module = importlib.import_module(f"src.behavior_managers.{module_name}")
        Manager_Types[module.manager_slug] = module    
logging.info("Imported all behavior managers to Manager_Types, ready to create a behavior manager object!")
# print available behavior managers
logging.config(f"Available behavior managers: {Manager_Types.keys()}")

# Create Manager object using the config provided
    
def create_manager(conversation_manager):
    config = conversation_manager.config
    if config.behavior_manager != "auto": # if a specific behavior manager is specified
        if config.behavior_manager not in Manager_Types:
            logging.error(f"Could not find behavior manager: {config.behavior_manager}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find behavior manager: {config.behavior_manager}! Please check your config.json file and try again!")
        module = Manager_Types[config.behavior_manager]
        if config.game_id not in module.valid_games:
            logging.error(f"Game '{config.game_id}' not supported by behavior manager {module.manager_slug}")
            input("Press enter to continue...")
            raise ValueError(f"Game '{config.game_id}' not supported by behavior manager {module.manager_slug}")
        manager = module.BehaviorManager(conversation_manager)
        return manager
    else: # if no specific behavior manager is specified
        interface_config = config.interface_configs[config.game_id]
        module = Manager_Types[interface_config['behavior_manager']]
        manager = module.BehaviorManager(conversation_manager)
        return manager