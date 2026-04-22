print("Importing character_generator.py")
from src.logging import logging
import src.tokenizer as tokenizers
import os
import importlib
import json
logging.info("Imported required libraries in character_generator.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

Generator_Types = {}
# Get all character generator types from src/character_generators/ and add them to Generator_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "character_generators/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned character_type: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.character_generators")
        module = importlib.import_module(f"src.character_generators.{module_name}")
        Generator_Types[module.generator_name] = module

addons_path = os.path.join(os.path.dirname(__file__), "../", "addons/")
for addon_dir in os.listdir(addons_path):
    addon_path = os.path.join(addons_path, addon_dir)
    metadata_path = os.path.join(addon_path, "metadata.json")
    if os.path.isdir(addon_path) and os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            if metadata.get("enabled", False) == False:
                continue
    else:
        continue
    if os.path.isdir(addon_path) and os.path.exists(os.path.join(addon_path, "character_generators/")):
        for file in os.listdir(os.path.join(addon_path, "character_generators/")):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                if module_name in banned_modules:
                    logging.warning(f"Skipping banned character generator: {module_name}")
                    continue
                logging.info(f"Importing {module_name} from addons.{addon_dir}.character_generators")
                module = importlib.import_module(f"addons.{addon_dir}.character_generators.{module_name}")
                Generator_Types[module.generator_name] = module
logging.info("Imported all Generators to Generator_Types!")

def create_generator_schema(conversation_manager):
    """Creates a character generator object based on the config provided"""
    config = conversation_manager.config
    config.manager_types["character_generator"] = Generator_Types.keys() # Add conversation manager types to config
    logging.info(f"Creating Generator[{conversation_manager.config.character_type}] object")
    generator = "auto"
    if conversation_manager.config.character_type not in Generator_Types and conversation_manager.config.character_type != "auto":
        logging.error(f"Could not find character type: {conversation_manager.config.character_type}! Please check your config.json file and try again!")
        generator = "none"
    generator = conversation_manager.config.character_type
    if generator == "auto":
        generator = conversation_manager.config.interface_configs[conversation_manager.config.game_id]['character_type']
    if generator == "none":
        return None
    return Generator_Types[generator].Character