print("Importing koboldcpp.py...")
from src.logging import logging
import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
import requests
logging.info("Imported required libraries in koboldcpp.py")

tokenizer_slug = "koboldcpp"
class Tokenizer(tokenizer.base_Tokenizer): # Gets token count from OpenAI's embedding API -- WARNING SLOW AS HELL -- Only use if you don't want to set up the right tokenizer for your local model or if you don't know how to do that
    def __init__(self, conversation_manager, client):
        super().__init__(conversation_manager)
        if not (self.config.inference_engine == "openai" or self.config.inference_engine == "default"):
            logging.error(f"koboldcpp tokenizer only works using OpenAI's API! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"koboldcpp tokenizer only works using OpenAI's API! Please check your config.json file and try again!")
        self.tokenizer_slug = tokenizer_slug
        self.client = client # Unnecessary for this tokenizer, but it's here for compatibility with other openai tokenizers
        
    @utils.time_it
    def get_token_count(self, string):
        """Returns the number of tokens in the string"""
        data = {"prompt": string}
        try:
            url = self.config.alternative_openai_api_base.replace("/v1/","") + "/api/extra/tokencount"
            r = requests.post(url, json=data)
            r.raise_for_status()
            r = r.json()
        except:
            try:
                url = self.config.openai_api_base.replace("/v1","") + "/extra/tokencount"
                r = requests.post(url, json=data)
                r.raise_for_status()
                r = r.json()
            except Exception as e:
                logging.error(f"Error getting token count from koboldcpp API: {e}")
                raise
        num_tokens = int(r["value"])
        return num_tokens
    