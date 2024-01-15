import pandas as pd
import logging
import src.config_loader as config_loader
import src.tts as tts
import src.utils as utils
import src.language_model as language_models
import src.character_db as character_db

def initialise(config_file):
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

    def get_token_limit(config): # TODO: Move this to the openai_api.py file later or something, this doesn't belong here anymore
        if config.is_local:
            logging.info(f"Using local language model. Token limit set to {str(config.maximum_local_tokens)} (this number can be changed via the `maximum_local_tokens` setting in config.ini)")
            try:
                token_limit = config.maximum_local_tokens
            except ValueError:
                logging.error(f"Invalid maximum_local_tokens value: {str(config.maximum_local_tokens)}. It should be a valid integer. Please update your configuration.")
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
                logging.info(f"Could not find number of available tokens for {llm}. Defaulting to token count of {str(config.maximum_local_tokens)} (this number can be changed via the `maximum_local_tokens` setting in config.ini)")

        if token_limit <= 4096:
            logging.info(f"{llm} has a low token count of {token_limit}. For better NPC memories, try changing to a model with a higher token count")
        return token_limit

    # clean up old instances of exe runtime files

    config = config_loader.ConfigLoader(config_file)
    utils.cleanup_mei(config.remove_mei_folders)
    logging_file, language_file = config.logging_file_path, config.language_support_file_path
    setup_logging(logging_file) # Setup logging with the file specified in config.ini

    is_local = True
    if (config.alternative_openai_api_base == 'none' or config.inference_engine != 'openai' and config.inference_engine != 'default'): # TODO: Improve this. Should do more granularity than local or not.
        is_local = False
    config.is_local = is_local
    
    xvasynth = tts.Synthesizer(config) # Create Synthesizer object using the config provided
    character_df = character_db.CharacterDB(config, xvasynth) # Create CharacterDB object using the config and client provided
    
    language_info = get_language_info(language_file) # Get language info from the language support file specified in config.ini
    
    token_limit = get_token_limit(config)

    llm, tokenizer = language_models.create_LLM(config, token_limit, language_info) # Create LLM and Tokenizer based on config

    return config, character_df, language_info, llm, tokenizer, token_limit, xvasynth