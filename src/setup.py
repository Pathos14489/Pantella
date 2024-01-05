from openai import OpenAI
import pandas as pd
import logging

import src.config_loader as config_loader
import src.tts as tts
import src.utils as utils
import src.language_model as language_model
import src.character_db as character_db

def initialise(config_file, logging_file, secret_key_file, language_file):
    def setup_openai_secret_key(file_name):
        with open(file_name, 'r') as f:
            api_key = f.readline().strip()
        return api_key

    def setup_logging(file_name):
        logging.basicConfig(filename=file_name, format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logging.getLogger('').addHandler(console)

    def get_language_info(file_name):
        language_df = pd.read_csv(file_name)
        try:
            language_info = language_df.loc[language_df['alpha2']==config.language].to_dict('records')[0]
            return language_info
        except:
            logging.error(f"Could not load language '{config.language}'. Please set a valid language in config.ini\n")

    def get_token_limit(config):
        if config.is_local:
            logging.info(f"Using local language model. Token limit set to {config.maximum_local_tokens} (this number can be changed via the `maximum_local_tokens` setting in config.ini)")
            try:
                token_limit = int(config.maximum_local_tokens)
            except ValueError:
                logging.error(f"Invalid maximum_local_tokens value: {config.maximum_local_tokens}. It should be a valid integer. Please update your configuration.")
                token_limit = 4096  # Default to 4096 in case of an error.
        else:
            llm = config.llm
            if '/' in llm:
                llm = llm.split('/')[-1]

            if llm == 'gpt-3.5-turbo':
                token_limit = 4096
            elif llm == 'gpt-3.5-turbo-16k':
                token_limit = 16384
            elif llm == 'gpt-4':
                token_limit = 8192
            elif llm == 'gpt-4-32k':
                token_limit = 32768
            elif llm == 'claude-2':
                token_limit = 100_000
            elif llm == 'claude-instant-v1':
                token_limit = 100_000
            elif llm == 'palm-2-chat-bison':
                token_limit = 8000
            elif llm == 'palm-2-codechat-bison':
                token_limit = 8000
            elif llm == 'llama-2-7b-chat':
                token_limit = 4096
            elif llm == 'llama-2-13b-chat':
                token_limit = 4096
            elif llm == 'llama-2-70b-chat':
                token_limit = 4096
            elif llm == 'codellama-34b-instruct':
                token_limit = 16000
            elif llm == 'nous-hermes-llama2-13b':
                token_limit = 4096
            elif llm == 'weaver':
                token_limit = 8000
            elif llm == 'mythomax-L2-13b':
                token_limit = 8192
            elif llm == 'airoboros-l2-70b-2.1':
                token_limit = 4096
            elif llm == 'gpt-3.5-turbo-1106':
                token_limit = 16_385
            elif llm == 'gpt-4-1106-preview':
                token_limit = 128_000
            else:
                logging.info(f"Could not find number of available tokens for {llm}. Defaulting to token count of {config.maximum_local_tokens} (this number can be changed via the `maximum_local_tokens` setting in config.ini)")

        if token_limit <= 4096:
            logging.info(f"{llm} has a low token count of {token_limit}. For better NPC memories, try changing to a model with a higher token count")
        return token_limit

    setup_logging(logging_file)
    config = config_loader.ConfigLoader(config_file)
    
    
    is_local = True
    if (config.alternative_openai_api_base == 'none'): # or (config.alternative_openai_api_base.startswith('https://openrouter.ai/api/v1')) -- this is a temporary fix for the openrouter api, as while it isn't local, it shouldnn't use the local tokenizer, so we're going to lie here TODO: Fix this. Should do more granularity than local or not, should just have a flag for when using openai or other models.
        is_local = False
    
    api_key = setup_openai_secret_key(secret_key_file)
    client = OpenAI(api_key=api_key)

    if config.alternative_openai_api_base != 'none':
        client.base_url  = config.alternative_openai_api_base
        logging.info(f"Using OpenAI API base: {client.base_url}")

    if is_local:
        logging.info(f"Running Mantella with local language model")
    else:
       logging.info(f"Running Mantella with '{config.llm}'. The language model chosen can be changed via config.ini")

    xvasynth = tts.Synthesizer(config)

    # clean up old instances of exe runtime files
    utils.cleanup_mei(config.remove_mei_folders)
    character_df = character_db.CharacterDB(config,xvasynth)
    
    language_info = get_language_info(language_file)
    
    config.is_local = is_local

    tokenizer = language_model.Tokenizer(config,client)
    token_limit = get_token_limit(config)
    
    llm = language_model.LLM(config, client, tokenizer, token_limit, language_info)



    return config, character_df, language_info, llm, tokenizer, token_limit, xvasynth