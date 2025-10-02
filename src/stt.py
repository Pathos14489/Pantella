print("Imported stt.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in stt.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

default = "faster_whisper" # The default LLM to use if the one specified in config.json is not found or if default is specified in config.json
transcriber_Types = {}
# Get all LLMs from src/stt_types/ and add them to LLM_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "stt_types/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned STT: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.stt_types")
        if module_name != "base_stt" and module_name != "base_whisper":
            try:
                module = importlib.import_module(f"src.stt_types.{module_name}")
                transcriber_Types[module.stt_slug] = module
            except Exception as e:
                logging.error(f"Failed to import {module_name}: {e}")
if default in transcriber_Types:
    transcriber_Types["default"] = transcriber_Types[default]
logging.info("Imported Transcriber types in stt.py")
# print available STT types
logging.config(f"Available Transcriber types: {transcriber_Types.keys()}")

# Create LLM object using the config and client provided
    
def create_Transcriber(game_interface):
    """Creates a transcriber object based on the config provided"""
    config = game_interface.config
    config.manager_types["stt"] = transcriber_Types.keys() # Add conversation manager types to config
    slug = game_interface.config.stt_engine
    if type(slug) == str:
        if slug not in transcriber_Types:
            slug = slug.lower()
        if slug not in transcriber_Types:
            logging.error(f"Could not find SpeechToText: {game_interface.config.stt_engine}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find SpeechToText: {game_interface.config.stt_engine}! Please check your config.json file and try again!")
        return transcriber_Types[slug].Transcriber(game_interface)
    else:
        if slug in banned_modules:
            logging.error(f"Banned type for stt_engine in config.json! Please check your config.json file and try again! Banned type: {slug}")
            input("Press enter to continue...")
            raise ValueError(f"Banned type for stt_engine in config.json! Please check your config.json file and try again! Banned type: {slug}")
        else:
            logging.error(f"Wrong type for stt_engine in config.json! Expected string or list of strings, got '{type(slug)}'! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Wrong type for stt_engine in config.json! Expected string or list of strings, got '{type(slug)}'! Please check your config.json file and try again!")