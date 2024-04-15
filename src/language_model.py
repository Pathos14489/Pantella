print("Importing language_model.py")
from src.logging import logging
import src.tokenizer as tokenizers
import os
import importlib
logging.info("Imported required libraries in language_model.py")

default = "openai" # The default LLM to use if the one specified in config.json is not found or if default is specified in config.json
LLM_Types = {}
# Get all LLMs from src/llms/ and add them to LLM_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "llms/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name != "base_llm":
            module = importlib.import_module(f"src.llms.{module_name}")
            LLM_Types[module.inference_engine_name] = module    
LLM_Types["default"] = LLM_Types[default]
logging.info("Imported all LLMs to LLM_Types, ready to create a LLM object!")

# Create LLM object using the config and client provided
    
def create_LLM(conversation_manager):
    if conversation_manager.config.inference_engine not in LLM_Types:
        logging.error(f"Could not find inference engine: {conversation_manager.config.inference_engine}! Please check your config.json file and try again!")
        input("Press enter to continue...")
        raise ValueError(f"Could not find inference engine: {conversation_manager.config.inference_engine}! Please check your config.json file and try again!")
    model = LLM_Types[conversation_manager.config.inference_engine]
    llm = model.LLM(conversation_manager)
    if conversation_manager.config.tokenizer_type == "default": # if using the default tokenizer for the LLM
        if "Tokenizer" in model.__dict__: # if the LLM has a tokenizer included
            logging.info(f"Using {conversation_manager.config.inference_engine}'s included tokenizer")
            tokenizer = model.Tokenizer(conversation_manager)
        elif "tokenizer_slug" in llm.__dict__: # or if the LLM has a tokenizer slug specified
            logging.info(f"Using {conversation_manager.config.inference_engine}'s recommended tokenizer")
            if "client" in llm.__dict__: # if the LLM has a client specified (only really needed for openai at this point)
                logging.info(llm.tokenizer_slug)
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