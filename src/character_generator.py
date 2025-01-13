print("Importing character_generator.py")
from src.logging import logging
import src.tokenizer as tokenizers
import os
import importlib
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
logging.info("Imported all Generators to Generator_Types!")

def create_generator_schema(conversation_manager):
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