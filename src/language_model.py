import src.llms.openai_api as openai_api
import src.llms.llama_cpp_python as llama_cpp_python
import src.tokenizer as tokenizers
import logging

LLM_Types = {
    "openai": openai_api,
    "llama-cpp-python": llama_cpp_python, # TODO: Remove this later
    "default": openai_api
}

# Create LLM object using the config and client provided
    
def create_LLM(config, token_limit, language_info):
    if config.inference_engine not in LLM_Types:
        logging.error(f"Could not find inference engine: {config.inference_engine}! Please check your config.ini file and try again!")
        input("Press enter to continue...")
        exit()
    model = LLM_Types[config.inference_engine]
    llm = model.LLM(config, token_limit, language_info)
    if config.tokenizer_type == "default":
        if "Tokenizer" in llm.__dict__:
            logging.info(f"Using {config.inference_engine}'s included tokenizer")
            if "client" in llm.__dict__:
                tokenizer = llm.Tokenizer(config, llm.client)
            else:
                tokenizer = llm.Tokenizer(config)
        elif "tokenizer_slug" in llm.__dict__:
            logging.info(f"Using {config.inference_engine}'s recommended tokenizer")
            if "client" in llm.__dict__:
                tokenizer = tokenizers.Tokenizer_Types[llm.tokenizer_slug](config, llm.client)
            else:
                tokenizer = tokenizers.Tokenizer_Types[llm.tokenizer_slug](config)
        else:
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