print("Importing memory_manager.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in memory_manager.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

Manager_Types = {}
# Get all Managers from src/memory_managers/ and add them to Manager_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "memory_managers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned memory manager: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.memory_managers")
        if module_name != "base_memory_manager":
            module = importlib.import_module(f"src.memory_managers.{module_name}")
            Manager_Types[module.manager_slug] = module
logging.info("Imported all memory managers to Manager_Types, ready to create a memory manager object!")
# print available memory managers
logging.config(f"Available memory managers: {Manager_Types.keys()}")

# Create Manager object using the config provided
    
def create_manager(character_manager):
    conversation_manager = character_manager.conversation_manager
    config = conversation_manager.config
    logging.config(f"Creating memory manager for '{config.game_id}' using '{config.memory_manager}'...")
    if config.memory_manager != "auto": # if a specific memory manager is specified
        if config.memory_manager not in Manager_Types:
            logging.error(f"Could not find memory manager: {config.memory_manager}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find memory manager: {config.memory_manager}! Please check your config.json file and try again!")
        logging.config(f"Using memory manager {config.memory_manager}...")
        module = Manager_Types[config.memory_manager]
        manager = module.MemoryManager(character_manager)
        return manager
    else: # if no specific memory manager is specified
        game_config = config.game_configs[config.game_id]
        logging.config(f"Using memory manager {game_config['memory_manager']} recommended by game config...")
        module = Manager_Types[game_config['memory_manager']]
        manager = module.MemoryManager(character_manager)
        return manager