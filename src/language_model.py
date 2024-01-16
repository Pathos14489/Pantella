# import src.llms.llama_cpp_python as llama_cpp_python
# import src.llms.openai_api as openai_api
import src.tokenizer as tokenizers
import logging
import os
import importlib

defalut = "openai" # The default LLM to use if the one specified in config.ini is not found or if default is specified in config.ini
LLM_Types = {}
# Get all LLMs from src/llms/ and add them to LLM_Types
for file in os.listdir("src/llms/"):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name != "base_llm":
            module = importlib.import_module(f"src.llms.{module_name}")
            LLM_Types[module.inference_engine_name] = module    
LLM_Types["default"] = LLM_Types[defalut]

# Create LLM object using the config and client provided
    
def create_LLM(config, token_limit, language_info):
    if config.inference_engine not in LLM_Types:
        logging.error(f"Could not find inference engine: {config.inference_engine}! Please check your config.ini file and try again!")
        input("Press enter to continue...")
        exit()
    model = LLM_Types[config.inference_engine]
    llm = model.LLM(config, token_limit, language_info)
    if config.tokenizer_type == "default": # if using the default tokenizer for the LLM
        if "Tokenizer" in model.__dict__: # if the LLM has a tokenizer included
            logging.info(f"Using {config.inference_engine}'s included tokenizer")
            tokenizer = model.Tokenizer(config)
        elif "tokenizer_slug" in llm.__dict__: # or if the LLM has a tokenizer slug specified
            logging.info(f"Using {config.inference_engine}'s recommended tokenizer")
            if "client" in llm.__dict__: # if the LLM has a client specified (only really needed for openai at this point)
                tokenizer = tokenizers.Tokenizer_Types[llm.tokenizer_slug](config, llm.client)
            else:
                tokenizer = tokenizers.Tokenizer_Types[llm.tokenizer_slug](config)
        else: # or if the LLM has no tokenizer specified
            logging.error(f"Could not find default tokenizer for inference engine: {llm.inference_engine_name}! Please check your config.ini file and try again!")
            input("Press enter to continue...")
            exit()
    elif config.tokenizer_type in tokenizers.Tokenizer_Types:
        if "client" in llm.__dict__:
            tokenizer = tokenizers.Tokenizer_Types[config.tokenizer_type](config, llm.client)
        else:
            tokenizer = tokenizers.Tokenizer_Types[config.tokenizer_type](config)
    llm.tokenizer = tokenizer
    return llm, tokenizer