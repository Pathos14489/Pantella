print("Importing language_model.py")
from src.logging import logging
import src.tokenizer as tokenizers
import os
import importlib
logging.info("Imported required libraries in language_model.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

default = "openai" # The default LLM to use if the one specified in config.json is not found or if default is specified in config.json
LLM_Types = {}
# Get all LLMs from src/inference_engines/ and add them to LLM_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "inference_engines/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned language model: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.inference_engines")
        if module_name != "base_llm":
            module = importlib.import_module(f"src.inference_engines.{module_name}")
            LLM_Types[module.inference_engine_name] = module    
LLM_Types["default"] = LLM_Types[default]
logging.info("Imported all LLMs to LLM_Types, ready to create a LLM object!")
# print available LLMs
logging.config(f"Available LLMs: {LLM_Types.keys()}")

# Create LLM object using the config and client provided
    
def create_LLM(conversation_manager):
    """Creates a language model object based on the config provided"""
    config = conversation_manager.config
    config.manager_types["language_model"] = LLM_Types.keys() # Add conversation manager types to config
    config.manager_types["tokenizer"] = tokenizers.Tokenizer_Types.keys() # Add conversation manager types to config
    logging.info(f"Creating LLM[{conversation_manager.config.inference_engine}] object")
    if conversation_manager.config.inference_engine not in LLM_Types:
        logging.error(f"Could not find inference engine: {conversation_manager.config.inference_engine}! Please check your config.json file and try again!")
        input("Press enter to continue...")
        raise ValueError(f"Could not find inference engine: {conversation_manager.config.inference_engine}! Please check your config.json file and try again!")
    model = LLM_Types[conversation_manager.config.inference_engine]
    llm = model.LLM(conversation_manager, vision_enabled=conversation_manager.config.vision_enabled)
    if conversation_manager.config.tokenizer_type == "default": # if using the default tokenizer for the LLM
        if "Tokenizer" in model.__dict__: # if the LLM has a tokenizer included
            logging.config(f"Using {conversation_manager.config.inference_engine}'s included tokenizer")
            tokenizer = model.Tokenizer(conversation_manager)
        elif "tokenizer_slug" in llm.__dict__: # or if the LLM has a tokenizer slug specified
            logging.config(f"Using {conversation_manager.config.inference_engine} inference engine's recommended tokenizer")
            if "client" in llm.__dict__: # if the LLM has a client specified (only really needed for openai at this point)
                logging.config(llm.tokenizer_slug)
                tokenizer = tokenizers.Tokenizer_Types[llm.tokenizer_slug].Tokenizer(conversation_manager, llm.client)
            else:
                tokenizer = tokenizers.Tokenizer_Types[llm.tokenizer_slug].Tokenizer(conversation_manager)
        else: # or if the LLM has no tokenizer specified
            logging.error(f"Could not find default tokenizer for inference engine: {llm.inference_engine_name}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find default tokenizer for inference engine: {llm.inference_engine_name}! Please check your config.json file and try again!")
    elif conversation_manager.config.tokenizer_type in tokenizers.Tokenizer_Types: # if using a custom tokenizer
        if "client" in llm.__dict__: # if the LLM has a client specified (only really needed for openai at this point)
            tokenizer = tokenizers.Tokenizer_Types[conversation_manager.config.tokenizer_type].Tokenizer(conversation_manager, llm.client)
        else: # if the LLM has no client specified
            tokenizer = tokenizers.Tokenizer_Types[conversation_manager.config.tokenizer_type].Tokenizer(conversation_manager)
    llm.tokenizer = tokenizer # Add the tokenizer to the LLM object
    return llm, tokenizer