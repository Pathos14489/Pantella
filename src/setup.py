import pandas as pd
import logging
import src.config_loader as config_loader
import src.utils as utils

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

    # clean up old instances of exe runtime files

    config = config_loader.ConfigLoader(config_file)
    utils.cleanup_mei(config.remove_mei_folders)
    logging_file, language_file = config.logging_file_path, config.language_support_file_path
    setup_logging(logging_file) # Setup logging with the file specified in config.ini

    is_local = True
    if (config.inference_engine == 'openai' or config.inference_engine == 'default') and config.alternative_openai_api_base == 'none': # TODO: Improve this. Should do more granularity than local or not.
        is_local = False
    config.is_local = is_local
    
    language_info = get_language_info(language_file) # Get language info from the language support file specified in config.ini

    return config, language_info