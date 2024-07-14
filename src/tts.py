print("Imported tts.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in tts.py")

default = "xvasynth" # The default LLM to use if the one specified in config.json is not found or if default is specified in config.json
tts_Types = {}
# Get all LLMs from src/llms/ and add them to LLM_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "tts_types/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name != "base_tts":
            module = importlib.import_module(f"src.tts_types.{module_name}")
            tts_Types[module.tts_slug] = module
tts_Types["default"] = tts_Types[default]
logging.info("Imported TTS types in tts.py")
# print available TTS types
logging.config(f"Available TTS types: {tts_Types.keys()}")

# Create LLM object using the config and client provided
    
def create_Synthesizer(conversation_manager):
    slug = conversation_manager.config.tts_engine
    if type(slug) == list and len(slug) == 1:
        slug = slug[0]
    ttses = []
    if type(slug) == list:
        for s in slug:
            if s not in tts_Types:
                s = s.lower()
            if s not in tts_Types:
                logging.error(f"Could not find inference engine: {s}! Please check your config.json file and try again!")
                input("Press enter to continue...")
                raise ValueError(f"Could not find inference engine: {s}! Please check your config.json file and try again!")
            synth = tts_Types[s].Synthesizer(conversation_manager)
            synth.crashable = False # If we have multiple tts engines, we don't want to crash if one of them doesn't have a voice model
            ttses.append(synth)
        return tts_Types["multi_tts"].Synthesizer(conversation_manager, ttses)
    elif type(slug) == str:
        if slug not in tts_Types:
            slug = slug.lower()
        if slug not in tts_Types:
            logging.error(f"Could not find inference engine: {conversation_manager.config.tts_engine}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find inference engine: {conversation_manager.config.tts_engine}! Please check your config.json file and try again!")
        return tts_Types[slug].Synthesizer(conversation_manager)
    else:
        logging.error(f"Wrong type for tts_engine in config.json! Expected string or list of strings, got '{type(slug)}'! Please check your config.json file and try again!")
        input("Press enter to continue...")
        raise ValueError(f"Wrong type for tts_engine in config.json! Expected string or list of strings, got '{type(slug)}'! Please check your config.json file and try again!")