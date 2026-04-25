print("Imported stt.py")
from src.logging import logging
import os
import importlib
import json
import traceback
logging.info("Imported required libraries in stt.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

default = "faster_whisper" # The default speech_input_processor to use if the one specified in config.json is not found or if default is specified in config.json
speech_input_processor_Types = {}
# Get all speech_input_processors from src/speech_input_processor_types/ and add them to speech_input_processor_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "speech_input_processor_types/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned STT: {module_name}")
            continue
        if module_name != "base_stt" and module_name != "base_whisper":
            logging.info(f"Importing {module_name} from src.speech_input_processor_types")
            try:
                module = importlib.import_module(f"src.speech_input_processor_types.{module_name}")
                speech_input_processor_Types[module.speech_input_processor_slug] = module
            except Exception as e:
                logging.error(f"Failed to import {module_name} from src.speech_input_processor_types: {e}")
                logging.error(traceback.format_exc())

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
    if os.path.isdir(addon_path) and os.path.exists(os.path.join(addon_path, "speech_input_processor_types/")):
        for file in os.listdir(os.path.join(addon_path, "speech_input_processor_types/")):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                if module_name in banned_modules:
                    logging.warning(f"Skipping banned speech input processor: {module_name}")
                    continue
                logging.info(f"Importing {module_name} from addons.{addon_dir}.speech_input_processor_types")
                try:
                    module = importlib.import_module(f"addons.{addon_dir}.speech_input_processor_types.{module_name}")
                    speech_input_processor_Types[module.speech_input_processor_slug] = module
                    logging.info(f"Imported {module_name} from addons.{addon_dir}.speech_input_processor_types")
                except Exception as e:
                    logging.error(f"Failed to import {module_name} from addons.{addon_dir}.speech_input_processor_types: {e}")
                    logging.error(traceback.format_exc())
if default in speech_input_processor_Types:
    speech_input_processor_Types["default"] = speech_input_processor_Types[default]
logging.info("Imported SpeechInputProcessor types in stt.py")
# print available STT types
logging.config(f"Available SpeechInputProcessor types: {speech_input_processor_Types.keys()}")

# Create speech_input_processor object using the config and client provided
    
def create_Speech_Input_Processor(stt_manager):
    """Creates a speech_input_processor object based on the config provided"""
    conversation_manager = stt_manager.conversation_manager
    config = conversation_manager.config
    config.manager_types["speech_processor"] = speech_input_processor_Types.keys()
    slug = conversation_manager.config.speech_processor
    if type(slug) == str:
        if slug not in speech_input_processor_Types:
            slug = slug.lower()
        if slug not in speech_input_processor_Types:
            logging.error(f"Could not find SpeechInputProcessor: {conversation_manager.config.speech_processor}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find SpeechInputProcessor: {conversation_manager.config.speech_processor}! Please check your config.json file and try again!")
        return speech_input_processor_Types[slug].Speech_Input_Processor(stt_manager)
    else:
        if slug in banned_modules:
            logging.error(f"Banned type for speech_processor in config.json! Please check your config.json file and try again! Banned type: {slug}")
            input("Press enter to continue...")
            raise ValueError(f"Banned type for speech_processor in config.json! Please check your config.json file and try again! Banned type: {slug}")
        else:
            logging.error(f"Wrong type for speech_processor in config.json! Expected string or list of strings, got '{type(slug)}'! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Wrong type for speech_processor in config.json! Expected string or list of strings, got '{type(slug)}'! Please check your config.json file and try again!")