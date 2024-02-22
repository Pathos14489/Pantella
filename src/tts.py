import logging
import os
import importlib

default = "xvasynth" # The default LLM to use if the one specified in config.json is not found or if default is specified in config.json
tts_Types = {}
# Get all LLMs from src/llms/ and add them to LLM_Types
for file in os.listdir("src/tts_types/"):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name != "base_tts":
            module = importlib.import_module(f"src.tts_types.{module_name}")
            tts_Types[module.tts_slug] = module    
tts_Types["default"] = tts_Types[default]

# Create LLM object using the config and client provided
    
def create_Synthesizer(conversation_manager):
    slug = conversation_manager.config.tts_engine
    if slug not in tts_Types:
        slug = slug.lower()
    if slug not in tts_Types:
        logging.error(f"Could not find inference engine: {conversation_manager.config.tts_engine}! Please check your config.json file and try again!")
        input("Press enter to continue...")
        exit()
    return tts_Types[slug].Synthesizer(conversation_manager)