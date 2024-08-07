print("Imported tts.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in tts.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

default = "xvasynth" # The default TTS to use if the one specified in config.json is not found or if default is specified in config.json
tts_Types = {}
# Get all TTSes from src/ttses/ and add them to TTS_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "tts_types/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned TTS: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.tts_types")
        if module_name != "base_tts":
            module = importlib.import_module(f"src.tts_types.{module_name}")
            tts_Types[module.tts_slug] = module
tts_Types["default"] = tts_Types[default]
logging.info("Imported TTS types in tts.py")
# print available TTS types
logging.config(f"Available TTS types: {tts_Types.keys()}")

# Create TTS object using the config and client provided
    
def create_Synthesizer(conversation_manager):
    slugs = conversation_manager.config.tts_engine # Get the TTS slug from config.json
    if type(slugs) == list and len(slugs) == 1:
        slugs = slugs[0]
        logging.warning(f"Using single TTS engine: {slugs}")
    else:
        logging.info(f"Using multi_tts with TTS engines: {slugs}")
    ttses = []
    if type(slugs) == list: # If there are multiple TTS engines specified in config.json
        for slug in slugs:
            logging.info(f"Creating TTS engine: {slug}")
            if slug not in tts_Types:
                slug = slug.lower()
                logging.warning(f"Could not find inference engine: {slug}! Trying lowercase...?")
            if slug not in tts_Types:
                logging.error(f"Could not find inference engine: {slug}! Please check your config.json file and try again!")
                input("Press enter to continue...")
                raise ValueError(f"Could not find inference engine: {slug}! Please check your config.json file and try again!")
            logging.info(f"Found TTS engine '{slug}', loading...")
            synth = tts_Types[slug].Synthesizer(conversation_manager)
            synth.crashable = False # If we have multiple tts engines, we don't want to crash if one of them doesn't have a voice model
            ttses.append(synth)
        return tts_Types["multi_tts"].Synthesizer(conversation_manager, ttses)
    elif type(slugs) == str: # If there is only one TTS engine specified in config.json
        if slugs not in tts_Types:
            slugs = slugs.lower()
        if slugs not in tts_Types:
            logging.error(f"Could not find inference engine: {conversation_manager.config.tts_engine}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find inference engine: {conversation_manager.config.tts_engine}! Please check your config.json file and try again!")
        return tts_Types[slugs].Synthesizer(conversation_manager)
    else:
        logging.error(f"Wrong type for tts_engine in config.json! Expected string or list of strings, got '{type(slugs)}'! Please check your config.json file and try again!")
        input("Press enter to continue...")
        raise ValueError(f"Wrong type for tts_engine in config.json! Expected string or list of strings, got '{type(slugs)}'! Please check your config.json file and try again!")